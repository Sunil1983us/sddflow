# Unit tests for the review-approval helpers — the no-Jira/chat approval path.
# Run from repo root:  pytest cli-python/tests -q
from pathlib import Path

import pytest
import yaml

from sdd.commands import review


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
