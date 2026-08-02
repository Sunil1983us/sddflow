from __future__ import annotations

import html
import re

import requests


def _strip_html(text: str) -> str:
    """Remove HTML tags and unescape entities (for comment bodies)."""
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(text).strip()


class ConfluenceClient:
    """Thin wrapper around Confluence REST API v1 (compatible with Cloud and Server/DC)."""

    def __init__(self, session: requests.Session, base_url: str):
        self._s = session
        self._base = base_url.rstrip("/")

    def _api(self, path: str) -> str:
        return f"{self._base}/wiki/rest/api{path}"

    def get_myself(self) -> dict:
        r = self._s.get(self._api("/user/current"))
        r.raise_for_status()
        return r.json()

    def get_page_by_title(self, space_key: str, title: str) -> dict | None:
        r = self._s.get(
            self._api("/content"),
            params={
                "type": "page",
                "spaceKey": space_key,
                "title": title,
                "expand": "version",
            },
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        return results[0] if results else None

    def create_page(
        self, space_key: str, title: str, body_html: str, parent_id: str | None = None
    ) -> dict:
        payload: dict = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": body_html,
                    "representation": "storage",
                }
            },
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]
        r = self._s.post(self._api("/content"), json=payload)
        r.raise_for_status()
        return r.json()

    def update_page(
        self, page_id: str, version: int, title: str, body_html: str
    ) -> dict:
        payload = {
            "type": "page",
            "title": title,
            "version": {"number": version + 1},
            "body": {
                "storage": {
                    "value": body_html,
                    "representation": "storage",
                }
            },
        }
        # expand=_links ensures the PUT response includes the webui URL,
        # matching the create_page() response shape used by callers.
        r = self._s.put(
            self._api(f"/content/{page_id}"),
            params={"expand": "_links"},
            json=payload,
        )
        r.raise_for_status()
        return r.json()

    def upload_attachment(
        self,
        page_id: str,
        filename: str,
        content: bytes,
        media_type: str = "image/svg+xml",
    ) -> dict:
        """Attach a file to a page. Confluence's attachment endpoint
        automatically creates a new version of an existing attachment
        with the same filename rather than erroring or duplicating it --
        callers don't need to check for an existing attachment first,
        the same idempotent-by-name behavior upsert_page() already
        relies on for pages themselves.

        X-Atlassian-Token: nocheck is required on multipart uploads --
        Confluence's XSRF protection otherwise rejects them.

        Content-Type: None is required too -- build_session() sets a
        blanket "application/json" Content-Type on the shared session for
        every other call this client makes, but requests only computes
        the multipart/form-data; boundary=... header itself when no
        Content-Type is already present. Since a per-request header
        merges over the session default rather than replacing it,
        leaving this unset would silently send multipart bytes labeled
        application/json -- Confluence's attachment endpoint returns 415
        for that, while the page content itself still saves fine (this
        is what a missing SVG image with no error looked like in
        practice). Passing None here is requests' documented way to
        remove a session-level header for one request."""
        r = self._s.post(
            self._api(f"/content/{page_id}/child/attachment"),
            headers={"X-Atlassian-Token": "nocheck", "Content-Type": None},
            files={"file": (filename, content, media_type)},
        )
        r.raise_for_status()
        return r.json()

    def get_page_with_body(self, page_id: str) -> dict:
        """Fetch a page including its body in storage format."""
        r = self._s.get(
            self._api(f"/content/{page_id}"),
            params={"expand": "body.storage,version,_links"},
        )
        r.raise_for_status()
        return r.json()

    def get_page_comments(self, page_id: str) -> list[dict]:
        """Return all footer comments on a page (newest first).

        Each item has: author (display name), created, body (plain text).
        Inline comments are fetched separately via get_inline_comments().
        """
        r = self._s.get(
            self._api(f"/content/{page_id}/child/comment"),
            params={"expand": "body.view,version,ancestors", "limit": 100},
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        comments = []
        for c in results:
            author = c.get("version", {}).get("by", {}).get("displayName", "Unknown")
            created = c.get("version", {}).get("when", "")
            body_html = c.get("body", {}).get("view", {}).get("value", "")
            body_text = _strip_html(body_html)
            if body_text.strip():
                comments.append(
                    {
                        "author": author,
                        "created": created[:10] if created else "",
                        "text": body_text.strip(),
                        "type": "comment",
                    }
                )
        return comments

    def get_inline_comments(self, page_id: str) -> list[dict]:
        """Return unresolved inline (annotation) comments on a page."""
        r = self._s.get(
            self._api(f"/content/{page_id}/child/comment"),
            params={
                "expand": "body.view,version,extensions.inlineProperties",
                "limit": 100,
                "location": "inline",
            },
        )
        if r.status_code == 400:
            return []
        r.raise_for_status()
        results = r.json().get("results", [])
        comments = []
        for c in results:
            resolved = (
                c.get("extensions", {}).get("resolution", {}).get("status", "")
                == "resolved"
            )
            if resolved:
                continue
            author = c.get("version", {}).get("by", {}).get("displayName", "Unknown")
            created = c.get("version", {}).get("when", "")
            body_html = c.get("body", {}).get("view", {}).get("value", "")
            body_text = _strip_html(body_html)
            if body_text.strip():
                comments.append(
                    {
                        "author": author,
                        "created": created[:10] if created else "",
                        "text": body_text.strip(),
                        "type": "inline",
                    }
                )
        return comments

    def upsert_page(
        self, space_key: str, title: str, body_html: str, parent_id: str | None = None
    ) -> tuple[dict, bool]:
        """Create or update a page. Returns (page_dict, was_created)."""
        existing = self.get_page_by_title(space_key, title)
        if existing:
            page = self.update_page(
                existing["id"],
                existing["version"]["number"],
                title,
                body_html,
            )
            return page, False
        page = self.create_page(space_key, title, body_html, parent_id)
        return page, True
