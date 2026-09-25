from __future__ import annotations

import requests

from sdd.utils.http_errors import raise_for_status_with_body


def _assignee_creation_error(response: requests.Response) -> str | None:
    """If a failed create-issue response's body blames the assignee
    field specifically, return Jira's own message for it; otherwise
    None.

    Jira's create-issue validation returns a body shaped like
    {"errorMessages": [...], "errors": {"<field-id>": "<reason>"}} --
    "errors" is keyed by field id, so an "assignee" key there is Jira's
    own signal that this field, and only this field, needs dropping to
    retry. A malformed/non-JSON body (a reverse proxy can return HTML
    for a 400) is treated as "no assignee-specific signal", not as
    license to guess and retry anyway."""
    try:
        body = response.json()
    except ValueError:
        return None
    if not isinstance(body, dict):
        return None
    errors = body.get("errors")
    if not isinstance(errors, dict):
        return None
    reason = errors.get("assignee")
    return reason if isinstance(reason, str) else None


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

    def assignee_field(self, user: str) -> dict:
        """Build an `assignee` field value for this deployment.

        The two are not interchangeable. `accountId` is a Cloud construct
        introduced with Atlassian's GDPR changes; Server/Data Center never
        adopted it and identifies users by `name` instead. Sending an
        accountId to Data Center does not error loudly -- the create call
        can come back 2xx with the issue simply left unassigned -- which
        is exactly how this went unnoticed: every call site hardcoded
        {"accountId": ...} regardless of deployment.

        `user` is whatever GET /rest/api/2/myself reports as `name` on
        Server/DC (on 8.x+ that is often a synthetic id such as
        JIRAUSER10100, not a human-readable login -- pass it through as
        given, do not try to prettify it), or the accountId on Cloud.
        """
        return {"name": user} if self.deployment == "server" else {"accountId": user}

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
        """Create a Jira issue.

        If `fields` includes "assignee" and Jira's validation rejects
        specifically that field (unrecognised/deactivated/mistyped user
        -- see _assignee_creation_error()), this retries once with
        "assignee" stripped rather than failing the whole ticket. A
        ticket created this way is unassigned, and the returned dict
        carries an extra "_assignee_dropped_reason" key (Jira's own
        error text for the field) so the caller can warn about it. This
        only fires when the retry itself succeeds -- if some OTHER
        field is also invalid, the retry's own error propagates
        normally and names only that field, since assignee is no longer
        part of the request by then.

        Reported live: `reviewer_jira_user` in integrations.yml is a
        hand-typed value (a username or accountId, see
        assignee_field()) with nothing to validate it against at config
        time. A typo, a reviewer who left the org, or a Cloud/Server
        accountId-vs-name mismatch would otherwise fail the ENTIRE
        review/CR ticket over a field that has no bearing on whether
        the document itself is trackable -- the whole point of the
        ticket."""
        r = self._s.post(self._api("/issue"), json={"fields": fields})
        if r.status_code == 400 and "assignee" in fields:
            reason = _assignee_creation_error(r)
            if reason is not None:
                retry_fields = {k: v for k, v in fields.items() if k != "assignee"}
                r2 = self._s.post(self._api("/issue"), json={"fields": retry_fields})
                raise_for_status_with_body(r2)
                result = r2.json()
                result["_assignee_dropped_reason"] = reason
                return result
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

    @staticmethod
    def _paged_values(payload: dict) -> list[dict]:
        """Pull the rows out of one of Jira's paginated envelopes
        ({startAt, maxResults, total, isLast, values}). Returns [] for a
        payload that isn't one, so callers can probe a shape safely."""
        values = payload.get("values")
        return values if isinstance(values, list) else []

    def _createmeta_issue_types(self, project_key: str) -> list[dict] | None:
        """Issue types for a project via the modern per-project endpoint.

        Returns None when the endpoint itself isn't on this instance, so
        the caller can fall back; [] means it answered and the project
        genuinely has no issue types."""
        out: list[dict] = []
        start = 0
        # Bounded rather than while-True: a server that ignores startAt
        # (or mis-reports isLast) would otherwise spin forever. 20 pages
        # at the default 50/page is far more issue types than any real
        # project has.
        for _ in range(20):
            r = self._s.get(
                self._api(f"/issue/createmeta/{project_key}/issuetypes"),
                params={"startAt": start, "maxResults": 50},
            )
            if r.status_code == 404:
                return None
            raise_for_status_with_body(r)
            payload = r.json()
            page = self._paged_values(payload)
            out.extend(page)
            if payload.get("isLast", True) or not page:
                break
            start += len(page)
        return out

    def _createmeta_field_map(self, project_key: str, issue_type_id: str) -> dict:
        """Field metadata for one issue type, normalised to the same
        {field_id: {...}} mapping the classic endpoint returned, so
        callers don't need to know which endpoint answered.

        The modern endpoint returns a paginated LIST of field objects
        keyed by 'fieldId' rather than a dict keyed by field id. Both
        shapes are accepted here because this could not be verified
        against every Jira version -- a server that returns the classic
        {'fields': {...}} dict is passed straight through."""
        out: dict = {}
        start = 0
        for _ in range(20):
            r = self._s.get(
                self._api(
                    f"/issue/createmeta/{project_key}/issuetypes/{issue_type_id}"
                ),
                params={"startAt": start, "maxResults": 50},
            )
            raise_for_status_with_body(r)
            payload = r.json()
            classic = payload.get("fields")
            if isinstance(classic, dict):
                return classic
            page = self._paged_values(payload)
            for field in page:
                field_id = field.get("fieldId") or field.get("key") or field.get("id")
                if field_id:
                    out[field_id] = field
            if payload.get("isLast", True) or not page:
                break
            start += len(page)
        return out

    def get_createmeta_fields(
        self, project_key: str, issue_type_name: str
    ) -> dict | None:
        """Fetch Jira's own field metadata (required/optional, schema
        type) for a given project + issue type. This is Jira's source of
        truth for what a create-issue request needs -- letting
        `sdd doctor` validate any organization's custom issue types and
        required fields generically, without this codebase needing to
        know about them in advance.

        Two endpoints exist and which one an instance serves depends on
        its version:

        - Modern, two calls: /issue/createmeta/{key}/issuetypes then
          .../issuetypes/{id}. Added in Jira 8.4 (Server/DC) and the ONLY
          option from Jira 9.0, which removed the classic one outright
          for performance reasons.
        - Classic, one call with projectKeys/issuetypeNames query params.
          Gone on Server/DC 9.0+; still served by Cloud.

        An earlier version of this method called the classic endpoint
        only, on the stated assumption that it was "still the only
        createmeta option on Server/Data Center". That was backwards --
        Cloud kept it, Server removed it -- and on a 9.0+ instance the
        request 404s with {"errorMessages":["Issue Does Not Exist"]},
        because with no createmeta route registered Jira falls through to
        GET /issue/{issueIdOrKey} and reads the literal path segment
        "createmeta" as an issue key. That confusing error is the
        signature of this specific problem.

        So: try modern first (works on 8.4+ and is the only thing that
        works on 9.0+), fall back to classic for older Server and Cloud.

        Returns None if the project or issue type wasn't found -- a
        genuinely different finding from "found but has zero fields", so
        callers can tell "typo'd issue type name" apart from "issue type
        has no custom fields configured at all"."""
        issue_types = self._createmeta_issue_types(project_key)
        if issue_types is not None:
            match = next(
                (
                    it
                    for it in issue_types
                    if str(it.get("name", "")).strip().casefold()
                    == issue_type_name.strip().casefold()
                ),
                None,
            )
            if match is None or not match.get("id"):
                return None
            return self._createmeta_field_map(project_key, str(match["id"]))

        # Pre-8.4 Server, or Cloud: the classic single-call endpoint.
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
