# Unit tests for the review-approval helpers — the no-Jira/chat approval path.
# Run from repo root:  pytest cli-python/tests -q
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from sdd.commands import review
from sdd.utils.integrations import JiraConfig, IntegrationsConfig


@pytest.fixture()
def project(tmp_path, monkeypatch):
    """Minimal .specify project rooted in a temp dir; cwd switched into it."""
    monkeypatch.chdir(tmp_path)
    features = tmp_path / ".specify" / "features" / "auth"
    features.mkdir(parents=True)
    (tmp_path / ".specify" / "manifest.yml").write_text(
        yaml.dump({"project": {"name": "Demo", "feature": "auth"}})
    )
    return tmp_path


def _write_doc(project, name, header):
    p = project / ".specify" / "features" / "auth" / f"{name}.md"
    p.write_text(f"# Doc\n> Version: 1.0 | {header} | Date: x | Author: y\n\nbody\n")
    return p


class TestMarkMdApproved:
    @pytest.mark.parametrize("header", ["Status: Draft", "Status: DRAFT",
                                        "Status: draft", "Status: Proposed",
                                        "Status: PROPOSED"])
    def test_flips_pre_approval_statuses(self, project, header):
        p = _write_doc(project, "brd", header)
        assert review._mark_md_approved(p) is True
        assert "Status: Approved" in p.read_text()

    def test_already_approved_is_noop(self, project):
        p = _write_doc(project, "brd", "Status: Approved")
        assert review._mark_md_approved(p) is False
        assert p.read_text().count("Status: Approved") == 1

    def test_only_first_occurrence_flipped(self, project):
        p = project / ".specify" / "features" / "auth" / "brd.md"
        p.write_text("> Status: Draft |\n\nBody mentions Status: Draft again\n")
        review._mark_md_approved(p)
        text = p.read_text()
        assert text.startswith("> Status: Approved |")
        assert "Status: Draft again" in text  # body untouched

    def test_does_not_match_draft_inside_words(self, project):
        p = project / ".specify" / "features" / "auth" / "brd.md"
        p.write_text("> Status: Drafted |\n")
        assert review._mark_md_approved(p) is False


class TestMarkApprovalsTable:
    def _doc_with_approvals(self, project, rows):
        table = "\n".join(f"| {role} | Pending | |" for role in rows)
        text = (
            "# Doc\n> Version: 1.0 | Status: Draft | Date: x | Author: y\n\n"
            f"## Approvals\n\n| Role | Status | Date |\n|---|---|---|\n{table}\n\n"
            "## Version History\n\n| Version | Date |\n|---|---|\n| 1.0 | x |\n"
        )
        p = project / ".specify" / "features" / "auth" / "brd.md"
        p.write_text(text)
        return p

    def test_single_row_flipped_with_date(self, project):
        p = self._doc_with_approvals(project, ["Product Owner (accountable)"])
        review._mark_md_approved(p)
        text = p.read_text()
        assert "| Product Owner (accountable) | Approved |" in text
        assert "| Pending |" not in text

    def test_all_rows_in_multi_row_table_flipped(self, project):
        p = self._doc_with_approvals(project, ["Architect", "Tech Lead", "Stakeholder (HLD sign-off)"])
        review._mark_md_approved(p)
        text = p.read_text()
        assert text.count("| Approved |") == 3
        assert "Pending" not in text

    def test_blank_line_before_next_heading_preserved(self, project):
        p = self._doc_with_approvals(project, ["Product Owner"])
        review._mark_md_approved(p)
        text = p.read_text()
        assert "\n\n## Version History" in text

    def test_no_approvals_section_is_noop(self, project):
        p = _write_doc(project, "brd", "Status: Draft")
        before = p.read_text()
        review._mark_md_approved(p)
        after = p.read_text()
        assert "Status: Approved" in after  # header still flips
        assert after.replace("Status: Approved", "Status: Draft") == before  # nothing else changed

    def test_self_heals_stale_table_when_header_already_approved(self, project):
        """Regression: header was flipped by an older version of this code
        that only touched the header, leaving the Approvals table stale."""
        p = self._doc_with_approvals(project, ["Product Owner"])
        text = p.read_text().replace("Status: Draft", "Status: Approved")
        p.write_text(text)
        assert review._mark_md_approved(p) is True
        assert "| Approved |" in p.read_text()
        assert "Pending" not in p.read_text()

    def test_already_approved_rows_left_alone(self, project):
        p = self._doc_with_approvals(project, ["Product Owner"])
        review._mark_md_approved(p)  # first pass: Pending -> Approved (today)
        first = p.read_text()
        assert review._mark_md_approved(p) is False  # second pass: nothing left to change
        assert p.read_text() == first


class TestLocalApprovals:
    def test_save_and_load_roundtrip(self, project):
        review._save_local_approval("brd", "Product Owner", "approved in chat")
        approvals = review._load_local_approvals()
        assert approvals["brd"]["approved_by"] == "Product Owner"
        assert approvals["brd"]["note"] == "approved in chat"
        assert review._is_locally_approved("brd")
        assert not review._is_locally_approved("srd")

    def test_second_approval_does_not_clobber_first(self, project):
        review._save_local_approval("brd", "PO")
        review._save_local_approval("srd", "BA")
        approvals = review._load_local_approvals()
        assert set(approvals) == {"brd", "srd"}

    def test_file_is_valid_yaml_with_comment_header(self, project):
        review._save_local_approval("brd", "PO")
        raw = Path(".specify/.local-approvals.yml").read_text()
        assert raw.startswith("#")
        assert yaml.safe_load(raw)["brd"]["approved_by"] == "PO"


class TestDocMdPath:
    def test_resolves_from_manifest_feature(self, project):
        p = review._doc_md_path("brd", None)
        assert p == Path(".specify/features/auth/brd.md")

    def test_explicit_feature_overrides_manifest(self, project):
        p = review._doc_md_path("brd", "other")
        assert p == Path(".specify/features/other/brd.md")

    def test_path_escape_rejected(self, project):
        assert review._doc_md_path("brd", "../../etc") is None

    def test_no_feature_anywhere_returns_none(self, project, monkeypatch):
        (project / ".specify" / "manifest.yml").write_text(yaml.dump({"project": {}}))
        assert review._doc_md_path("brd", None) is None


class TestPushDocPage:
    def test_no_integrations_file_returns_none(self, project):
        p = _write_doc(project, "brd", "Status: Approved")
        assert review._push_doc_page("brd", p, "auth") is None

    def test_no_confluence_section_returns_none(self, project):
        (project / ".specify" / "integrations.yml").write_text("profile: default\n")
        p = _write_doc(project, "brd", "Status: Approved")
        assert review._push_doc_page("brd", p, "auth") is None


# ── _ensure_epic / feature-qualified review labels ──────────────────────────

class FakeJiraClient:
    """In-memory double — enough surface for _ensure_epic/_get_review_status,
    no real HTTP. Mirrors the fake used in test_jira_push_content.py."""
    def __init__(self):
        self.by_label: dict[str, dict] = {}
        self.created: list[dict] = []
        self.updated: list[tuple[str, dict]] = []
        self.parents: list[tuple[str, str, str]] = []
        self.comments_by_key: dict[str, list[dict]] = {}
        self.added_comments: list[tuple[str, str]] = []
        self._next_key = 1

    def find_by_label(self, project_key, label):
        return self.by_label.get(label)

    def add_comment(self, issue_key, text):
        self.added_comments.append((issue_key, text))

    def create_issue(self, fields):
        key = f"PROJ-{self._next_key}"
        self._next_key += 1
        self.created.append(fields)
        for label in fields.get("labels", []):
            if label.startswith("sdd"):
                self.by_label[label] = {"key": key, "fields": fields}
        return {"key": key}

    def update_issue(self, key, fields):
        self.updated.append((key, fields))

    def set_parent(self, child_key, parent_key, parent_field="parent"):
        self.parents.append((child_key, parent_key, parent_field))

    def get_comments(self, key):
        return self.comments_by_key.get(key, [])


class RaisingParentClient(FakeJiraClient):
    """set_parent always fails, like a company-managed Jira project
    rejecting the "parent" field — used to confirm a failed review-ticket
    link now prints a diagnosable warning instead of vanishing silently
    (regression test for the bug found during manual QA)."""
    def set_parent(self, child_key, parent_key, parent_field="parent"):
        raise RuntimeError('HTTP 400 — cannot set field "parent"')


class TestLinkReviewStoryToEpic:
    def test_success_records_the_link(self, project):
        client = FakeJiraClient()
        cfg = JiraConfig(project_key="MYPROJ")
        review._link_review_story_to_epic(client, "PROJ-2", "PROJ-1", cfg)
        assert client.parents == [("PROJ-2", "PROJ-1", "parent")]

    def test_uses_review_level_parent_field_override(self, project):
        """parent_field_by_level: {review: ...} must steer how the review
        Story links to its Epic, independently of the base parent_field."""
        client = FakeJiraClient()
        cfg = JiraConfig(project_key="MYPROJ",
                          parent_field_by_level={"review": "customfield_10014"})
        review._link_review_story_to_epic(client, "PROJ-2", "PROJ-1", cfg)
        assert client.parents == [("PROJ-2", "PROJ-1", "customfield_10014")]

    def test_failure_prints_diagnosable_warning(self, project, capsys):
        client = RaisingParentClient()
        cfg = JiraConfig(project_key="MYPROJ")
        review._link_review_story_to_epic(client, "PROJ-2", "PROJ-1", cfg)
        out = capsys.readouterr().out
        assert "was not linked under" in out
        assert "PROJ-1" in out
        assert "cannot set field" in out

    def test_failure_does_not_raise(self, project):
        """A failed link must never propagate -- the review ticket itself
        was already created successfully."""
        client = RaisingParentClient()
        cfg = JiraConfig(project_key="MYPROJ")
        review._link_review_story_to_epic(client, "PROJ-2", "PROJ-1", cfg)  # no raise

    def test_failure_warning_names_the_review_override_project_key(self, project, capsys):
        """The 'sdd config fields --project X' hint in a failed-link warning
        must name the project the review Story actually lives in, not the
        base project_key, when project_keys overrides "review"."""
        client = RaisingParentClient()
        cfg = JiraConfig(project_key="SUN", project_keys={"review": "SUNR"})
        review._link_review_story_to_epic(client, "PROJ-2", "PROJ-1", cfg)
        out = capsys.readouterr().out
        assert "--project SUNR" in out


class TestEnsureEpic:
    def test_creates_epic_from_brd_objectives(self, project):
        (project / ".specify" / "features" / "auth" / "brd.md").write_text(
            "BO-001 Reduce login friction significantly\n"
        )
        client = FakeJiraClient()
        cfg = JiraConfig(project_key="MYPROJ")
        key = review._ensure_epic(client, cfg, "auth")

        assert key == "PROJ-1"
        assert "sdd-feature:auth" in client.created[0]["labels"]

    def test_creates_epic_under_feature_project_keys_override(self, project):
        """project_keys: {feature: ...} must steer the Epic's own project,
        not just the review Stories parented under it."""
        client = FakeJiraClient()
        cfg = JiraConfig(project_key="SUN", project_keys={"feature": "SUNF"})
        review._ensure_epic(client, cfg, "auth")
        assert client.created[0]["project"]["key"] == "SUNF"

    def test_idempotent_second_call_updates_not_creates(self, project):
        client = FakeJiraClient()
        cfg = JiraConfig(project_key="MYPROJ")
        first = review._ensure_epic(client, cfg, "auth")
        second = review._ensure_epic(client, cfg, "auth")

        assert first == second
        assert len(client.created) == 1
        assert len(client.updated) == 1

    def test_returns_none_and_warns_on_failure(self, project):
        class BrokenClient(FakeJiraClient):
            def find_by_label(self, project_key, label):
                raise RuntimeError("network down")

        cfg = JiraConfig(project_key="MYPROJ")
        assert review._ensure_epic(BrokenClient(), cfg, "auth") is None


class TestRecordConfluenceDraftLink:
    def test_writes_entry_compatible_with_confluence_load_drafts(self, project):
        from sdd.commands.confluence import _load_drafts

        page = {"id": "12345", "_links": {"webui": "/spaces/X/pages/12345"}}
        review._record_confluence_draft_link("brd", page, "Demo — Business Requirements")

        drafts = _load_drafts()
        assert drafts["brd"] == {"page_id": "12345", "title": "Demo — Business Requirements"}

    def test_preserves_other_docs_already_recorded(self, project):
        from sdd.commands.confluence import _load_drafts, _save_drafts

        _save_drafts({"srd": {"page_id": "999", "title": "Old SRD"}})
        review._record_confluence_draft_link("brd", {"id": "1"}, "New BRD")

        drafts = _load_drafts()
        assert drafts["srd"] == {"page_id": "999", "title": "Old SRD"}
        assert drafts["brd"] == {"page_id": "1", "title": "New BRD"}

    def test_overwrites_stale_entry_for_same_doc(self, project):
        from sdd.commands.confluence import _load_drafts, _save_drafts

        _save_drafts({"brd": {"page_id": "old-id", "title": "Stale title"}})
        review._record_confluence_draft_link("brd", {"id": "new-id"}, "Fresh title")

        drafts = _load_drafts()
        assert drafts["brd"] == {"page_id": "new-id", "title": "Fresh title"}


class TestRecordReviewLink:
    def test_writes_entry_readable_by_load_review_links(self, project):
        review._record_review_link("brd", "PROJ-9")
        links = review._load_review_links()
        assert links["brd"] == {"key": "PROJ-9"}

    def test_preserves_other_docs_already_recorded(self, project):
        review._save_review_links({"srd": {"key": "PROJ-1"}})
        review._record_review_link("brd", "PROJ-9")
        links = review._load_review_links()
        assert links["srd"] == {"key": "PROJ-1"}
        assert links["brd"] == {"key": "PROJ-9"}

    def test_overwrites_stale_entry_for_same_doc(self, project):
        review._save_review_links({"brd": {"key": "OLD-1"}})
        review._record_review_link("brd", "NEW-2")
        links = review._load_review_links()
        assert links["brd"] == {"key": "NEW-2"}


class TestGetReviewStatusFeatureQualified:
    def _cfg(self):
        return IntegrationsConfig(profile=None, jira=JiraConfig(project_key="MYPROJ"),
                                   confluence=None)

    def test_label_is_feature_qualified(self, project):
        client = FakeJiraClient()
        client.by_label["sdd-doc:auth:brd"] = {
            "key": "PROJ-1",
            "fields": {"status": {"name": "Done"}},
        }
        status, _ = review._get_review_status("brd", client, "MYPROJ", self._cfg(), "auth")
        assert status == "APPROVED"

    def test_unqualified_label_is_not_found(self, project):
        """A ticket registered under the old bare 'sdd-doc:brd' label must
        not be matched — this is the exact collision class fixed for
        Story/Task labels earlier; review labels get the same treatment."""
        client = FakeJiraClient()
        client.by_label["sdd-doc:brd"] = {
            "key": "PROJ-1",
            "fields": {"status": {"name": "Done"}},
        }
        status, _ = review._get_review_status("brd", client, "MYPROJ", self._cfg(), "auth")
        assert status == "NOT_SUBMITTED"

    def test_different_features_do_not_collide(self, project):
        client = FakeJiraClient()
        client.by_label["sdd-doc:auth:brd"] = {
            "key": "PROJ-1",
            "fields": {"status": {"name": "Done"}},
        }
        status, _ = review._get_review_status("brd", client, "MYPROJ", self._cfg(), "billing")
        assert status == "NOT_SUBMITTED"


# ── review_submit end-to-end: labels/team field wiring ──────────────────────
# review_submit() hand-builds its Jira `fields` dict rather than routing
# through jira.py's _upsert_issue() -- a field audit found it had silently
# skipped cfg.jira.labels (base_fields.labels) and the team stamp that every
# other issue type (Epic/Story/Task/CHG) gets. These tests exercise the full
# command (mocking only the HTTP-touching client classes) to catch a
# regression at the one place the bug actually manifested, not just at the
# level of the helper functions already covered above.

class FakeConfluenceClient:
    def __init__(self, session=None, base_url=None):
        self.pages_by_title: dict[str, dict] = {}
        self._next_id = 1

    def get_page_by_title(self, space_key, title):
        return self.pages_by_title.get(title)

    def create_page(self, space_key, title, body_html, parent_id=None):
        page = {"id": str(self._next_id), "_links": {"webui": f"/pages/{self._next_id}"}}
        self._next_id += 1
        self.pages_by_title[title] = page
        return page

    def upsert_page(self, space_key, title, body_html, parent_id=None):
        existing = self.get_page_by_title(space_key, title)
        if existing:
            return existing, False
        return self.create_page(space_key, title, body_html, parent_id), True


class TestReviewSubmitFieldWiring:
    @pytest.fixture()
    def runner(self):
        from click.testing import CliRunner
        return CliRunner()

    @pytest.fixture()
    def review_project(self, project):
        (project / ".specify" / "features" / "auth" / "brd.md").write_text(
            "# BRD\n\nBO-001 Reduce login friction.\n"
        )
        (project / ".specify" / "integrations.yml").write_text(
            "profile: default\n"
            "jira:\n"
            "  project_key: MYPROJ\n"
            "  base_fields:\n"
            "    labels: [sdd-generated, org-required-label]\n"
            "    team: Team Phoenix\n"
            "  custom_fields:\n"
            "    team: customfield_20000\n"
            "confluence:\n"
            "  space_key: ENG\n"
            "document_reviews:\n"
            "  brd:\n"
            "    reviewer_jira_user: ''\n"
            "    reviewer_role: 'Product Owner'\n"
            "    phase: specify\n"
            "    sequence: 1\n"
            "    confluence_page: '{project} — BRD'\n"
        )
        return project

    def test_labels_and_team_are_sent_on_the_review_story(self, review_project, runner):
        from sdd.utils.atlassian_auth import Profile
        fake_jira = FakeJiraClient()
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=fake_jira), \
             patch("sdd.commands.review.ConfluenceClient", return_value=FakeConfluenceClient()):
            result = runner.invoke(review.review_command, ["submit", "--doc", "brd"])

        assert result.exit_code == 0, result.output
        # First created issue is the Epic (via _ensure_epic), second is the
        # review Story itself -- find it by its distinguishing label.
        review_issue = next(
            f for f in fake_jira.created if "sdd-review" in f.get("labels", [])
        )
        assert "sdd-generated" in review_issue["labels"]
        assert "org-required-label" in review_issue["labels"]
        assert review_issue["customfield_20000"] == "Team Phoenix"

    def test_two_features_do_not_collide_on_the_same_confluence_page(self, project, runner):
        """Regression test: document_reviews.confluence_page templates
        never had {feature} substituted (only {project} was), so two
        features submitting the same doc type used to silently upsert the
        SAME Confluence page -- the exact collision class {feature} was
        already added to page_map for (bug #82), just never fixed here."""
        from sdd.utils.atlassian_auth import Profile
        (project / ".specify" / "features" / "auth" / "brd.md").write_text(
            "# BRD\n\nBO-001 Reduce login friction.\n"
        )
        (project / ".specify" / "features" / "billing").mkdir(parents=True)
        (project / ".specify" / "features" / "billing" / "brd.md").write_text(
            "# BRD\n\nBO-001 Reduce billing friction.\n"
        )
        (project / ".specify" / "integrations.yml").write_text(
            "profile: default\n"
            "jira:\n  project_key: MYPROJ\n"
            "confluence:\n  space_key: ENG\n"
            "document_reviews:\n"
            "  brd:\n"
            "    reviewer_jira_user: ''\n"
            "    reviewer_role: 'Product Owner'\n"
            "    phase: specify\n"
            "    sequence: 1\n"
            "    confluence_page: '{feature} — BRD'\n"
        )
        shared_cf_client = FakeConfluenceClient()
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=FakeJiraClient()), \
             patch("sdd.commands.review.ConfluenceClient", return_value=shared_cf_client):
            r1 = runner.invoke(review.review_command, ["submit", "--doc", "brd", "--feature", "auth"])
            r2 = runner.invoke(review.review_command, ["submit", "--doc", "brd", "--feature", "billing"])

        assert r1.exit_code == 0, r1.output
        assert r2.exit_code == 0, r2.output
        # Two distinct pages, not one page silently overwritten by the second call
        assert "auth — BRD" in shared_cf_client.pages_by_title
        assert "billing — BRD" in shared_cf_client.pages_by_title
        assert shared_cf_client.pages_by_title["auth — BRD"]["id"] != \
               shared_cf_client.pages_by_title["billing — BRD"]["id"]

    def test_submit_records_the_review_link_locally(self, review_project, runner):
        """Regression: the dashboard's per-document Jira pill previously
        had no local fallback at all (unlike Confluence's), staying blank
        until the user manually clicked "Check Jira/Confluence review
        links" -- sdd review submit must record the review-gate ticket
        key the same way it already records the Confluence page."""
        from sdd.utils.atlassian_auth import Profile
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=FakeJiraClient()), \
             patch("sdd.commands.review.ConfluenceClient", return_value=FakeConfluenceClient()):
            result = runner.invoke(review.review_command, ["submit", "--doc", "brd"])

        assert result.exit_code == 0, result.output
        links = review._load_review_links()
        assert links["brd"]["key"].startswith("PROJ-")


class TestReviewApplyRecordsLink:
    @pytest.fixture()
    def runner(self):
        from click.testing import CliRunner
        return CliRunner()

    @pytest.fixture()
    def review_project(self, project):
        (project / ".specify" / "integrations.yml").write_text(
            "profile: default\n"
            "jira:\n  project_key: MYPROJ\n"
            "confluence:\n  space_key: ENG\n"
            "document_reviews:\n"
            "  brd:\n"
            "    reviewer_jira_user: ''\n"
            "    reviewer_role: 'Product Owner'\n"
            "    phase: specify\n"
            "    sequence: 1\n"
            "    confluence_page: '{feature} — BRD'\n"
        )
        return project

    def test_apply_records_the_review_link_when_issue_found(self, review_project, runner):
        from sdd.utils.atlassian_auth import Profile
        fake_jira = FakeJiraClient()
        fake_jira.by_label["sdd-doc:auth:brd"] = {
            "key": "PROJ-7", "fields": {"status": {"name": "In Review"}},
        }
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=fake_jira), \
             patch("sdd.commands.review.ConfluenceClient", return_value=FakeConfluenceClient()):
            result = runner.invoke(review.review_command, ["apply", "--doc", "brd"])

        assert result.exit_code == 0, result.output
        assert fake_jira.added_comments == [("PROJ-7", "Document updated per review comments. Please re-review: ")]
        links = review._load_review_links()
        assert links["brd"] == {"key": "PROJ-7"}

    def test_apply_does_not_record_a_link_when_no_issue_found(self, review_project, runner):
        from sdd.utils.atlassian_auth import Profile
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=FakeJiraClient()), \
             patch("sdd.commands.review.ConfluenceClient", return_value=FakeConfluenceClient()):
            result = runner.invoke(review.review_command, ["apply", "--doc", "brd"])

        assert result.exit_code == 0, result.output
        assert review._load_review_links() == {}


class TestReviewStatusPersonaHint:
    """`sdd review status` -- same Virtual Team persona hint the dashboard
    shows, added next to each non-approved/non-blocked row so the terminal
    output tells you who to ask, not just what state a doc is in."""

    @pytest.fixture()
    def runner(self):
        from click.testing import CliRunner
        return CliRunner()

    @pytest.fixture()
    def review_project(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".specify" / "features" / "auth").mkdir(parents=True)
        (tmp_path / ".specify" / "manifest.yml").write_text(
            yaml.dump({"project": {"name": "Demo", "feature": "auth", "scope": "pilot"}})
        )
        (tmp_path / ".specify" / "integrations.yml").write_text(
            "profile: default\n"
            "jira:\n  project_key: MYPROJ\n"
            "confluence:\n  space_key: ENG\n"
            "document_reviews:\n"
            "  brd:\n"
            "    reviewer_jira_user: ''\n"
            "    reviewer_role: 'Product Owner'\n"
            "    phase: specify\n"
            "    sequence: 1\n"
        )
        return tmp_path

    def _run(self, runner, fake_jira):
        from sdd.utils.atlassian_auth import Profile
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=fake_jira):
            return runner.invoke(review.review_command, ["status"])

    def test_not_submitted_doc_shows_who_to_ask(self, review_project, runner):
        result = self._run(runner, FakeJiraClient())  # by_label empty -> NOT_SUBMITTED
        assert result.exit_code == 0, result.output
        assert "ask Maya" in result.output

    def test_approved_doc_shows_no_ask_hint(self, review_project, runner):
        fake_jira = FakeJiraClient()
        fake_jira.by_label["sdd-doc:auth:brd"] = {
            "key": "PROJ-1", "fields": {"status": {"name": "Done"}},
        }
        fake_jira.comments_by_key["PROJ-1"] = []
        result = self._run(runner, fake_jira)
        assert result.exit_code == 0, result.output
        assert "ask" not in result.output

    def test_needs_revision_doc_shows_who_to_ask(self, review_project, runner):
        fake_jira = FakeJiraClient()
        fake_jira.by_label["sdd-doc:auth:brd"] = {
            "key": "PROJ-1", "fields": {"status": {"name": "In Review"}},
        }
        fake_jira.comments_by_key["PROJ-1"] = [{"body": "please clarify this section"}]
        result = self._run(runner, fake_jira)
        assert result.exit_code == 0, result.output
        assert "ask Maya" in result.output


class TestLocalDashboardCommentsFallback:
    """`sdd review check` / `sdd review apply` / `sdd review comments` --
    the pure-local-mode path for reviewer feedback with no Jira ticket to
    poll (a dashboard comment, with no integrations.yml at all)."""

    @pytest.fixture()
    def runner(self):
        from click.testing import CliRunner
        return CliRunner()

    def _write_comment(self, project, feature, doc, by, text, at):
        import json
        path = project / ".specify" / ".dashboard-comments.json"
        data = json.loads(path.read_text()) if path.exists() else {}
        data.setdefault(f"{feature}/{doc}", []).append({"by": by, "text": text, "at": at})
        path.write_text(json.dumps(data))

    def test_check_falls_back_to_local_comments_when_no_integrations_yml(self, project, runner):
        self._write_comment(project, "auth", "brd", "PO", "please clarify §2", "2000-01-01T00:00:00+00:00")
        result = runner.invoke(review.review_command, ["check", "--doc", "brd"])
        assert result.exit_code == 1
        assert "please clarify" in result.output
        assert "NEEDS REVISION" in result.output

    def test_check_reports_not_submitted_when_no_comments_and_no_config(self, project, runner):
        result = runner.invoke(review.review_command, ["check", "--doc", "brd"])
        assert result.exit_code == 3
        assert "NOT SUBMITTED" in result.output

    def test_apply_acknowledges_local_comments_with_no_config(self, project, runner):
        self._write_comment(project, "auth", "brd", "PO", "please clarify §2", "2000-01-01T00:00:00+00:00")
        assert runner.invoke(review.review_command, ["check", "--doc", "brd"]).exit_code == 1

        apply_result = runner.invoke(review.review_command, ["apply", "--doc", "brd"])
        assert apply_result.exit_code == 0
        assert "acknowledged" in apply_result.output

        # Re-checking must not repeat the same already-addressed comment
        assert runner.invoke(review.review_command, ["check", "--doc", "brd"]).exit_code == 3

    def test_comments_command_lists_unacknowledged(self, project, runner):
        self._write_comment(project, "auth", "brd", "PO", "please clarify §2", "2000-01-01T00:00:00+00:00")
        result = runner.invoke(review.review_command, ["comments", "--doc", "brd"])
        assert result.exit_code == 1
        assert "please clarify" in result.output

    def test_comments_command_no_comments_exits_zero(self, project, runner):
        result = runner.invoke(review.review_command, ["comments", "--doc", "brd"])
        assert result.exit_code == 0
        assert "no unacknowledged" in result.output

    def test_comments_command_ack_flag_clears_them(self, project, runner):
        self._write_comment(project, "auth", "brd", "PO", "please clarify §2", "2000-01-01T00:00:00+00:00")
        ack_result = runner.invoke(review.review_command, ["comments", "--doc", "brd", "--ack"])
        assert ack_result.exit_code == 0

        result = runner.invoke(review.review_command, ["comments", "--doc", "brd"])
        assert result.exit_code == 0
        assert "no unacknowledged" in result.output
