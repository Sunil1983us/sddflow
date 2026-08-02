# Unit tests for sdd/utils/sdd_parser.py.
#
# This file previously only covered derived_uc/parse_use_cases and
# explicitly noted "the pre-existing Story/Task parsing isn't retested
# here" -- which is exactly how a real bug slipped through: the parser's
# regexes (### STORY-NNN em-dash heading, **Satisfies:**/**As a** bold
# fields, ## TASK-NNN H2 heading) never matched what the shipped
# templates (feature-story-template.md / tasks-template.md) actually
# generate (### STORY-NNN: colon heading, **Linked FRs:**/**As** fields,
# ### TASK-NNN H3 heading with plain unbolded fields) -- so `sdd jira
# push` and `sdd pr create --task` silently found zero stories/tasks for
# every real generated stories.md/tasks.md. The golden-template tests
# below parse the actual shipped template files directly so a future
# template edit that breaks the parser fails CI instead of shipping.
from pathlib import Path

from sdd.utils.sdd_parser import (
    UseCase,
    _parse_stories_text,
    _parse_tasks_text,
    parse_use_cases,
)

_PACKS_ROOT = (
    Path(__file__).resolve().parents[2]
    / "packs"
    / "sdd-backend-service"
    / ".specify"
    / "templates"
)


def _load_template(name: str) -> str:
    return (_PACKS_ROOT / name).read_text().replace("{NNN}", "001")


# ── golden: the actual shipped templates must parse correctly ─────────────────


def test_current_shipped_story_template_parses_correctly():
    stories = _parse_stories_text(_load_template("feature-story-template.md"))
    assert len(stories) == 3  # 2 Must Have + 1 Should Have illustrative stories
    assert [s.moscow for s in stories] == ["must-have", "must-have", "should-have"]
    for s in stories:
        assert s.id == "STORY-001"
        assert s.satisfies, "Linked FRs: field must be extracted"
        assert s.acceptance_criteria, "Acceptance Criteria: bullets must be extracted"
        assert (
            "As" in s.description
            and "I want" in s.description
            and "So that" in s.description
        )


def test_current_shipped_tasks_template_parses_correctly():
    tasks = _parse_tasks_text(_load_template("tasks-template.md"))
    assert len(tasks) == 14  # Phase A(4) + B(2) + C(2) + D(3) + E(1) + F(1) + G/PERF(1)
    assert tasks[0].id == "TASK-001"
    assert tasks[-1].id == "PERF-001"  # Phase G perf task keeps its own prefix
    for t in tasks:
        assert t.story_id == "STORY-001"
        assert t.satisfies
        assert t.estimate
        assert t.acceptance_criteria


def test_current_shipped_task_ac_bullets_have_checkbox_marker_stripped():
    tasks = _parse_tasks_text(_load_template("tasks-template.md"))
    for t in tasks:
        for criterion in t.acceptance_criteria:
            assert not criterion.startswith("[ ]")
            assert not criterion.startswith("[x]")


def test_perf_task_inline_files_field_captured_as_description():
    tasks = _parse_tasks_text(_load_template("tasks-template.md"))
    perf = tasks[-1]
    assert perf.description  # inline "Files: perf/load-test-{nfr}.js" style


# ── current template field styles, isolated ────────────────────────────────


def test_story_colon_heading_and_unbolded_as_field():
    text = (
        "## Must Have Stories\n\n"
        "### STORY-001: Submit Payment\n"
        "**As** a payments operator\n"
        "**I want** to submit an instant credit transfer\n"
        "**So that** funds move immediately\n\n"
        "**Linked FRs:** FR-001, FR-002\n"
        "**Story Points:** 5 | **Sprint:** 1\n\n"
        "**Acceptance Criteria:**\n"
        "- [ ] Given valid payload, then a message is generated\n"
    )
    stories = _parse_stories_text(text)
    assert len(stories) == 1
    s = stories[0]
    assert s.id == "STORY-001"
    assert s.title == "Submit Payment"
    assert s.moscow == "must-have"
    assert s.satisfies == ["FR-001", "FR-002"]
    assert s.story_points == 5
    assert s.acceptance_criteria == ["Given valid payload, then a message is generated"]


def test_task_h3_heading_and_plain_unbolded_fields():
    text = (
        "### TASK-001 — Project Scaffold + Dependencies\n"
        "Story: STORY-001\n"
        "Satisfies: NFR-001 (build), NFR-002 (tech stack)\n"
        "Dependencies: none\n"
        "Estimated lines: ~50 | PR: single\n"
        "Files:\n"
        "  pom.xml\n"
        "  application.yml\n"
        "Acceptance criteria:\n"
        "  - [ ] Build tool configured with all required dependencies\n"
        "  - [ ] Language version locked\n"
    )
    tasks = _parse_tasks_text(text)
    assert len(tasks) == 1
    t = tasks[0]
    assert t.id == "TASK-001"
    assert t.story_id == "STORY-001"
    assert t.satisfies == ["NFR-001 (build)", "NFR-002 (tech stack)"]
    assert t.estimate == "~50 | PR: single"
    assert t.description == "pom.xml\napplication.yml"
    assert t.acceptance_criteria == [
        "Build tool configured with all required dependencies",
        "Language version locked",
    ]


def test_perf_prefix_task_heading_is_parsed():
    text = (
        "### PERF-001 — Load Test: NFR-005\n"
        "Story: STORY-001\n"
        "Satisfies: NFR-005\n"
        "Estimated lines: ~60 | PR: single\n"
        "Files: perf/load-test-nfr005.js\n"
        "Acceptance criteria:\n"
        "  - [ ] P99 response <= 500ms\n"
    )
    tasks = _parse_tasks_text(text)
    assert len(tasks) == 1
    assert tasks[0].id == "PERF-001"
    assert tasks[0].description == "perf/load-test-nfr005.js"


def test_moscow_bucket_header_with_trailing_word_normalizes_correctly():
    text = (
        "## Must Have Stories\n\n"
        "### STORY-001: A\n**As** x\n\n"
        "## Should Have Stories\n\n"
        "### STORY-002: B\n**As** y\n\n"
        "## Could Have Stories\n\n"
        "### STORY-003: C\n**As** z\n"
    )
    stories = _parse_stories_text(text)
    assert [s.moscow for s in stories] == ["must-have", "should-have", "could-have"]


# ── older generated-doc style (em-dash heading, bold fields, H2 tasks,
#    Description: paragraph, Estimate: not Estimated lines:) still parses ──


def test_older_em_dash_heading_and_bold_satisfies_still_parses():
    text = (
        "## Must Have\n\n"
        "### STORY-001 — Create a Task\n"
        "**As a** registered user  \n"
        "**I want to** create a task  \n"
        "**So that** I can track work\n\n"
        "**Acceptance Criteria:**\n"
        "- AC-001-1: POST /tasks returns 201\n\n"
        "**Story Points:** 3  \n"
        "**Satisfies:** FR-001, FR-002\n"
    )
    stories = _parse_stories_text(text)
    assert len(stories) == 1
    s = stories[0]
    assert s.id == "STORY-001"
    assert s.satisfies == ["FR-001", "FR-002"]
    assert s.story_points == 3
    assert s.acceptance_criteria == ["AC-001-1: POST /tasks returns 201"]


def test_older_h2_heading_bold_fields_and_description_paragraph_still_parses():
    text = (
        "## TASK-001 — Prisma Schema + Migration\n\n"
        "**Story:** STORY-001 (Create a Task)  \n"
        "**Satisfies:** FR-001, FR-002  \n"
        "**Estimate:** ~50 lines (schema) + ~30 lines (migration)\n\n"
        "**Description:**  \n"
        "Define the `tasks` table in `prisma/schema.prisma`.\n\n"
        "**Acceptance Criteria:**\n"
        "- [ ] `tasks` table created with all columns\n"
    )
    tasks = _parse_tasks_text(text)
    assert len(tasks) == 1
    t = tasks[0]
    assert t.id == "TASK-001"
    assert t.story_id == "STORY-001"
    assert t.satisfies == ["FR-001", "FR-002"]
    assert t.estimate == "~50 lines (schema) + ~30 lines (migration)"
    assert "Define the" in t.description
    assert t.acceptance_criteria == ["`tasks` table created with all columns"]


# ── pre-existing coverage: derived_uc / parse_use_cases ────────────────────


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
    text = "## Must Have\n\n### STORY-001 — Submit payment\n**Satisfies:** FR-001\n"
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
