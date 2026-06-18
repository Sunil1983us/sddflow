from __future__ import annotations
import requests


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
        r = self._s.get(self._api("/content"), params={
            "type":     "page",
            "spaceKey": space_key,
            "title":    title,
            "expand":   "version",
        })
        r.raise_for_status()
        results = r.json().get("results", [])
        return results[0] if results else None

    def create_page(self, space_key: str, title: str, body_html: str,
                    parent_id: str | None = None) -> dict:
        payload: dict = {
            "type":  "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value":          body_html,
                    "representation": "storage",
                }
            },
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]
        r = self._s.post(self._api("/content"), json=payload)
        r.raise_for_status()
        return r.json()

    def update_page(self, page_id: str, version: int, title: str,
                    body_html: str) -> dict:
        payload = {
            "type":    "page",
            "title":   title,
            "version": {"number": version + 1},
            "body": {
                "storage": {
                    "value":          body_html,
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

    def upsert_page(self, space_key: str, title: str, body_html: str,
                    parent_id: str | None = None) -> tuple[dict, bool]:
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
