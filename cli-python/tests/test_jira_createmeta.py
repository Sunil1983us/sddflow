# Unit tests for check_epic_createmeta() (sdd/commands/jira.py) and
# JiraClient.get_createmeta_fields() (sdd/utils/jira_client.py) -- the
# `sdd doctor` live check that validates the configured Epic/Feature
# issue type against Jira's own field requirements, so an organization's
# custom issue types and required fields get caught locally instead of
# only surfacing as a failed push.
from __future__ import annotations

from unittest.mock import MagicMock

from sdd.commands.jira import check_epic_createmeta
from sdd.utils.integrations import JiraConfig
from sdd.utils.jira_client import JiraClient


def _cfg(**kw) -> JiraConfig:
    return JiraConfig(project_key="DEMO", **kw)


class FakeCreatemetaClient:
    """Stands in for JiraClient in check_epic_createmeta() tests --
    real HTTP behavior of get_createmeta_fields() is covered separately
    below via TestGetCreatemetaFields, against a mocked session."""

    def __init__(self, fields_meta: dict | None, deployment: str = "server"):
        self.deployment = deployment
        self._fields_meta = fields_meta

    def get_createmeta_fields(self, project_key, issue_type_name):
        return self._fields_meta


class TestIssueTypeNotFound:
    def test_none_fields_meta_reports_issue_type_not_found(self):
        client = FakeCreatemetaClient(fields_meta=None)
        findings = check_epic_createmeta(_cfg(), client)
        assert len(findings) == 1
        ok, message = findings[0]
        assert ok is False
        assert "not found in project" in message
        assert "issue_hierarchy.feature" in message


class TestRequiredFieldCoverage:
    def test_all_required_fields_covered_reports_ok(self):
        fields_meta = {
            "summary": {
                "required": True,
                "name": "Summary",
                "schema": {"type": "string"},
            },
            "description": {
                "required": False,
                "name": "Description",
                "schema": {"type": "string"},
            },
            "priority": {"required": True, "name": "Priority", "schema": {}},
        }
        client = FakeCreatemetaClient(fields_meta)
        findings = check_epic_createmeta(_cfg(), client)
        assert any(
            ok and "every Jira-required field is covered" in msg for ok, msg in findings
        )
        assert all(ok for ok, _ in findings)

    def test_missing_epic_name_field_names_the_fix(self):
        """Regression: this is exactly the real-world gap that started
        this whole investigation -- a classic/company-managed project's
        Epic issue type requires 'Epic Name' and nothing in
        integrations.yml sets it."""
        fields_meta = {
            "summary": {
                "required": True,
                "name": "Summary",
                "schema": {"type": "string"},
            },
            "customfield_10011": {
                "required": True,
                "name": "Epic Name",
                "schema": {"type": "string"},
            },
        }
        client = FakeCreatemetaClient(fields_meta)
        findings = check_epic_createmeta(_cfg(), client)
        failures = [msg for ok, msg in findings if not ok]
        assert any(
            "Epic Name" in msg and "customfield_10011" in msg for msg in failures
        )
        assert any("custom_fields.epic_name" in msg for msg in failures)

    def test_epic_name_configured_is_no_longer_flagged(self):
        fields_meta = {
            "summary": {
                "required": True,
                "name": "Summary",
                "schema": {"type": "string"},
            },
            "customfield_10011": {
                "required": True,
                "name": "Epic Name",
                "schema": {"type": "string"},
            },
        }
        cfg = _cfg(custom_fields={"epic_name": "customfield_10011"})
        client = FakeCreatemetaClient(fields_meta)
        findings = check_epic_createmeta(cfg, client)
        assert all(ok for ok, _ in findings)

    def test_unrecognized_required_custom_field_gets_generic_hint(self):
        """A required field SDD has no field-mapping key for at all (not
        Epic Name, not team) -- can't tell the user which config key to
        set, since none exists; must say so honestly instead of guessing."""
        fields_meta = {
            "summary": {
                "required": True,
                "name": "Summary",
                "schema": {"type": "string"},
            },
            "customfield_99999": {
                "required": True,
                "name": "Cost Center",
                "schema": {"type": "string"},
            },
        }
        client = FakeCreatemetaClient(fields_meta)
        findings = check_epic_createmeta(_cfg(), client)
        failures = [msg for ok, msg in findings if not ok]
        assert any(
            "Cost Center" in msg and "customfield_99999" in msg for msg in failures
        )
        assert any("no integrations.yml field mapping" in msg for msg in failures)

    def test_reporter_required_is_not_flagged(self):
        """Jira commonly marks 'reporter' required even though it
        auto-fills from the authenticated API caller -- must not produce
        a false-positive finding for something that already works."""
        fields_meta = {
            "summary": {
                "required": True,
                "name": "Summary",
                "schema": {"type": "string"},
            },
            "reporter": {"required": True, "name": "Reporter", "schema": {}},
        }
        client = FakeCreatemetaClient(fields_meta)
        findings = check_epic_createmeta(_cfg(), client)
        assert all(ok for ok, _ in findings)

    def test_team_field_configured_and_set_is_not_flagged(self):
        fields_meta = {
            "summary": {
                "required": True,
                "name": "Summary",
                "schema": {"type": "string"},
            },
            "customfield_10100": {"required": True, "name": "Team", "schema": {}},
        }
        cfg = _cfg(custom_fields={"team": "customfield_10100"}, team="Team Phoenix")
        client = FakeCreatemetaClient(fields_meta)
        findings = check_epic_createmeta(cfg, client)
        assert all(ok for ok, _ in findings)

    def test_team_field_id_configured_but_cfg_team_unset_is_still_flagged(self):
        """_apply_team_field() (jira.py) only stamps the team field if
        BOTH custom_fields.team AND base_fields.team (cfg.team) are set
        -- a custom_fields.team entry alone never actually gets sent, so
        this must still be flagged as uncovered."""
        fields_meta = {
            "summary": {
                "required": True,
                "name": "Summary",
                "schema": {"type": "string"},
            },
            "customfield_10100": {"required": True, "name": "Team", "schema": {}},
        }
        cfg = _cfg(custom_fields={"team": "customfield_10100"})  # cfg.team left None
        client = FakeCreatemetaClient(fields_meta)
        findings = check_epic_createmeta(cfg, client)
        assert any(not ok for ok, _ in findings)


class TestDescriptionSchemaCheck:
    def test_server_deployment_string_schema_is_ok(self):
        fields_meta = {
            "description": {
                "required": False,
                "name": "Description",
                "schema": {"type": "string"},
            }
        }
        client = FakeCreatemetaClient(fields_meta, deployment="server")
        findings = check_epic_createmeta(_cfg(), client)
        assert any(
            ok and "format matches this deployment" in msg for ok, msg in findings
        )

    def test_server_deployment_non_string_schema_is_flagged(self):
        fields_meta = {
            "description": {
                "required": False,
                "name": "Description",
                "schema": {"type": "doc"},
            }
        }
        client = FakeCreatemetaClient(fields_meta, deployment="server")
        findings = check_epic_createmeta(_cfg(), client)
        failures = [msg for ok, msg in findings if not ok]
        assert any("schema type is 'doc'" in msg for msg in failures)

    def test_cloud_deployment_non_string_schema_is_not_flagged(self):
        """ADF ('doc'-typed schema) is the expected, correct shape on
        Cloud -- only Server/DC's plain-string requirement makes a
        non-string schema noteworthy."""
        fields_meta = {
            "description": {
                "required": False,
                "name": "Description",
                "schema": {"type": "doc"},
            }
        }
        client = FakeCreatemetaClient(fields_meta, deployment="cloud")
        findings = check_epic_createmeta(_cfg(), client)
        assert all(ok for ok, _ in findings)


def _routed_session(routes: list[tuple[str, int, dict]]) -> MagicMock:
    """A session whose GET picks its response by matching a substring of
    the requested URL, so a two-call flow can be scripted.

    routes: (url_substring, status_code, json_body), first match wins.
    An unmatched URL is a 404 with an empty body, which is what a Jira
    that doesn't serve that route effectively does."""
    session = MagicMock()

    def _get(url, **kwargs):
        response = MagicMock()
        for needle, status, body in routes:
            if needle in url:
                response.status_code = status
                response.json.return_value = body
                response.text = str(body)
                response.raise_for_status.return_value = None
                return response
        response.status_code = 404
        response.json.return_value = {}
        response.text = ""
        response.raise_for_status.return_value = None
        return response

    session.get.side_effect = _get
    return session


# The modern endpoint's response envelope. The shape is the point, and
# it is what the classic endpoint did not do: rows live under "values"
# rather than at the top level, issue type ids are strings not ints, and
# the payload is paginated. A custom issue type sits alongside the stock
# ones because resolving a name that this codebase cannot know about in
# advance is the whole reason the lookup exists.
_ISSUETYPES_PAGE = {
    "maxResults": 50,
    "startAt": 0,
    "total": 6,
    "isLast": True,
    "values": [
        {"id": "10001", "name": "Bug", "subtask": False},
        {"id": "10002", "name": "Story", "subtask": False},
        {"id": "10003", "name": "Task", "subtask": False},
        {"id": "10004", "name": "Sub-task", "subtask": True},
        {"id": "10005", "name": "Spike", "subtask": False},
        {"id": "10006", "name": "Change Request", "subtask": False},
    ],
}


class TestGetCreatemetaFieldsModern:
    """Jira 8.4+ / 9.0+ two-call path. From 9.0 this is the ONLY path --
    the classic query-param endpoint was removed outright."""

    def test_resolves_issue_type_by_name_then_fetches_that_type_fields(self):
        session = _routed_session(
            [
                (
                    "/issue/createmeta/DEMO/issuetypes/10002",
                    200,
                    {
                        "isLast": True,
                        "values": [
                            {
                                "fieldId": "summary",
                                "name": "Summary",
                                "required": True,
                            },
                            {
                                "fieldId": "customfield_10001",
                                "name": "Epic Name",
                                "required": True,
                            },
                        ],
                    },
                ),
                ("/issue/createmeta/DEMO/issuetypes", 200, _ISSUETYPES_PAGE),
            ]
        )
        client = JiraClient(session, "https://jira.example.net", deployment="server")
        result = client.get_createmeta_fields("DEMO", "Story")
        assert result == {
            "summary": {"fieldId": "summary", "name": "Summary", "required": True},
            "customfield_10001": {
                "fieldId": "customfield_10001",
                "name": "Epic Name",
                "required": True,
            },
        }

    def test_issue_type_match_is_case_insensitive(self):
        session = _routed_session(
            [
                (
                    "/issue/createmeta/DEMO/issuetypes/10002",
                    200,
                    {"isLast": True, "values": []},
                ),
                ("/issue/createmeta/DEMO/issuetypes", 200, _ISSUETYPES_PAGE),
            ]
        )
        client = JiraClient(session, "https://jira.example.net", deployment="server")
        assert client.get_createmeta_fields("DEMO", "story") == {}

    def test_returns_none_when_issue_type_name_is_not_in_the_project(self):
        session = _routed_session(
            [("/issue/createmeta/DEMO/issuetypes", 200, _ISSUETYPES_PAGE)]
        )
        client = JiraClient(session, "https://jira.example.net", deployment="server")
        assert client.get_createmeta_fields("DEMO", "NotARealType") is None

    def test_never_calls_the_removed_classic_endpoint_when_modern_answers(self):
        session = _routed_session(
            [
                (
                    "/issue/createmeta/DEMO/issuetypes/10002",
                    200,
                    {"isLast": True, "values": []},
                ),
                ("/issue/createmeta/DEMO/issuetypes", 200, _ISSUETYPES_PAGE),
            ]
        )
        client = JiraClient(session, "https://jira.example.net", deployment="server")
        client.get_createmeta_fields("DEMO", "Story")
        for call in session.get.call_args_list:
            assert "projectKeys" not in (call.kwargs.get("params") or {})

    def test_follows_pagination_when_isLast_is_false(self):
        page_one = {
            "isLast": False,
            "values": [{"id": "9", "name": "Other", "subtask": False}],
        }
        calls = {"n": 0}

        def _get(url, **kwargs):
            response = MagicMock()
            response.status_code = 200
            response.raise_for_status.return_value = None
            if "/issuetypes/10002" in url:
                response.json.return_value = {"isLast": True, "values": []}
            elif "/issuetypes" in url:
                calls["n"] += 1
                response.json.return_value = (
                    page_one if calls["n"] == 1 else _ISSUETYPES_PAGE
                )
            return response

        session = MagicMock()
        session.get.side_effect = _get
        client = JiraClient(session, "https://jira.example.net", deployment="server")
        # "Story" is only on the second page -- a non-paging implementation
        # would return None here.
        assert client.get_createmeta_fields("DEMO", "Story") == {}
        assert calls["n"] == 2

    def test_accepts_a_classic_shaped_fields_dict_from_the_modern_url(self):
        """Defensive: not every Jira version was verifiable, so a server
        answering the per-issue-type URL with the old {'fields': {...}}
        dict is passed straight through rather than read as empty."""
        session = _routed_session(
            [
                (
                    "/issue/createmeta/DEMO/issuetypes/10002",
                    200,
                    {"fields": {"summary": {"required": True}}},
                ),
                ("/issue/createmeta/DEMO/issuetypes", 200, _ISSUETYPES_PAGE),
            ]
        )
        client = JiraClient(session, "https://jira.example.net", deployment="server")
        assert client.get_createmeta_fields("DEMO", "Story") == {
            "summary": {"required": True}
        }


class TestGetCreatemetaFieldsClassicFallback:
    """Pre-8.4 Server and Cloud, where the modern per-project endpoint is
    absent (404) and the classic query-param one still answers."""

    def _client(self, classic_body: dict) -> tuple[JiraClient, MagicMock]:
        # Routed on the URL's tail rather than via _routed_session: requests
        # puts query params in kwargs, so the classic call arrives as a bare
        # "/issue/createmeta" and would otherwise also match the modern
        # "/issue/createmeta/{key}/issuetypes" substring.
        session = MagicMock()

        def _get(url, **kwargs):
            response = MagicMock()
            response.raise_for_status.return_value = None
            if url.endswith("/issue/createmeta"):
                response.status_code = 200
                response.json.return_value = classic_body
            else:
                response.status_code = 404
                response.json.return_value = {}
            return response

        session.get.side_effect = _get
        client = JiraClient(session, "https://example.atlassian.net")
        return client, session

    def test_falls_back_with_project_and_issuetype_params(self):
        client, session = self._client({"projects": [{"issuetypes": [{"fields": {}}]}]})
        client.get_createmeta_fields("DEMO", "Change Request")
        classic = [
            c
            for c in session.get.call_args_list
            if c.args[0].endswith("/issue/createmeta")
        ]
        assert len(classic) == 1
        assert classic[0].kwargs["params"] == {
            "projectKeys": "DEMO",
            "issuetypeNames": "Change Request",
            "expand": "projects.issuetypes.fields",
        }

    def test_returns_fields_dict_when_found(self):
        client, _session = self._client(
            {
                "projects": [
                    {"issuetypes": [{"fields": {"summary": {"required": True}}}]}
                ]
            }
        )
        assert client.get_createmeta_fields("DEMO", "Epic") == {
            "summary": {"required": True}
        }

    def test_returns_none_when_no_projects_match(self):
        client, _session = self._client({"projects": []})
        assert client.get_createmeta_fields("NOPE", "Epic") is None

    def test_returns_none_when_project_has_no_matching_issuetype(self):
        client, _session = self._client({"projects": [{"issuetypes": []}]})
        assert client.get_createmeta_fields("DEMO", "NotARealType") is None
