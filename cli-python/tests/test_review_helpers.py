# Unit tests for the review-approval helpers — the no-Jira/chat approval path.
# Run from repo root:  pytest cli-python/tests -q
from pathlib import Path

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
        assert review._push_doc_page("brd", p) is None

    def test_no_confluence_section_returns_none(self, project):
        (project / ".specify" / "integrations.yml").write_text("profile: default\n")
        p = _write_doc(project, "brd", "Status: Approved")
        assert review._push_doc_page("brd", p) is None


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
        self._next_key = 1

    def find_by_label(self, project_key, label):
        return self.by_label.get(label)

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


class TestLinkReviewTaskToEpic:
    def test_success_records_the_link(self, project):
        client = FakeJiraClient()
        cfg = JiraConfig(project_key="MYPROJ")
        review._link_review_task_to_epic(client, "PROJ-2", "PROJ-1", cfg)
        assert client.parents == [("PROJ-2", "PROJ-1", "parent")]

    def test_failure_prints_diagnosable_warning(self, project, capsys):
        client = RaisingParentClient()
        cfg = JiraConfig(project_key="MYPROJ")
        review._link_review_task_to_epic(client, "PROJ-2", "PROJ-1", cfg)
        out = capsys.readouterr().out
        assert "was not linked under" in out
        assert "PROJ-1" in out
        assert "cannot set field" in out

    def test_failure_does_not_raise(self, project):
        """A failed link must never propagate -- the review ticket itself
        was already created successfully."""
        client = RaisingParentClient()
        cfg = JiraConfig(project_key="MYPROJ")
        review._link_review_task_to_epic(client, "PROJ-2", "PROJ-1", cfg)  # no raise


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
