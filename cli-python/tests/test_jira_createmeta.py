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
    return JiraConfig(project_key="FRAML", **kw)


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


class TestGetCreatemetaFields:
    def _client_with_mock_session(
        self, json_body: dict
    ) -> tuple[JiraClient, MagicMock]:
        session = MagicMock()
        response = MagicMock()
        response.json.return_value = json_body
        response.raise_for_status.return_value = None
        session.get.return_value = response
        client = JiraClient(session, "https://example.atlassian.net")
        return client, session

    def test_queries_createmeta_with_project_and_issuetype_params(self):
        client, session = self._client_with_mock_session(
            {"projects": [{"issuetypes": [{"fields": {}}]}]}
        )
        client.get_createmeta_fields("FRAML", "SAFe Enabler")
        params = session.get.call_args.kwargs["params"]
        assert params == {
            "projectKeys": "FRAML",
            "issuetypeNames": "SAFe Enabler",
            "expand": "projects.issuetypes.fields",
        }

    def test_returns_fields_dict_when_found(self):
        client, _session = self._client_with_mock_session(
            {
                "projects": [
                    {"issuetypes": [{"fields": {"summary": {"required": True}}}]}
                ]
            }
        )
        result = client.get_createmeta_fields("FRAML", "Epic")
        assert result == {"summary": {"required": True}}

    def test_returns_none_when_no_projects_match(self):
        client, _session = self._client_with_mock_session({"projects": []})
        assert client.get_createmeta_fields("NOPE", "Epic") is None

    def test_returns_none_when_project_has_no_matching_issuetype(self):
        client, _session = self._client_with_mock_session(
            {"projects": [{"issuetypes": []}]}
        )
        assert client.get_createmeta_fields("FRAML", "NotARealType") is None
