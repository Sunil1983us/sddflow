from __future__ import annotations

import requests

from sdd.utils.http_errors import raise_for_status_with_body


class JiraClient:
    """Thin wrapper around Jira REST API v3 (Cloud) / v2 (Server/DC).

    Jira Server/Data Center does not support REST API v3 at all -- it's
    Cloud-exclusive (confirmed: JRASERVER-70688, an Atlassian Data
    Center feature request for v3 support, is still open). Every request
    against a Server/DC instance built with the v3 path fails -- not
    always with a clean 401/404: a reverse proxy or SSO gateway in front
    of the real instance can respond 200 with an HTML login page, or
    403, for a path it doesn't recognize, which is what made this hard
    to diagnose from the CLI's error message alone before this existed
    (see the `deployment` parameter below and Profile.deployment)."""

    def __init__(
        self, session: requests.Session, base_url: str, *, deployment: str = "cloud"
    ):
        self._s = session
        self._base = base_url.rstrip("/")
        self.deployment = deployment
        self._api_version = "2" if deployment == "server" else "3"

    def _api(self, path: str) -> str:
        return f"{self._base}/rest/api/{self._api_version}{path}"

    def get_myself(self) -> dict:
        r = self._s.get(self._api("/myself"))
        raise_for_status_with_body(r)
        return r.json()

    def get_fields(self) -> list[dict]:
        r = self._s.get(self._api("/field"))
        raise_for_status_with_body(r)
        return r.json()

    def search(
        self, jql: str, fields: list[str] | None = None, max_results: int = 50
    ) -> list[dict]:
        """Run a JQL search. Cloud (v3) uses POST /rest/api/3/search/jql --
        Atlassian deprecated the old GET /rest/api/3/search endpoint
        (removed, returns 410 Gone) in favor of this one, but /search/jql
        is itself Cloud-only: it does not exist on Server/Data Center,
        which never deprecated its classic /rest/api/2/search endpoint
        (confirmed against a real Data Center instance -- posting to
        .../2/search/jql there returns a clean 404, breaking every
        idempotency lookup, i.e. every --level epic/story/task/chg push,
        the moment `deployment='server'` is set). Server/DC therefore
        posts to plain /search instead. Only the first page is fetched
        (no nextPageToken follow-up): every caller in this codebase is an
        idempotency lookup expecting 0-1 matches, well under max_results,
        so pagination has never been needed here."""
        payload: dict = {"jql": jql, "maxResults": max_results}
        if fields:
            payload["fields"] = fields
        path = "/search/jql" if self._api_version == "3" else "/search"
        r = self._s.post(self._api(path), json=payload)
        raise_for_status_with_body(r)
        return r.json().get("issues", [])

    def find_by_label(self, project_key: str, label: str) -> dict | None:
        safe_project = project_key.replace('"', '\\"')
        safe_label = label.replace('"', '\\"')
        issues = self.search(
            f'project = "{safe_project}" AND labels = "{safe_label}"',
            fields=["summary", "status", "issuetype", "labels", "parent"],
        )
        return issues[0] if issues else None

    def create_issue(self, fields: dict) -> dict:
        r = self._s.post(self._api("/issue"), json={"fields": fields})
        raise_for_status_with_body(r)
        return r.json()

    def update_issue(self, issue_key: str, fields: dict) -> None:
        r = self._s.put(
            self._api(f"/issue/{issue_key}"),
            json={"fields": fields},
        )
        raise_for_status_with_body(r)

    def set_parent(
        self, child_key: str, parent_key: str, parent_field: str = "parent"
    ) -> None:
        if parent_field == "parent":
            self.update_issue(child_key, {"parent": {"key": parent_key}})
        else:
            self.update_issue(child_key, {parent_field: parent_key})

    def link_issues(
        self, from_key: str, to_key: str, link_type: str = "Relates"
    ) -> None:
        """Create a Jira issue link (default type "Relates", present on
        every Jira instance out of the box) between two issues. Unlike
        the parent/Epic-Link relationship set_parent() establishes, issue
        links are NOT scoped to a single project -- this is the fallback
        used when a true parent-child link can't be created (most
        commonly: child and parent live in different Jira projects,
        which the parent/Epic-Link field rejects outright)."""
        r = self._s.post(
            self._api("/issueLink"),
            json={
                "type": {"name": link_type},
                "inwardIssue": {"key": from_key},
                "outwardIssue": {"key": to_key},
            },
        )
        raise_for_status_with_body(r)

    def get_issue_types(self, project_key: str) -> list[dict]:
        r = self._s.get(self._api(f"/project/{project_key}/statuses"))
        raise_for_status_with_body(r)
        return r.json()

    def get_createmeta_fields(
        self, project_key: str, issue_type_name: str
    ) -> dict | None:
        """Fetch Jira's own field metadata (required/optional, schema
        type) for a given project + issue type, via the classic
        createmeta endpoint. This is Jira's own source of truth for what
        a create-issue request needs -- letting `sdd doctor` validate any
        organization's custom issue types and required fields generically,
        without this codebase needing to know about them in advance.

        Still the only createmeta option on Server/Data Center (API v2 --
        confirmed, see this class's own docstring on v2/v3). Cloud has
        since introduced a newer two-step per-issue-type endpoint and
        Atlassian's docs mark this classic one deprecated there, though it
        remains functional as of writing; if Atlassian removes it from
        Cloud entirely, this is the call site that would need a
        Cloud-specific fallback.

        Returns None if the project or issue type wasn't found (empty
        "projects" or "issuetypes" in the response) -- a genuinely
        different finding from "found but has zero fields", so callers
        can tell "typo'd issue type name" apart from "issue type has no
        custom fields configured at all"."""
        r = self._s.get(
            self._api("/issue/createmeta"),
            params={
                "projectKeys": project_key,
                "issuetypeNames": issue_type_name,
                "expand": "projects.issuetypes.fields",
            },
        )
        raise_for_status_with_body(r)
        projects = r.json().get("projects", [])
        if not projects:
            return None
        issuetypes = projects[0].get("issuetypes", [])
        if not issuetypes:
            return None
        return issuetypes[0].get("fields", {})

    def get_comments(self, issue_key: str) -> list[dict]:
        r = self._s.get(self._api(f"/issue/{issue_key}/comment"))
        raise_for_status_with_body(r)
        return r.json().get("comments", [])

    def get_transitions(self, issue_key: str) -> list[dict]:
        """List the transitions currently available for this issue, given
        its current workflow state. Each entry has at least 'id' and
        'to': {'name': ...}."""
        r = self._s.get(self._api(f"/issue/{issue_key}/transitions"))
        raise_for_status_with_body(r)
        return r.json().get("transitions", [])

    def transition_issue(self, issue_key: str, target_status_name: str) -> bool:
        """Move an issue to the named status, if a transition to it exists
        from the issue's current workflow state. Returns True if a
        transition was found and executed, False if none matches (e.g.
        the ticket is already in that status -- Jira does not offer a
        self-transition -- or the configured workflow simply doesn't
        allow reaching that status from here).

        False is a normal, silent outcome for callers, not an error:
        workflow shapes vary per Jira project (custom status names,
        custom transition graphs) and this is a best-effort nudge, never
        a hard requirement for the review-apply flow to proceed."""
        transitions = self.get_transitions(issue_key)
        match = next(
            (
                t
                for t in transitions
                if t.get("to", {}).get("name", "").casefold()
                == target_status_name.casefold()
            ),
            None,
        )
        if not match:
            return False
        r = self._s.post(
            self._api(f"/issue/{issue_key}/transitions"),
            json={"transition": {"id": match["id"]}},
        )
        raise_for_status_with_body(r)
        return True

    def add_comment(self, issue_key: str, text: str) -> dict:
        """Add a plain-text comment. Cloud (v3) requires the comment body
        in Atlassian Document Format (ADF); Server/Data Center (v2) has
        no ADF support at all and expects `body` as a plain string --
        sending the ADF wrapper there is a field-type mismatch Jira
        rejects outright (this method's own prior docstring claimed ADF
        was fine "for Cloud/Server compatibility", which was simply
        wrong and shipped as a real bug: every comment this CLI tried to
        post against a Server/DC instance -- review status updates, PR-
        created notifications -- failed)."""
        if self.deployment == "server":
            payload: dict = {"body": text}
        else:
            payload = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": text}],
                        }
                    ],
                }
            }
        r = self._s.post(self._api(f"/issue/{issue_key}/comment"), json=payload)
        raise_for_status_with_body(r)
        return r.json()
