from __future__ import annotations
import requests


class JiraClient:
    """Thin wrapper around Jira REST API v3 (Cloud) / v2 (Server/DC)."""

    def __init__(self, session: requests.Session, base_url: str):
        self._s = session
        self._base = base_url.rstrip("/")

    def _api(self, path: str) -> str:
        return f"{self._base}/rest/api/3{path}"

    def get_myself(self) -> dict:
        r = self._s.get(self._api("/myself"))
        r.raise_for_status()
        return r.json()

    def get_fields(self) -> list[dict]:
        r = self._s.get(self._api("/field"))
        r.raise_for_status()
        return r.json()

    def search(self, jql: str, fields: list[str] | None = None,
               max_results: int = 50) -> list[dict]:
        params: dict = {"jql": jql, "maxResults": max_results}
        if fields:
            params["fields"] = ",".join(fields)
        r = self._s.get(self._api("/search"), params=params)
        r.raise_for_status()
        return r.json().get("issues", [])

    def find_by_label(self, project_key: str, label: str) -> dict | None:
        issues = self.search(
            f'project = "{project_key}" AND labels = "{label}"',
            fields=["summary", "status", "issuetype", "labels", "parent"],
        )
        return issues[0] if issues else None

    def create_issue(self, fields: dict) -> dict:
        r = self._s.post(self._api("/issue"), json={"fields": fields})
        r.raise_for_status()
        return r.json()

    def update_issue(self, issue_key: str, fields: dict) -> None:
        r = self._s.put(
            self._api(f"/issue/{issue_key}"),
            json={"fields": fields},
        )
        r.raise_for_status()

    def set_parent(self, child_key: str, parent_key: str,
                   parent_field: str = "parent") -> None:
        if parent_field == "parent":
            self.update_issue(child_key, {"parent": {"key": parent_key}})
        else:
            self.update_issue(child_key, {parent_field: parent_key})

    def get_issue_types(self, project_key: str) -> list[dict]:
        r = self._s.get(self._api(f"/project/{project_key}/statuses"))
        r.raise_for_status()
        return r.json()

    def get_comments(self, issue_key: str) -> list[dict]:
        r = self._s.get(self._api(f"/issue/{issue_key}/comment"))
        r.raise_for_status()
        return r.json().get("comments", [])

    def add_comment(self, issue_key: str, text: str) -> dict:
        """Add a plain-text comment. Uses ADF format for Cloud/Server compatibility."""
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [{
                    "type": "paragraph",
                    "content": [{"type": "text", "text": text}],
                }],
            }
        }
        r = self._s.post(self._api(f"/issue/{issue_key}/comment"), json=payload)
        r.raise_for_status()
        return r.json()
