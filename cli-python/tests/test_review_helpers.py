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
        status, _, _ = review._get_review_status("brd", client, "MYPROJ", self._cfg(), "auth")
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
        status, _, _ = review._get_review_status("brd", client, "MYPROJ", self._cfg(), "auth")
        assert status == "NOT_SUBMITTED"

    def test_different_features_do_not_collide(self, project):
        client = FakeJiraClient()
        client.by_label["sdd-doc:auth:brd"] = {
            "key": "PROJ-1",
            "fields": {"status": {"name": "Done"}},
        }
        status, _, _ = review._get_review_status("brd", client, "MYPROJ", self._cfg(), "billing")
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
        self.body_by_title: dict[str, str] = {}
        self._next_id = 1

    def get_page_by_title(self, space_key, title):
        return self.pages_by_title.get(title)

    def create_page(self, space_key, title, body_html, parent_id=None):
        page = {"id": str(self._next_id), "_links": {"webui": f"/pages/{self._next_id}"}}
        self._next_id += 1
        self.pages_by_title[title] = page
        self.body_by_title[title] = body_html
        return page

    def upsert_page(self, space_key, title, body_html, parent_id=None):
        existing = self.get_page_by_title(space_key, title)
        if existing:
            self.body_by_title[title] = body_html
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
        assert fake_jira.added_comments == [("PROJ-7", "Document updated per review comments. Please re-review:")]
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

    def test_apply_pushes_confluence_with_no_jira_configured(self, project, runner):
        """review_apply used to hard-require both jira: and confluence: --
        a confluence-only project (no jira: section at all) got a red error
        and nothing pushed, even though there's nothing stopping the
        Confluence half from working on its own."""
        (project / ".specify" / "features" / "auth" / "brd.md").write_text(
            "# BRD\n\nUpdated content.\n"
        )
        (project / ".specify" / "integrations.yml").write_text(
            "profile: default\n"
            "confluence:\n  space_key: ENG\n"
            "document_reviews:\n"
            "  brd:\n"
            "    reviewer_jira_user: ''\n"
            "    reviewer_role: 'Product Owner'\n"
            "    phase: specify\n"
            "    sequence: 1\n"
            "    confluence_page: '{feature} — BRD'\n"
        )
        from sdd.utils.atlassian_auth import Profile
        cf_client = FakeConfluenceClient()
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.ConfluenceClient", return_value=cf_client):
            result = runner.invoke(review.review_command, ["apply", "--doc", "brd"])

        assert result.exit_code == 0, result.output
        assert "auth — BRD" in cf_client.pages_by_title
        assert "Updated content." in cf_client.body_by_title["auth — BRD"]

    def test_apply_notifies_jira_with_no_confluence_configured(self, project, runner):
        """Symmetric case: jira-only (no confluence: section) should still
        notify the reviewer, just skip the Confluence push entirely rather
        than erroring out."""
        (project / ".specify" / "features" / "auth" / "brd.md").write_text(
            "# BRD\n\nUpdated content.\n"
        )
        (project / ".specify" / "integrations.yml").write_text(
            "profile: default\n"
            "jira:\n  project_key: MYPROJ\n"
            "document_reviews:\n"
            "  brd:\n"
            "    reviewer_jira_user: ''\n"
            "    reviewer_role: 'Product Owner'\n"
            "    phase: specify\n"
            "    sequence: 1\n"
            "    confluence_page: '{feature} — BRD'\n"
        )
        from sdd.utils.atlassian_auth import Profile
        fake_jira = FakeJiraClient()
        fake_jira.by_label["sdd-doc:auth:brd"] = {
            "key": "PROJ-9", "fields": {"status": {"name": "In Review"}},
        }
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=fake_jira):
            result = runner.invoke(review.review_command, ["apply", "--doc", "brd"])

        assert result.exit_code == 0, result.output
        assert fake_jira.added_comments == [
            ("PROJ-9", "Document updated per review comments. Please re-review:")
        ]
        assert "Confluence" not in result.output


class TestValidatePhaseDocKeys:
    """analyze.md and clarify.md are just as generic to the review-gate
    CLI as brd/srd/etc -- resolve_doc_path/review_submit/review_approve
    have no doc-key allowlist, so wiring them up is purely a matter of
    integrations.yml document_reviews entries (phase: validate,
    sequence 1/2/3 for validate/analyze/clarify) plus the prompt-side
    Step B/C sections. These tests guard against a future regression
    where someone hard-codes a doc-key allowlist into the CLI and
    silently breaks this."""

    @pytest.fixture()
    def runner(self):
        from click.testing import CliRunner
        return CliRunner()

    @pytest.fixture()
    def validate_phase_project(self, project):
        (project / ".specify" / "features" / "auth" / "validate.md").write_text(
            "# Validation Report\n> Version: 1.0 | Status: Draft\n\nBody.\n"
        )
        (project / ".specify" / "features" / "auth" / "analyze.md").write_text(
            "# Analysis Report\n> Version: 1.0 | Status: Draft\n\nBody.\n"
        )
        (project / ".specify" / "features" / "auth" / "clarify.md").write_text(
            "# Clarification Report\n> Version: 1.0 | Status: Draft\n\nBody.\n"
        )
        (project / ".specify" / "integrations.yml").write_text(
            "profile: default\n"
            "jira:\n  project_key: MYPROJ\n"
            "confluence:\n  space_key: ENG\n"
            "document_reviews:\n"
            "  validate:\n"
            "    reviewer_jira_user: ''\n"
            "    reviewer_role: 'Product Owner'\n"
            "    phase: validate\n"
            "    sequence: 1\n"
            "    confluence_page: '{feature} — Validation Report'\n"
            "  analyze:\n"
            "    reviewer_jira_user: ''\n"
            "    reviewer_role: 'Tech Lead'\n"
            "    phase: validate\n"
            "    sequence: 2\n"
            "    confluence_page: '{feature} — Analysis Report'\n"
            "  clarify:\n"
            "    reviewer_jira_user: ''\n"
            "    reviewer_role: 'Architect'\n"
            "    phase: validate\n"
            "    sequence: 3\n"
            "    confluence_page: '{feature} — Clarifications'\n"
        )
        return project

    def test_submit_works_for_analyze_and_clarify_doc_keys(self, validate_phase_project, runner):
        from sdd.utils.atlassian_auth import Profile
        fake_jira = FakeJiraClient()
        # Satisfy the sequence gate for both: validate approved before
        # analyze submits, analyze approved before clarify submits.
        fake_jira.by_label["sdd-doc:auth:validate"] = {
            "key": "PROJ-1", "fields": {"status": {"name": "Done"}},
        }
        fake_jira.by_label["sdd-doc:auth:analyze"] = {
            "key": "PROJ-2", "fields": {"status": {"name": "Done"}},
        }
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=fake_jira), \
             patch("sdd.commands.review.ConfluenceClient", return_value=FakeConfluenceClient()):
            r_analyze = runner.invoke(review.review_command, ["submit", "--doc", "analyze"])
            r_clarify = runner.invoke(review.review_command, ["submit", "--doc", "clarify"])

        assert r_analyze.exit_code == 0, r_analyze.output
        assert r_clarify.exit_code == 0, r_clarify.output
        links = review._load_review_links()
        assert links["analyze"]["key"].startswith("PROJ-")
        assert links["clarify"]["key"].startswith("PROJ-")

    def test_analyze_submission_blocked_until_validate_approved(self, validate_phase_project, runner):
        from sdd.utils.atlassian_auth import Profile
        fake_jira = FakeJiraClient()
        fake_jira.by_label["sdd-doc:auth:validate"] = {
            "key": "PROJ-1", "fields": {"status": {"name": "In Review"}},
        }
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=fake_jira), \
             patch("sdd.commands.review.ConfluenceClient", return_value=FakeConfluenceClient()):
            result = runner.invoke(review.review_command, ["submit", "--doc", "analyze"])

        assert result.exit_code == 1
        assert "VALIDATE is not yet approved" in result.output

    def test_review_approve_local_flips_clarify_status_header(self, validate_phase_project, runner):
        """Regression: clarify-template.md's header used to say
        'Status: OPEN' instead of 'Status: Draft' -- _mark_md_approved's
        regex only recognizes Draft/Proposed, so the header would have
        silently never flipped to Approved. Confirms the template fix
        (OPEN -> Draft) makes the standard approval flow work for
        clarify.md exactly like every other document."""
        result = runner.invoke(review.review_command, [
            "approve", "--doc", "clarify", "--local", "--by", "Architect", "--no-confluence",
        ])
        assert result.exit_code == 0, result.output
        clarify_text = (validate_phase_project / ".specify" / "features" / "auth" / "clarify.md").read_text()
        assert "Status: Approved" in clarify_text
        assert "Status: Draft" not in clarify_text


class TestJiraStatusBanner:
    """The Confluence page for a document under Jira review should show the
    ticket's link + live status directly on the page, so a reviewer never
    has to leave Confluence to see where things stand."""

    def test_banner_for_pending_status(self):
        html = review._jira_status_banner("PROJ-1", "https://x/browse/PROJ-1", "PENDING", "Product Owner")
        assert 'ac:name="info"' in html
        assert "PROJ-1" in html
        assert "https://x/browse/PROJ-1" in html
        assert "Pending review" in html
        assert "Product Owner" in html

    def test_banner_for_approved_status(self):
        html = review._jira_status_banner("PROJ-1", "https://x/browse/PROJ-1", "APPROVED", "Architect")
        assert 'ac:name="success"' in html
        assert "Approved" in html

    def test_banner_for_needs_revision_status(self):
        html = review._jira_status_banner("PROJ-1", "https://x/browse/PROJ-1", "NEEDS_REVISION", "Tech Lead")
        assert 'ac:name="warning"' in html
        assert "Needs Revision" in html

    @pytest.fixture()
    def runner(self):
        from click.testing import CliRunner
        return CliRunner()

    @pytest.fixture()
    def banner_project(self, project):
        (project / ".specify" / "features" / "auth" / "brd.md").write_text(
            "# BRD\n\nBO-001 Reduce login friction.\n"
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
            "    confluence_page: '{project} — BRD'\n"
        )
        return project

    def test_submit_stamps_pending_banner_on_confluence_page(self, banner_project, runner):
        """The first push (before the ticket exists) can't include a
        banner -- review_submit must re-push once the ticket is created so
        the page picks it up."""
        from sdd.utils.atlassian_auth import Profile
        cf_client = FakeConfluenceClient()
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=FakeJiraClient()), \
             patch("sdd.commands.review.ConfluenceClient", return_value=cf_client):
            result = runner.invoke(review.review_command, ["submit", "--doc", "brd"])

        assert result.exit_code == 0, result.output
        body = cf_client.body_by_title["Demo — BRD"]
        assert "Jira review" in body
        assert "Pending review" in body
        assert "PROJ-" in body

    def test_check_refreshes_banner_to_approved(self, banner_project, runner):
        from sdd.utils.atlassian_auth import Profile
        fake_jira = FakeJiraClient()
        fake_jira.by_label["sdd-doc:auth:brd"] = {
            "key": "PROJ-7", "fields": {"status": {"name": "Done"}},
        }
        cf_client = FakeConfluenceClient()
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=fake_jira), \
             patch("sdd.commands.review.ConfluenceClient", return_value=cf_client):
            result = runner.invoke(review.review_command, ["check", "--doc", "brd"])

        assert result.exit_code == 0, result.output
        body = cf_client.body_by_title["Demo — BRD"]
        assert "PROJ-7" in body
        assert "Approved" in body

    def test_push_doc_page_omits_banner_when_doc_not_under_jira_review(self, project, runner):
        """qa-testcases.md (and any doc key not in document_reviews) can
        still get a Confluence page via the page_map fallback -- it just
        never carries a Jira banner since there's no review ticket for it."""
        (project / ".specify" / "features" / "auth" / "qa-testcases.md").write_text(
            "# QA Test Cases\n\nTC-001 ...\n"
        )
        (project / ".specify" / "integrations.yml").write_text(
            "profile: default\n"
            "confluence:\n"
            "  space_key: ENG\n"
            "  page_map:\n"
            "    qa-testcases: '{feature} — QA Test Cases'\n"
        )
        from sdd.utils.atlassian_auth import Profile
        cf_client = FakeConfluenceClient()
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.ConfluenceClient", return_value=cf_client):
            result = review._push_doc_page(
                "qa-testcases",
                project / ".specify" / "features" / "auth" / "qa-testcases.md",
                "auth",
            )

        assert result is not None
        title, url = result
        assert title == "auth — QA Test Cases"
        assert url.startswith("https://x.atlassian.net/wiki/pages/")
        assert "Jira review" not in cf_client.body_by_title["auth — QA Test Cases"]


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


# ── Open-questions push/pull (blocked-doc Jira Q&A) ────────────────────────────

class TestParseOpenQuestions:
    def test_parses_single_location_row(self):
        text = (
            "| ID | Locations | Question |\n"
            "|---|---|---|\n"
            "| brd:NC-002 | brd:NC-002 | What business problem does this pilot address? |\n"
        )
        items = review._parse_open_questions(text)
        assert len(items) == 1
        assert items[0]["id"] == "brd:NC-002"
        assert items[0]["locations"] == ["brd:NC-002"]
        assert items[0]["question"] == "What business problem does this pilot address?"

    def test_parses_multi_location_row(self):
        """A question asked in more than one document (a duplicate) must
        list every doc-qualified ID so one answer patches all of them."""
        text = "| brd:NC-003 | brd:NC-003, srd:NC-001 | How long must records be retained? |\n"
        items = review._parse_open_questions(text)
        assert items[0]["locations"] == ["brd:NC-003", "srd:NC-001"]

    def test_ignores_non_matching_table_rows(self):
        text = (
            "| Role | Status |\n"
            "|---|---|\n"
            "| Product Owner | Pending |\n"
            "| brd:NC-001 | brd:NC-001 | A real question |\n"
        )
        items = review._parse_open_questions(text)
        assert len(items) == 1
        assert items[0]["id"] == "brd:NC-001"

    def test_no_matching_rows_returns_empty_list(self):
        assert review._parse_open_questions("nothing here\n") == []

    def test_tolerant_of_extra_whitespace(self):
        text = "|   brd:NC-005   |   brd:NC-005  ,  srd:NC-002   |   Padded question?   |\n"
        items = review._parse_open_questions(text)
        assert items[0]["id"] == "brd:NC-005"
        assert items[0]["locations"] == ["brd:NC-005", "srd:NC-002"]
        assert items[0]["question"] == "Padded question?"


class TestExtractTextPreservesLineBoundaries:
    """Regression: user-reported. Jira's rich-text comment editor stores
    each line a reviewer types as a SEPARATE paragraph node in the ADF
    tree, not one paragraph with embedded newlines. _extract_text() used
    to join every text run in the whole comment with a single space,
    collapsing a real multi-line reply (one "{doc}:NC-{NNN}: {answer}"
    item per line) into a single run-on line -- _ANSWER_LINE_RE's
    per-line matching then only ever found the first item, with every
    other item's text swallowed into its answer."""

    def _multi_paragraph_adf(self, *lines):
        return {
            "type": "doc", "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": line}]}
                for line in lines
            ],
        }

    def test_separate_paragraphs_become_separate_lines(self):
        body = self._multi_paragraph_adf("brd:NC-001: first", "brd:NC-002: second")
        assert review._extract_text(body) == "brd:NC-001: first\nbrd:NC-002: second"

    def test_plain_string_body_unchanged(self):
        assert review._extract_text("brd:NC-001: 90 days") == "brd:NC-001: 90 days"

    def test_hard_break_within_one_paragraph_becomes_newline(self):
        body = {
            "type": "doc", "version": 1,
            "content": [{"type": "paragraph", "content": [
                {"type": "text", "text": "brd:NC-001: first"},
                {"type": "hardBreak"},
                {"type": "text", "text": "brd:NC-002: second"},
            ]}],
        }
        assert review._extract_text(body) == "brd:NC-001: first\nbrd:NC-002: second"

    def test_pull_answers_parses_all_seven_items_from_real_world_multi_line_reply(self):
        """The exact shape of the bug report: 7 distinct answers, each its
        own paragraph, all previously collapsing into one answer for the
        first item only."""
        body = self._multi_paragraph_adf(
            "brd:NC-001:<answer one>",
            "brd:NC-002: <answer two>",
            "brd:NC-003: <answer three>",
            "srd:NC-001: <answer four>",
            "srd:NC-002: <answer five>",
            "srd:NC-003: <answer six>",
            "srd:NC-005: <answer seven>",
        )
        answers = review._parse_answers([{"body": body, "author": {}, "created": "x"}])
        assert len(answers) == 7
        assert answers["brd:NC-001"] == "<answer one>"
        assert answers["srd:NC-005"] == "<answer seven>"


class TestParseAnswers:
    def _comment(self, text, created="2026-01-01T00:00:00+00:00"):
        return {"body": text, "author": {"displayName": "PO"}, "created": created}

    def test_parses_single_answer_line(self):
        answers = review._parse_answers([self._comment("brd:NC-002: 90 days")])
        assert answers == {"brd:NC-002": "90 days"}

    def test_parses_multiple_lines_in_one_comment(self):
        answers = review._parse_answers([self._comment(
            "brd:NC-001: Some answer here\nsrd:NC-002: Another answer"
        )])
        assert answers["brd:NC-001"] == "Some answer here"
        assert answers["srd:NC-002"] == "Another answer"

    def test_later_comment_overrides_earlier_answer(self):
        answers = review._parse_answers([
            self._comment("brd:NC-002: first answer", created="2026-01-01T00:00:00+00:00"),
            self._comment("brd:NC-002: corrected answer", created="2026-01-02T00:00:00+00:00"),
        ])
        assert answers["brd:NC-002"] == "corrected answer"

    def test_is_case_insensitive_on_doc_key(self):
        answers = review._parse_answers([self._comment("BRD:NC-002: value")])
        assert answers == {"brd:NC-002": "value"}

    def test_ignores_comments_with_no_id(self):
        answers = review._parse_answers([self._comment("just a general comment, no ID here")])
        assert answers == {}

    def test_handles_adf_body(self):
        adf_body = {
            "type": "doc", "version": 1,
            "content": [{"type": "paragraph", "content": [
                {"type": "text", "text": "brd:NC-002: 90 days"}
            ]}],
        }
        answers = review._parse_answers([self._comment(adf_body)])
        assert answers == {"brd:NC-002": "90 days"}


class TestPatchMarker:
    def _doc(self, project, name, body):
        p = project / ".specify" / "features" / "auth" / f"{name}.md"
        p.write_text(body)
        return p

    def test_replaces_marker_with_answer_text(self, project):
        p = self._doc(project, "brd", (
            "# BRD\n> Version: 1.0 | Status: Draft\n\n"
            "§4 [NEEDS CLARIFICATION-002: What problem does this solve?]\n"
        ))
        assert review._patch_marker(p, "002", "Real-time settlement demo.") is True
        text = p.read_text()
        assert "Real-time settlement demo." in text
        assert "NEEDS CLARIFICATION-002" not in text

    def test_bumps_version_header(self, project):
        p = self._doc(project, "brd", (
            "# BRD\n> Version: 1.0 | Status: Draft\n\n"
            "[NEEDS CLARIFICATION-002: q?]\n"
        ))
        review._patch_marker(p, "002", "answer")
        assert "Version: 1.1" in p.read_text()

    def test_appends_version_history_row(self, project):
        p = self._doc(project, "brd", (
            "# BRD\n> Version: 1.0\n\n"
            "[NEEDS CLARIFICATION-002: q?]\n\n"
            "## Version History\n\n"
            "| Version | Date | Changed By | Summary | CHG-NNN |\n"
            "|---|---|---|---|---|\n"
            "| 1.0 | 2026-01-01 | init | Initial draft | — |\n"
        ))
        review._patch_marker(p, "002", "answer")
        text = p.read_text()
        assert "NC-002 resolved via Jira/Confluence comment" in text
        assert text.index("| 1.1 |") < text.index("| 1.0 |")  # new row inserted first

    def test_missing_marker_id_returns_false_and_leaves_file_untouched(self, project):
        p = self._doc(project, "brd", (
            "# BRD\n> Version: 1.0\n\n[NEEDS CLARIFICATION-002: q?]\n"
        ))
        before = p.read_text()
        assert review._patch_marker(p, "999", "answer") is False
        assert p.read_text() == before

    def test_nonexistent_file_returns_false(self, project):
        p = project / ".specify" / "features" / "auth" / "does-not-exist.md"
        assert review._patch_marker(p, "001", "answer") is False

    def test_no_version_history_section_still_patches_marker(self, project):
        """Best-effort: missing Version History table must not block the
        marker replacement itself, only skip that bonus bookkeeping."""
        p = self._doc(project, "brd", (
            "# BRD\n> Version: 1.0\n\n[NEEDS CLARIFICATION-002: q?]\n"
        ))
        assert review._patch_marker(p, "002", "answer") is True
        assert "answer" in p.read_text()


class TestNumberLegacyMarkers:
    def _doc(self, project, name, body):
        p = project / ".specify" / "features" / "auth" / f"{name}.md"
        p.write_text(body)
        return p

    def test_numbers_unnumbered_markers_in_order(self, project):
        p = self._doc(project, "brd", (
            "# BRD\n\n"
            "§4 [NEEDS CLARIFICATION: What problem does this solve?]\n\n"
            "§5 [NEEDS CLARIFICATION: How long must records be retained?]\n"
        ))
        assert review._number_legacy_markers(p) == 2
        text = p.read_text()
        assert "[NEEDS CLARIFICATION-001: What problem does this solve?]" in text
        assert "[NEEDS CLARIFICATION-002: How long must records be retained?]" in text

    def test_zero_pads_to_three_digits(self, project):
        body = "\n".join(
            f"[NEEDS CLARIFICATION: q{i}?]" for i in range(1, 11)
        )
        p = self._doc(project, "brd", body)
        review._number_legacy_markers(p)
        text = p.read_text()
        assert "[NEEDS CLARIFICATION-001:" in text
        assert "[NEEDS CLARIFICATION-010:" in text

    def test_continues_after_highest_existing_number_in_mixed_doc(self, project):
        p = self._doc(project, "brd", (
            "[NEEDS CLARIFICATION-002: already numbered?]\n\n"
            "[NEEDS CLARIFICATION: legacy, unnumbered?]\n"
        ))
        assert review._number_legacy_markers(p) == 1
        text = p.read_text()
        assert "[NEEDS CLARIFICATION-002: already numbered?]" in text
        assert "[NEEDS CLARIFICATION-003: legacy, unnumbered?]" in text

    def test_leaves_already_numbered_markers_untouched(self, project):
        p = self._doc(project, "brd", "[NEEDS CLARIFICATION-001: already numbered?]\n")
        assert review._number_legacy_markers(p) == 0
        assert p.read_text() == "[NEEDS CLARIFICATION-001: already numbered?]\n"

    def test_no_legacy_markers_returns_zero_and_does_not_rewrite_file(self, project):
        p = self._doc(project, "brd", "# BRD\n\nNo open questions here.\n")
        before = p.read_text()
        assert review._number_legacy_markers(p) == 0
        assert p.read_text() == before

    def test_nonexistent_file_returns_zero(self, project):
        p = project / ".specify" / "features" / "auth" / "does-not-exist.md"
        assert review._number_legacy_markers(p) == 0


class TestNormalizeDocKey:
    def test_uc_normalizes_to_use_cases(self):
        assert review._normalize_doc_key("uc") == "use-cases"

    def test_usecases_normalizes_to_use_cases(self):
        assert review._normalize_doc_key("usecases") == "use-cases"

    def test_is_case_insensitive(self):
        assert review._normalize_doc_key("UC") == "use-cases"

    def test_unknown_key_passes_through_lowercased(self):
        assert review._normalize_doc_key("BRD") == "brd"
        assert review._normalize_doc_key("srd") == "srd"


class TestClarifyOpenItemsAndAnswers:
    """clarify.md's own items (AMB/GAP/CON/ASM/OQ/R) use a STATUS TABLE, not
    a bracketed [NEEDS CLARIFICATION-NNN] marker -- push-questions/
    pull-answers only ever understood the latter, so clarify.md could never
    be pushed to Jira for answers the way validate.md already could. These
    tests cover the parallel _parse_clarify_*/_patch_clarify_item path that
    fixes that gap."""

    def _clarify_md(self, extra_amb_line: str = "") -> str:
        return (
            "# Clarification Report — Demo\n"
            "> Version: 1.0 | Status: Draft | Date: 2026-01-01 | Author: Rex\n\n"
            "## AMBIGUITIES — AMB-NNN\n\n"
            "### AMB-001: clearing_ref vs clearingRef naming\n"
            "**Found in:** brd.md §2, srd.md §3\n"
            "**The ambiguity:** BRD uses clearing_ref, SRD uses clearingRef.\n"
            "**Option A:** intentional JSON-field vs DB-column split\n"
            "**Option B:** unintentional drift\n"
            f"**Your answer:** {{FILL THIS}}{extra_amb_line}\n\n"
            "---\n\n"
            "## ASSUMPTIONS — ASM-NNN\n\n"
            "### ASM-001: 99% availability is a real pilot target\n"
            "**Assumption:** single-instance Docker Compose has no redundancy\n"
            "**Found in:** srd.md §5 NFR-003\n"
            "**Basis:** inherited service-baseline default\n"
            "**Correct?** {FILL: Yes / No — if No: correct version}\n\n"
            "---\n\n"
            "## STATUS TABLE\n\n"
            "| ID | Type | Item | Status |\n"
            "|---|---|---|---|\n"
            "| AMB-001 | Ambiguity | clearing_ref naming | OPEN |\n"
            "| ASM-001 | Assumption | 99% availability target | OPEN |\n\n"
            "## Version History\n\n"
            "| Version | Date | Changed By | Summary of Changes | CHG-NNN |\n"
            "|---|---|---|---|---|\n"
            "| 1.0 | 2026-01-01 | Rex | Initial draft | — |\n"
        )

    def test_parse_open_items_finds_both_open_rows(self):
        items = review._parse_clarify_open_items(self._clarify_md())
        ids = [it["id"] for it in items]
        assert ids == ["clarify:AMB-001", "clarify:ASM-001"]
        assert all(it["locations"] == [it["id"]] for it in items)

    def test_parse_open_items_skips_resolved_rows(self):
        text = self._clarify_md().replace(
            "| ASM-001 | Assumption | 99% availability target | OPEN |",
            "| ASM-001 | Assumption | 99% availability target | CONFIRMED |",
        )
        items = review._parse_clarify_open_items(text)
        assert [it["id"] for it in items] == ["clarify:AMB-001"]

    def test_question_text_includes_full_item_block(self):
        items = review._parse_clarify_open_items(self._clarify_md())
        amb = next(it for it in items if it["id"] == "clarify:AMB-001")
        assert "Option A" in amb["question"]
        assert "Option B" in amb["question"]

    def test_parse_answers_extracts_clarify_prefixed_lines(self):
        comments = [{"body": "clarify:AMB-001: Intentional split — keep both."}]
        answers = review._parse_clarify_answers(comments)
        assert answers == {"clarify:AMB-001": "Intentional split — keep both."}

    def test_parse_answers_is_case_insensitive_and_normalizes_code_case(self):
        comments = [{"body": "Clarify:amb-001: some answer"}]
        answers = review._parse_clarify_answers(comments)
        assert answers == {"clarify:AMB-001": "some answer"}

    def test_patch_fills_placeholder_and_sets_resolved_for_ambiguity(self, project):
        p = project / ".specify" / "features" / "auth" / "clarify.md"
        p.write_text(self._clarify_md())
        assert review._patch_clarify_item(p, "AMB-001", "Intentional split.") is True
        text = p.read_text()
        assert "**Your answer:** Intentional split." in text
        assert "{FILL THIS}" not in text.split("## ASSUMPTIONS")[0]  # AMB block only
        assert "| AMB-001 | Ambiguity | clearing_ref naming | RESOLVED |" in text

    def test_patch_sets_confirmed_for_assumption_answered_yes(self, project):
        p = project / ".specify" / "features" / "auth" / "clarify.md"
        p.write_text(self._clarify_md())
        assert review._patch_clarify_item(p, "ASM-001", "Yes, keep as monitored target.") is True
        text = p.read_text()
        assert "**Correct?** Yes, keep as monitored target." in text
        assert "| ASM-001 | Assumption | 99% availability target | CONFIRMED |" in text

    def test_patch_sets_corrected_for_assumption_answered_no(self, project):
        p = project / ".specify" / "features" / "auth" / "clarify.md"
        p.write_text(self._clarify_md())
        assert review._patch_clarify_item(p, "ASM-001", "No, defer to mvp+.") is True
        text = p.read_text()
        assert "| ASM-001 | Assumption | 99% availability target | CORRECTED |" in text

    def test_patch_bumps_version_and_logs(self, project):
        p = project / ".specify" / "features" / "auth" / "clarify.md"
        p.write_text(self._clarify_md())
        review._patch_clarify_item(p, "AMB-001", "answer")
        text = p.read_text()
        assert "Version: 1.1" in text
        assert "AMB-001 resolved via Jira/Confluence comment" in text

    def test_patch_already_answered_item_returns_false(self, project):
        """No {FILL...} left in the block -- already resolved, don't
        silently re-flip an already-terminal STATUS TABLE row."""
        p = project / ".specify" / "features" / "auth" / "clarify.md"
        text = self._clarify_md().replace("{FILL THIS}", "Already answered.")
        p.write_text(text)
        assert review._patch_clarify_item(p, "AMB-001", "new answer") is False

    def test_patch_unknown_code_returns_false(self, project):
        p = project / ".specify" / "features" / "auth" / "clarify.md"
        p.write_text(self._clarify_md())
        assert review._patch_clarify_item(p, "GAP-999", "answer") is False

    def test_patch_nonexistent_file_returns_false(self, project):
        p = project / ".specify" / "features" / "auth" / "clarify.md"
        assert review._patch_clarify_item(p, "AMB-001", "answer") is False


class TestClarifyPushPullCommands:
    @pytest.fixture()
    def runner(self):
        from click.testing import CliRunner
        return CliRunner()

    @pytest.fixture()
    def clarify_project(self, project):
        (project / ".specify" / "features" / "auth" / "clarify.md").write_text(
            TestClarifyOpenItemsAndAnswers()._clarify_md()
        )
        (project / ".specify" / "integrations.yml").write_text(
            "profile: default\n"
            "jira:\n  project_key: MYPROJ\n"
            "confluence:\n  space_key: ENG\n"
            "document_reviews:\n"
            "  clarify:\n"
            "    reviewer_jira_user: '712020:abc'\n"
            "    reviewer_role: 'Architect'\n"
            "    phase: specify\n"
            "    sequence: 6\n"
            "    confluence_page: '{feature} — Clarifications'\n"
        )
        return project

    def test_push_questions_creates_ticket_with_clarify_items(self, clarify_project, runner):
        from sdd.utils.atlassian_auth import Profile
        fake_jira = FakeJiraClient()
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=fake_jira), \
             patch("sdd.commands.review.ConfluenceClient", return_value=FakeConfluenceClient()):
            result = runner.invoke(review.review_command, ["push-questions", "--doc", "clarify"])

        assert result.exit_code == 0, result.output
        issue = next(f for f in fake_jira.created if "sdd-open-questions" in f.get("labels", []))
        desc_text = issue["description"]["content"][0]["content"][0]["text"]
        assert "clarify:AMB-001" in desc_text
        assert "clarify:ASM-001" in desc_text
        assert "re-run /clarify" in desc_text

    def test_pull_answers_patches_clarify_md_and_refreshes_its_confluence_page(
        self, clarify_project, runner
    ):
        from sdd.utils.atlassian_auth import Profile
        fake_jira = FakeJiraClient()
        fake_confluence = FakeConfluenceClient()
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=fake_jira), \
             patch("sdd.commands.review.ConfluenceClient", return_value=fake_confluence):
            runner.invoke(review.review_command, ["push-questions", "--doc", "clarify"])
            issue_key = review._load_review_links()["clarify"]["key"]
            fake_jira.comments_by_key[issue_key] = [{
                "body": "clarify:AMB-001: Intentional split.\n"
                        "clarify:ASM-001: Yes, keep as monitored target.",
                "author": {"displayName": "Architect"}, "created": "2026-01-02T00:00:00+00:00",
            }]
            result = runner.invoke(review.review_command, ["pull-answers", "--doc", "clarify"])

        assert result.exit_code == 0, result.output
        text = (clarify_project / ".specify" / "features" / "auth" / "clarify.md").read_text()
        assert "Intentional split." in text
        assert "| AMB-001 | Ambiguity | clearing_ref naming | RESOLVED |" in text
        assert "| ASM-001 | Assumption | 99% availability target | CONFIRMED |" in text
        assert "{FILL" not in text
        assert "auth — Clarifications" in fake_confluence.pages_by_title


class TestPushPullQuestionsCommands:
    @pytest.fixture()
    def runner(self):
        from click.testing import CliRunner
        return CliRunner()

    @pytest.fixture()
    def blocked_project(self, project):
        (project / ".specify" / "features" / "auth" / "brd.md").write_text(
            "# BRD\n> Version: 1.0 | Status: Draft\n\n"
            "§4 [NEEDS CLARIFICATION-001: What business problem does this solve?]\n\n"
            "§5 [NEEDS CLARIFICATION-002: How long must records be retained?]\n\n"
            "## Version History\n\n| Version | Date | Changed By | Summary | CHG-NNN |\n"
            "|---|---|---|---|---|\n| 1.0 | 2026-01-01 | init | Initial draft | — |\n"
        )
        (project / ".specify" / "features" / "auth" / "srd.md").write_text(
            "# SRD\n> Version: 1.0 | Status: Draft\n\n"
            "§3 [NEEDS CLARIFICATION-001: How long must records be retained?]\n\n"
            "## Version History\n\n| Version | Date | Changed By | Summary | CHG-NNN |\n"
            "|---|---|---|---|---|\n| 1.0 | 2026-01-01 | init | Initial draft | — |\n"
        )
        (project / ".specify" / "features" / "auth" / "validate.md").write_text(
            "# Validation Report\n> Version: 1.0 | Status: BLOCKED\n\n"
            "| ID | Locations | Question |\n|---|---|---|\n"
            "| brd:NC-001 | brd:NC-001 | What business problem does this solve? |\n"
            "| brd:NC-002 | brd:NC-002, srd:NC-001 | How long must records be retained? |\n"
        )
        (project / ".specify" / "integrations.yml").write_text(
            "profile: default\n"
            "jira:\n  project_key: MYPROJ\n"
            "confluence:\n  space_key: ENG\n"
            "document_reviews:\n"
            "  validate:\n"
            "    reviewer_jira_user: '712020:abc'\n"
            "    reviewer_role: 'Business Analyst'\n"
            "    phase: specify\n"
            "    sequence: 4\n"
            "    confluence_page: '{feature} — Validation'\n"
        )
        return project

    def test_push_questions_creates_ticket_with_open_questions_label(self, blocked_project, runner):
        from sdd.utils.atlassian_auth import Profile
        fake_jira = FakeJiraClient()
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=fake_jira), \
             patch("sdd.commands.review.ConfluenceClient", return_value=FakeConfluenceClient()):
            result = runner.invoke(review.review_command, ["push-questions", "--doc", "validate"])

        assert result.exit_code == 0, result.output
        issue = next(f for f in fake_jira.created if "sdd-open-questions" in f.get("labels", []))
        assert "sdd-doc:auth:validate" in issue["labels"]
        assert "brd:NC-001" in issue["description"]["content"][0]["content"][0]["text"]
        links = review._load_review_links()
        assert links["validate"]["key"].startswith("PROJ-")

    def test_push_questions_uses_same_idempotency_label_as_submit(self, blocked_project, runner):
        """The whole point of reusing sdd-doc:{feature}:{doc} as the label
        is that `sdd review submit --doc validate` later finds this exact
        ticket via find_by_label and updates it in place, rather than
        creating a second one -- verified here by calling submit right
        after push-questions and checking only one ticket key exists."""
        from sdd.utils.atlassian_auth import Profile
        fake_jira = FakeJiraClient()
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=fake_jira), \
             patch("sdd.commands.review.ConfluenceClient", return_value=FakeConfluenceClient()):
            runner.invoke(review.review_command, ["push-questions", "--doc", "validate"])
            result = runner.invoke(review.review_command, ["submit", "--doc", "validate"])

        assert result.exit_code == 0, result.output
        # push-questions creates 2 issues (the Epic + the open-questions
        # ticket); submit must find both by label and update, not create
        # a second Epic or a second review ticket. submit's own epic-ensure
        # step refreshes the existing Epic's content too, so 2 updates
        # total (Epic + the review ticket), not a 3rd/4th create.
        assert len(fake_jira.created) == 2
        assert len(fake_jira.updated) == 2
        open_questions_key = fake_jira.by_label["sdd-doc:auth:validate"]["key"]
        assert open_questions_key in [key for key, _ in fake_jira.updated]

    def test_submit_posts_transition_comment_when_reusing_open_questions_ticket(self, blocked_project, runner):
        from sdd.utils.atlassian_auth import Profile
        fake_jira = FakeJiraClient()
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=fake_jira), \
             patch("sdd.commands.review.ConfluenceClient", return_value=FakeConfluenceClient()):
            runner.invoke(review.review_command, ["push-questions", "--doc", "validate"])
            runner.invoke(review.review_command, ["submit", "--doc", "validate"])

        assert len(fake_jira.added_comments) == 1
        issue_key, text = fake_jira.added_comments[0]
        assert "ready for full review" in text

    def test_pull_answers_patches_both_docs_and_multi_location_question(self, blocked_project, runner):
        from sdd.utils.atlassian_auth import Profile
        fake_jira = FakeJiraClient()
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=fake_jira), \
             patch("sdd.commands.review.ConfluenceClient", return_value=FakeConfluenceClient()):
            runner.invoke(review.review_command, ["push-questions", "--doc", "validate"])
            issue_key = review._load_review_links()["validate"]["key"]
            fake_jira.comments_by_key[issue_key] = [{
                "body": "brd:NC-001: Demonstrates real-time settlement.\n"
                        "brd:NC-002: 90 days per policy DR-014.",
                "author": {"displayName": "PO"}, "created": "2026-01-02T00:00:00+00:00",
            }]
            result = runner.invoke(review.review_command, ["pull-answers", "--doc", "validate"])

        assert result.exit_code == 0, result.output
        brd_text = (blocked_project / ".specify" / "features" / "auth" / "brd.md").read_text()
        srd_text = (blocked_project / ".specify" / "features" / "auth" / "srd.md").read_text()
        assert "Demonstrates real-time settlement." in brd_text
        assert "NEEDS CLARIFICATION-001" not in brd_text
        # brd:NC-002's answer must also patch srd:NC-001 (multi-location row)
        assert "90 days per policy DR-014." in brd_text
        assert "90 days per policy DR-014." in srd_text
        assert "NEEDS CLARIFICATION-001" not in srd_text

    def test_pull_answers_exits_quietly_when_no_ticket_recorded_yet(self, blocked_project, runner):
        result = runner.invoke(review.review_command, ["pull-answers", "--doc", "validate"])
        assert result.exit_code == 0

    def test_pull_answers_exits_quietly_when_not_configured(self, project, runner):
        result = runner.invoke(review.review_command, ["pull-answers", "--doc", "validate"])
        assert result.exit_code == 0

    @pytest.fixture()
    def legacy_blocked_project(self, project):
        """Reproduces the reported production bug: validate.md's table
        displays synthesized brd:NC-001/use-cases:NC-001-style IDs
        (order-of-appearance) even though the underlying docs predate the
        NEEDS CLARIFICATION-NNN numbering feature and still use the old
        unnumbered `[NEEDS CLARIFICATION: ...]` form. Also exercises the
        `uc` -> `use-cases` doc-key alias, since that's how the AI
        abbreviated the Locations column in the real report."""
        (project / ".specify" / "features" / "auth" / "brd.md").write_text(
            "# BRD\n> Version: 1.0 | Status: Draft\n\n"
            "§4 [NEEDS CLARIFICATION: What business problem does this solve?]\n\n"
            "## Version History\n\n| Version | Date | Changed By | Summary | CHG-NNN |\n"
            "|---|---|---|---|---|\n| 1.0 | 2026-01-01 | init | Initial draft | — |\n"
        )
        (project / ".specify" / "features" / "auth" / "use-cases.md").write_text(
            "# Use Cases\n> Version: 1.0 | Status: Draft\n\n"
            "§2 [NEEDS CLARIFICATION: What HTTP status should a duplicate return?]\n\n"
            "## Version History\n\n| Version | Date | Changed By | Summary | CHG-NNN |\n"
            "|---|---|---|---|---|\n| 1.0 | 2026-01-01 | init | Initial draft | — |\n"
        )
        (project / ".specify" / "features" / "auth" / "validate.md").write_text(
            "# Validation Report\n> Version: 1.0 | Status: BLOCKED\n\n"
            "| ID | Locations | Question |\n|---|---|---|\n"
            "| brd:NC-001 | brd:NC-001 | What business problem does this solve? |\n"
            "| uc:NC-001 | uc:NC-001 | What HTTP status should a duplicate return? |\n"
        )
        (project / ".specify" / "integrations.yml").write_text(
            "profile: default\n"
            "jira:\n  project_key: MYPROJ\n"
            "confluence:\n  space_key: ENG\n"
            "document_reviews:\n"
            "  validate:\n"
            "    reviewer_jira_user: '712020:abc'\n"
            "    reviewer_role: 'Business Analyst'\n"
            "    phase: specify\n"
            "    sequence: 4\n"
            "    confluence_page: '{feature} — Validation'\n"
        )
        return project

    def test_pull_answers_retrofits_legacy_unnumbered_markers_and_patches(
        self, legacy_blocked_project, runner
    ):
        from sdd.utils.atlassian_auth import Profile
        fake_jira = FakeJiraClient()
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=fake_jira), \
             patch("sdd.commands.review.ConfluenceClient", return_value=FakeConfluenceClient()):
            runner.invoke(review.review_command, ["push-questions", "--doc", "validate"])
            issue_key = review._load_review_links()["validate"]["key"]
            fake_jira.comments_by_key[issue_key] = [{
                "body": "brd:NC-001: Demonstrates real-time settlement.\n"
                        "uc:NC-001: 409 Conflict.",
                "author": {"displayName": "PO"}, "created": "2026-01-02T00:00:00+00:00",
            }]
            # Before the fix, brd.md/use-cases.md still have the OLD
            # unnumbered `[NEEDS CLARIFICATION: ...]` form -- confirm that
            # precondition explicitly, matching the live `grep -o
            # "NEEDS CLARIFICATION-[0-9]*"` diagnostic that proved the bug.
            brd_before = (legacy_blocked_project / ".specify" / "features" / "auth" / "brd.md").read_text()
            assert "NEEDS CLARIFICATION-" not in brd_before

            result = runner.invoke(review.review_command, ["pull-answers", "--doc", "validate"])

        assert result.exit_code == 0, result.output
        brd_text = (legacy_blocked_project / ".specify" / "features" / "auth" / "brd.md").read_text()
        uc_text = (legacy_blocked_project / ".specify" / "features" / "auth" / "use-cases.md").read_text()
        assert "Demonstrates real-time settlement." in brd_text
        assert "NEEDS CLARIFICATION" not in brd_text
        assert "409 Conflict." in uc_text
        assert "NEEDS CLARIFICATION" not in uc_text

    def test_pull_answers_refreshes_confluence_pages_of_patched_docs(self, blocked_project, runner):
        """BRD/SRD's Confluence pages (created back at their own
        /specify-brd -> `sdd review submit` time) must not go stale once
        pull-answers resolves their markers -- each patched doc's page
        should be re-pushed automatically, not left showing the
        pre-answer [NEEDS CLARIFICATION] text until someone remembers to
        run `sdd confluence push --doc brd` by hand."""
        from sdd.utils.atlassian_auth import Profile
        fake_jira = FakeJiraClient()
        fake_confluence = FakeConfluenceClient()
        with patch("sdd.commands.review.load_profile",
                    return_value=Profile(auth_mode="basic", base_url="https://x.atlassian.net")), \
             patch("sdd.commands.review.build_session", return_value=object()), \
             patch("sdd.commands.review.JiraClient", return_value=fake_jira), \
             patch("sdd.commands.review.ConfluenceClient", return_value=fake_confluence), \
             patch("sdd.commands.confluence.ConfluenceClient", return_value=fake_confluence):
            runner.invoke(review.review_command, ["push-questions", "--doc", "validate"])
            issue_key = review._load_review_links()["validate"]["key"]
            fake_jira.comments_by_key[issue_key] = [{
                "body": "brd:NC-001: Demonstrates real-time settlement.\n"
                        "brd:NC-002: 90 days per policy DR-014.",
                "author": {"displayName": "PO"}, "created": "2026-01-02T00:00:00+00:00",
            }]
            result = runner.invoke(review.review_command, ["pull-answers", "--doc", "validate"])

        assert result.exit_code == 0, result.output
        # brd:NC-002's answer patches both brd.md and srd.md (multi-location
        # row) -- both docs' pages must be refreshed, not just brd's.
        # Titles come from integrations.py's _DEFAULT_PAGE_MAP, since this
        # fixture's integrations.yml only configures document_reviews.validate.
        assert "Demo — Business Requirements" in fake_confluence.pages_by_title
        assert "Demo — System Requirements" in fake_confluence.pages_by_title
        assert "Confluence page refreshed" in result.output
