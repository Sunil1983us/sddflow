# Unit tests for sdd/utils/sdd_parser.py -- the newly added pieces:
# derived_uc on Story (links a stories.md entry back to the UC-NNN it was
# bootstrapped from) and parse_use_cases (feeds `sdd jira push --level
# uc-draft`). The pre-existing Story/Task parsing isn't retested here.
from pathlib import Path

from sdd.utils.sdd_parser import _parse_stories_text, parse_use_cases, UseCase


def test_story_with_derived_from_field_sets_derived_uc():
    text = (
        "## Must Have\n\n"
        "### STORY-001 — Submit payment\n"
        "**As** a user **I want** to pay **So that** I complete checkout\n\n"
        "**Derived from:** UC-001\n"
        "**Satisfies:** FR-001\n"
    )
    stories = _parse_stories_text(text)
    assert len(stories) == 1
    assert stories[0].derived_uc == "UC-001"


def test_story_without_derived_from_field_leaves_it_none():
    text = (
        "## Must Have\n\n"
        "### STORY-001 — Submit payment\n"
        "**Satisfies:** FR-001\n"
    )
    stories = _parse_stories_text(text)
    assert stories[0].derived_uc is None


def test_parse_use_cases_extracts_id_and_title(tmp_path: Path):
    (tmp_path / "use-cases.md").write_text(
        "## §3 Use Case Details\n\n"
        "### UC-001 — Submit Outbound Instant Credit Transfer\n"
        "Some body text.\n\n"
        "### UC-002 — Receive Settlement Receipt\n"
        "More body text.\n"
    )
    use_cases = parse_use_cases(tmp_path)
    assert use_cases == [
        UseCase(id="UC-001", title="Submit Outbound Instant Credit Transfer"),
        UseCase(id="UC-002", title="Receive Settlement Receipt"),
    ]


def test_parse_use_cases_missing_file_returns_empty(tmp_path: Path):
    assert parse_use_cases(tmp_path) == []


def test_parse_use_cases_accepts_direct_file_path(tmp_path: Path):
    path = tmp_path / "use-cases.md"
    path.write_text("### UC-001 — Only One\n")
    assert parse_use_cases(path) == [UseCase(id="UC-001", title="Only One")]
