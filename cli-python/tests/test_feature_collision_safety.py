"""Regression tests for the multi-feature Confluence/Jira title-collision
class of bug: a page title or Jira idempotency label that doesn't
distinguish one feature from another silently causes a second feature's
push to upsert onto (Confluence) or find-and-reuse (Jira) the first
feature's page/ticket, overwriting its content.

Covers:
- confluence.py's feature_collision_warning() and its wiring into
  `sdd confluence push`/`draft` (--force gate)
- config.py's scaffolded page_map template (was missing {feature} for
  every per-feature doc key)
- integrations.py's _DEFAULT_PAGE_MAP fallback (same gap)
- review.py's Jira review Story / Open Questions summaries (feature name
  was missing from the display text, though the underlying ticket lookup
  was already label-scoped and safe)
- cr.py's Jira idempotency label (was NOT feature-qualified at all -- a
  real ticket-identity collision, not just a display issue, since CHG-NNN
  ids are scoped per feature's own tasks.md counter, not globally unique)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from sdd.commands.config import _integrations_template
from sdd.commands.confluence import confluence_command, feature_collision_warning
from sdd.commands.cr import cr_command
from sdd.utils.atlassian_auth import Profile
from sdd.utils.integrations import _DEFAULT_PAGE_MAP


class TestFeatureCollisionWarning:
    def test_single_feature_project_is_always_safe(self, tmp_path):
        (tmp_path / ".specify" / "features" / "auth").mkdir(parents=True)
        warning = feature_collision_warning(
            "Demo — Business Requirements", "auth", root=tmp_path
        )
        assert warning is None

    def test_title_already_including_feature_name_is_safe(self, tmp_path):
        (tmp_path / ".specify" / "features" / "auth").mkdir(parents=True)
        (tmp_path / ".specify" / "features" / "billing").mkdir(parents=True)
        warning = feature_collision_warning(
            "auth — Business Requirements", "auth", root=tmp_path
        )
        assert warning is None

    def test_multi_feature_project_with_generic_title_warns(self, tmp_path):
        (tmp_path / ".specify" / "features" / "auth").mkdir(parents=True)
        (tmp_path / ".specify" / "features" / "billing").mkdir(parents=True)
        warning = feature_collision_warning(
            "Demo — Business Requirements", "auth", root=tmp_path
        )
        assert warning is not None
        assert "billing" in warning
        assert "--force" in warning

    def test_no_features_dir_is_safe(self, tmp_path):
        warning = feature_collision_warning("Demo — BRD", "auth", root=tmp_path)
        assert warning is None


class TestConfigScaffoldIncludesFeature:
    """config.py's _integrations_template() is what `sdd config init`
    actually writes -- it must match integrations.yml.example's
    already-correct {feature}-inclusive titles, not the stale
    {project}-only titles it previously scaffolded."""

    def test_per_feature_doc_titles_include_feature_placeholder(self):
        rendered = _integrations_template("default", "PROJ", "SPACE", "", "Validation")
        data = yaml.safe_load(rendered)
        page_map = data["confluence"]["page_map"]
        for key in (
            "brd",
            "use-cases",
            "srd",
            "design",
            "arch",
            "hld",
            "adr",
            "lld",
        ):
            assert "{feature}" in page_map[key], f"{key}: {page_map[key]!r}"

    def test_living_and_project_wide_entries_do_not_need_feature(self):
        rendered = _integrations_template("default", "PROJ", "SPACE", "", "Validation")
        data = yaml.safe_load(rendered)
        page_map = data["confluence"]["page_map"]
        # runbook/constitution are project-wide; their title value is
        # baked with the real project name directly (no placeholder left
        # to substitute at push time).
        assert page_map["runbook"] == "Validation — Runbook"
        assert page_map["constitution"] == "Validation — Constitution"

    def test_two_features_resolve_to_distinct_titles(self):
        from sdd.commands.confluence import _resolve_page_title

        rendered = _integrations_template("default", "PROJ", "SPACE", "", "Validation")
        page_map = yaml.safe_load(rendered)["confluence"]["page_map"]
        for doc in ("brd", "use-cases", "srd"):
            t1 = _resolve_page_title(doc, "Validation", "validation-service", page_map)
            t2 = _resolve_page_title(doc, "Validation", "rule-management-ui", page_map)
            assert t1 != t2, f"{doc}: both resolved to {t1!r}"


class TestDefaultPageMapFallbackIncludesFeature:
    def test_per_feature_keys_include_feature_placeholder(self):
        for key in ("brd", "use-cases", "srd", "design", "arch", "hld", "adr", "lld"):
            assert "{feature}" in _DEFAULT_PAGE_MAP[key], (
                f"{key}: {_DEFAULT_PAGE_MAP[key]!r}"
            )


class TestConfluencePushForceGate:
    @pytest.fixture()
    def multi_feature_project(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        for feature in ("validation-service", "rule-management-ui"):
            fd = tmp_path / ".specify" / "features" / feature
            fd.mkdir(parents=True)
            (fd / "brd.md").write_text(f"# BRD for {feature}\n")
        (tmp_path / ".specify" / "manifest.yml").write_text(
            yaml.dump(
                {"project": {"name": "Validation", "feature": "validation-service"}}
            )
        )
        (tmp_path / ".specify" / "integrations.yml").write_text(
            "profile: default\n"
            "confluence:\n"
            "  space_key: SPACE\n"
            "  page_map:\n"
            # Deliberately the OLD, stale, {feature}-less title -- this is
            # what an existing project's already-scaffolded integrations.yml
            # looks like if it predates the config.py fix above.
            '    brd: "{project} — Business Requirements"\n'
        )
        return tmp_path

    def test_push_refuses_without_force_when_collision_risk(
        self, multi_feature_project
    ):
        result = CliRunner().invoke(
            confluence_command, ["push", "--doc", "brd", "--dry-run"]
        )
        # dry-run never blocks -- it's informational only, printing the
        # collision-risk flag inline (see the actual push test below for
        # the blocking case).
        assert result.exit_code == 0
        assert "collision risk" in result.output

    def test_push_blocks_for_real_without_force(self, multi_feature_project):
        result = CliRunner().invoke(confluence_command, ["push", "--doc", "brd"])
        assert result.exit_code == 1
        assert "Refusing to push" in result.output

    def test_push_proceeds_with_force(self, multi_feature_project):
        class FakeClient:
            def __init__(self, *a, **k):
                pass

            def get_page_by_title(self, *a, **k):
                return None

            def create_page(self, *a, **k):
                return {"id": "1", "_links": {}}

            def update_page(self, *a, **k):
                return {"id": "1", "_links": {}}

            def upsert_page(self, *a, **k):
                return {"id": "1", "_links": {}}, True

        with (
            patch(
                "sdd.commands.confluence.load_confluence_session",
                return_value=(
                    Profile(auth_mode="basic", base_url="https://x.atlassian.net"),
                    object(),
                ),
            ),
            patch("sdd.commands.confluence.ConfluenceClient", FakeClient),
        ):
            result = CliRunner().invoke(
                confluence_command, ["push", "--doc", "brd", "--force"]
            )
        assert result.exit_code == 0, result.output
        assert "created" in result.output or "updated" in result.output


class FakeJiraClient:
    """In-memory double -- create_issue auto-indexes by every 'sdd*' label
    so find_by_label round-trips, same convention as the fakes in
    test_review_helpers.py / test_jira_push_levels.py."""

    def __init__(self, session=None, base_url=None):
        self.by_label: dict[str, dict] = {}
        self.created: list[dict] = []
        self._next_id = 1

    def find_by_label(self, project_key, label):
        return self.by_label.get(label)

    def create_issue(self, fields):
        key = f"PROJ-{self._next_id}"
        self._next_id += 1
        self.created.append(fields)
        for label in fields.get("labels", []):
            if label.startswith("sdd"):
                self.by_label[label] = {"key": key, "fields": fields}
        return {"key": key}

    def update_issue(self, key, fields):
        pass

    def set_parent(self, child_key, parent_key, parent_field):
        pass


@pytest.fixture()
def two_feature_cr_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for feature in ("validation-service", "rule-management-ui"):
        changesets = tmp_path / ".specify" / "features" / feature / "changesets"
        changesets.mkdir(parents=True)
        (changesets / "CHG-001.md").write_text(f"# CHG-001\n\nChange for {feature}.\n")
    (tmp_path / ".specify" / "integrations.yml").write_text(
        "profile: default\njira:\n  project_key: PROJ\n"
    )
    return tmp_path


class TestCrFeatureQualifiedLabel:
    """Regression: cr_submit's Jira idempotency label used to be plain
    f"sdd-cr:{cr_id.lower()}" with no feature qualifier at all -- since
    CHG-NNN numbering is per-feature (not globally unique), two features
    each having their own "CHG-001" would resolve to the SAME Jira ticket
    via this label lookup, not just a title-display collision."""

    def _patch_jira(self, fake):
        return (
            patch(
                "sdd.commands.cr.load_jira_session",
                return_value=(
                    Profile(auth_mode="basic", base_url="https://x.atlassian.net"),
                    object(),
                ),
            ),
            patch("sdd.commands.cr.JiraClient", return_value=fake),
        )

    def test_same_cr_id_two_features_create_separate_tickets(
        self, two_feature_cr_project
    ):
        fake = FakeJiraClient()
        p1, p2 = self._patch_jira(fake)
        runner = CliRunner()
        with p1, p2:
            r1 = runner.invoke(
                cr_command,
                ["submit", "--cr", "CHG-001", "--feature", "validation-service"],
            )
            r2 = runner.invoke(
                cr_command,
                ["submit", "--cr", "CHG-001", "--feature", "rule-management-ui"],
            )
        assert r1.exit_code == 0, r1.output
        assert r2.exit_code == 0, r2.output
        cr_tickets = [f for f in fake.created if f["summary"].startswith("Review:")]
        # Two genuinely separate tickets, not one create + one silent reuse.
        assert len(cr_tickets) == 2
        summaries = {f["summary"] for f in cr_tickets}
        assert len(summaries) == 2  # distinct summary text too

    def test_cr_check_finds_the_ticket_cr_submit_created(self, two_feature_cr_project):
        fake = FakeJiraClient()
        p1, p2 = self._patch_jira(fake)
        runner = CliRunner()
        with p1, p2:
            submit_result = runner.invoke(
                cr_command,
                ["submit", "--cr", "CHG-001", "--feature", "validation-service"],
            )
            assert submit_result.exit_code == 0, submit_result.output
            check_result = runner.invoke(
                cr_command,
                ["check", "--cr", "CHG-001", "--feature", "validation-service"],
            )
        # Must find the ticket (not "NOT SUBMITTED") -- proves cr_check's
        # lookup label matches cr_submit's exactly.
        assert "NOT SUBMITTED" not in check_result.output, check_result.output

    def test_cr_check_does_not_cross_features(self, two_feature_cr_project):
        fake = FakeJiraClient()
        p1, p2 = self._patch_jira(fake)
        runner = CliRunner()
        with p1, p2:
            runner.invoke(
                cr_command,
                ["submit", "--cr", "CHG-001", "--feature", "validation-service"],
            )
            # rule-management-ui never submitted its own CHG-001.
            check_result = runner.invoke(
                cr_command,
                ["check", "--cr", "CHG-001", "--feature", "rule-management-ui"],
            )
        assert "NOT SUBMITTED" in check_result.output, check_result.output
