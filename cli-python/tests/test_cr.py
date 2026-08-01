# Unit tests for cr.py's Jira field wiring -- specifically the bug found
# during a field audit: cr_submit hand-builds its `fields` dict rather than
# routing through jira.py's _upsert_issue(), and had silently skipped
# cfg.jira.labels (base_fields.labels) and the team stamp that every other
# issue type (Epic/Story/Task/CHG) gets. Run from repo root: pytest cli-python/tests -q
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from sdd.commands.cr import cr_command
from sdd.utils.atlassian_auth import Profile


class FakeJiraClient:
    """Same shape as the fakes in test_jira_push_levels.py /
    test_review_helpers.py -- records what cr_submit actually sends."""
    def __init__(self, session=None, base_url=None):
        self.created: list[dict] = []
        self.updated: list[tuple[str, dict]] = []

    def find_by_label(self, project_key, label):
        return None   # always "not yet submitted" -- exercises the create path

    def create_issue(self, fields):
        self.created.append(fields)
        return {"key": "PROJ-1"}

    def update_issue(self, key, fields):
        self.updated.append((key, fields))


@pytest.fixture()
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    changesets = tmp_path / ".specify" / "features" / "auth" / "changesets"
    changesets.mkdir(parents=True)
    (changesets / "CR-001.md").write_text(
        "# CR-001\n\nAdd rate limiting to the login endpoint.\n"
    )
    (tmp_path / ".specify" / "manifest.yml").write_text(
        yaml.dump({"project": {"name": "Demo", "feature": "auth"}})
    )
    (tmp_path / ".specify" / "integrations.yml").write_text(
        "profile: default\n"
        "jira:\n"
        "  project_key: MYPROJ\n"
        "  base_fields:\n"
        "    labels: [sdd-generated, org-required-label]\n"
        "    team: Team Phoenix\n"
        "  custom_fields:\n"
        "    team: customfield_20000\n"
    )
    return tmp_path


class TestCrSubmitFieldWiring:
    @pytest.fixture()
    def runner(self):
        return CliRunner()

    def test_labels_and_team_are_sent(self, project, runner):
        fake = FakeJiraClient()
        with patch("sdd.commands.cr.load_jira_session",
                    return_value=(Profile(auth_mode="basic", base_url="https://x.atlassian.net"), object())), \
             patch("sdd.commands.cr.JiraClient", return_value=fake):
            result = runner.invoke(cr_command, ["submit", "--cr", "CR-001"])

        assert result.exit_code == 0, result.output
        assert len(fake.created) == 1
        sent = fake.created[0]
        # base_fields.labels must be present, not silently dropped
        assert "sdd-generated" in sent["labels"]
        assert "org-required-label" in sent["labels"]
        assert "sdd-cr" in sent["labels"]
        # base_fields.team + custom_fields.team must stamp the team field
        assert sent["customfield_20000"] == "Team Phoenix"
