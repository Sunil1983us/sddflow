# Unit tests for jira.py's content-parity fixes: Feature/Epic gets a real
# description from brd.md, Story/Task always carry Acceptance Criteria.
from __future__ import annotations
import json
from pathlib import Path

import pytest

from sdd.commands.jira import (
    adf_doc,
    adf_sections,
    feature_extra_fields,
    parse_brd_problem_statement,
    parse_brd_business_hypothesis,
    parse_brd_executive_summary,
    parse_brd_out_of_scope,
    parse_srd_nfr_rows,
    parse_brd_business_objectives,
    parse_brd_success_criteria,
    brd_confluence_link,
    _resolve_confluence_base_url,
    _upsert_issue,
    _push,
)
from sdd.utils.integrations import JiraConfig
from sdd.utils.sdd_parser import Story, Task


# ── adf_doc ──────────────────────────────────────────────────────────────────


class TestAdfDoc:
    def test_filters_blank_and_falsy_paragraphs(self):
        doc = adf_doc("Real line", "", None, "   ", "Another real line")
        texts = [p["content"][0]["text"] for p in doc["content"]]
        assert texts == ["Real line", "Another real line"]

    def test_bullet_list_appended_when_provided(self):
        doc = adf_doc("Heading:", bullet_list=["one", "two"])
        assert doc["content"][-1]["type"] == "bulletList"
        assert len(doc["content"][-1]["content"]) == 2

    def test_empty_bullet_items_filtered(self):
        doc = adf_doc(bullet_list=["one", "", None, "two"])
        assert len(doc["content"][-1]["content"]) == 2

    def test_falls_back_to_blank_paragraph_when_nothing_given(self):
        doc = adf_doc()
        assert doc["content"] == [
            {"type": "paragraph", "content": [{"type": "text", "text": " "}]}
        ]


class TestAdfSections:
    def test_string_body_becomes_heading_plus_paragraph(self):
        doc = adf_sections(("Problem Statement", "Users churn."))
        assert doc["content"][0] == {
            "type": "heading",
            "attrs": {"level": 3},
            "content": [{"type": "text", "text": "Problem Statement"}],
        }
        assert doc["content"][1]["type"] == "paragraph"

    def test_list_body_becomes_heading_plus_bullet_list(self):
        doc = adf_sections(("Out of Scope", ["A", "B"]))
        assert doc["content"][0]["type"] == "heading"
        assert doc["content"][1]["type"] == "bulletList"
        assert len(doc["content"][1]["content"]) == 2

    def test_empty_body_section_omitted_entirely(self):
        doc = adf_sections(
            ("Problem Statement", "Real content"), ("NFR", []), ("Out of Scope", "")
        )
        headings = [
            n["content"][0]["text"] for n in doc["content"] if n["type"] == "heading"
        ]
        assert headings == ["Problem Statement"]

    def test_all_empty_falls_back_to_blank_paragraph(self):
        doc = adf_sections(("A", ""), ("B", []))
        assert doc["content"] == [
            {"type": "paragraph", "content": [{"type": "text", "text": " "}]}
        ]


# ── brd.md / srd.md section parsers ─────────────────────────────────────────

_BRD_ALL_SECTIONS = (
    "## 1. Executive Summary\n"
    "The thing being built, in a nutshell.\n\n"
    "## 2. Business Objectives\n\n"
    "| ID | Objective | Success Metric |\n"
    "|---|---|---|\n"
    "| BO-001 | Reduce cart abandonment | Abandonment rate < 20% |\n"
    "| BO-002 | Speed up checkout | < 30s median checkout time |\n\n"
    "## 4. Business Context\n"
    "### Problem Statement\n"
    "Checkout takes too many steps and users abandon their cart.\n\n"
    "### Business Hypothesis\n"
    "We believe that a one-click checkout will result in fewer abandoned "
    "carts. We'll know this is true when abandonment drops below 20%.\n\n"
    "### Scope\n"
    "In Scope:\n"
    "- One-click checkout for returning customers\n\n"
    "Out of Scope:\n"
    "- Guest checkout redesign\n"
    "- Payment provider migration\n\n"
    "## 5. Business Requirements\n\n"
    "## 8. Success Criteria\n"
    "- [ ] Cart abandonment rate drops below 20%\n"
    "- [ ] Median checkout time under 30 seconds\n\n"
    "## 9. Investment Summary\n"
)


class TestBrdSectionParsers:
    def test_missing_brd_returns_empty_for_every_parser(self, tmp_path):
        assert parse_brd_problem_statement(tmp_path) == ""
        assert parse_brd_business_hypothesis(tmp_path) == ""
        assert parse_brd_executive_summary(tmp_path) == ""
        assert parse_brd_out_of_scope(tmp_path) == []

    def test_extracts_all_sections(self, tmp_path):
        (tmp_path / "brd.md").write_text(_BRD_ALL_SECTIONS)
        assert "abandon their cart" in parse_brd_problem_statement(tmp_path)
        assert "fewer abandoned carts" in parse_brd_business_hypothesis(tmp_path)
        assert "nutshell" in parse_brd_executive_summary(tmp_path)
        assert parse_brd_out_of_scope(tmp_path) == [
            "Guest checkout redesign",
            "Payment provider migration",
        ]

    def test_unfilled_template_placeholder_treated_as_empty(self, tmp_path):
        (tmp_path / "brd.md").write_text(
            "## 4. Business Context\n"
            "### Problem Statement\n"
            "{What problem does this solve? What happens today without this?}\n\n"
            "### Scope\n"
            "Out of Scope:\n"
            "- {item}\n"
        )
        assert parse_brd_problem_statement(tmp_path) == ""
        assert parse_brd_out_of_scope(tmp_path) == []

    def test_in_scope_bullets_not_mistaken_for_out_of_scope(self, tmp_path):
        (tmp_path / "brd.md").write_text(_BRD_ALL_SECTIONS)
        out_of_scope = parse_brd_out_of_scope(tmp_path)
        assert "One-click checkout for returning customers" not in out_of_scope


class TestSrdNfrParser:
    def test_missing_srd_returns_empty(self, tmp_path):
        assert parse_srd_nfr_rows(tmp_path) == []

    def test_extracts_nfr_rows(self, tmp_path):
        (tmp_path / "srd.md").write_text(
            "## 3. Non-Functional Requirements\n\n"
            "| ID | Category | Requirement |\n"
            "|---|---|---|\n"
            "| NFR-001 | Performance | < 200ms p99 |\n"
            "| NFR-002 | Availability | 99.9% uptime |\n"
        )
        rows = parse_srd_nfr_rows(tmp_path)
        assert rows == ["Performance: < 200ms p99", "Availability: 99.9% uptime"]

    def test_unfilled_template_row_skipped(self, tmp_path):
        (tmp_path / "srd.md").write_text(
            "| ID | Category | Requirement |\n"
            "|---|---|---|\n"
            "| NFR-{NNN} | Security | {e.g. all endpoints require auth} |\n"
        )
        assert parse_srd_nfr_rows(tmp_path) == []


class TestBrdBusinessObjectivesParser:
    def test_missing_brd_returns_empty(self, tmp_path):
        assert parse_brd_business_objectives(tmp_path) == []

    def test_extracts_objective_and_metric(self, tmp_path):
        (tmp_path / "brd.md").write_text(_BRD_ALL_SECTIONS)
        objectives = parse_brd_business_objectives(tmp_path)
        assert objectives == [
            "BO-001: Reduce cart abandonment — Abandonment rate < 20%",
            "BO-002: Speed up checkout — < 30s median checkout time",
        ]

    def test_objective_without_metric_omits_dash(self, tmp_path):
        (tmp_path / "brd.md").write_text(
            "## 2. Business Objectives\n\n"
            "| ID | Objective | Success Metric |\n"
            "|---|---|---|\n"
            "| BO-001 | Reduce cart abandonment | |\n"
        )
        assert parse_brd_business_objectives(tmp_path) == [
            "BO-001: Reduce cart abandonment"
        ]

    def test_unfilled_template_row_skipped(self, tmp_path):
        (tmp_path / "brd.md").write_text(
            "| ID | Objective | Success Metric |\n"
            "|---|---|---|\n"
            "| BO-{NNN} | {objective} | {how measured} |\n"
        )
        assert parse_brd_business_objectives(tmp_path) == []


class TestBrdSuccessCriteriaParser:
    def test_missing_brd_returns_empty(self, tmp_path):
        assert parse_brd_success_criteria(tmp_path) == []

    def test_extracts_checklist_items(self, tmp_path):
        (tmp_path / "brd.md").write_text(_BRD_ALL_SECTIONS)
        assert parse_brd_success_criteria(tmp_path) == [
            "Cart abandonment rate drops below 20%",
            "Median checkout time under 30 seconds",
        ]

    def test_unfilled_template_item_skipped(self, tmp_path):
        (tmp_path / "brd.md").write_text(
            "## 8. Success Criteria\n"
            "- [ ] {verifiable end-to-end criterion}\n"
            "- [ ] {verifiable criterion}\n"
        )
        assert parse_brd_success_criteria(tmp_path) == []

    def test_other_checklists_elsewhere_not_captured(self, tmp_path):
        """Only the Success Criteria heading's own checkboxes count -- a
        checkbox elsewhere in the document (e.g. a compliance table cell)
        must not leak in."""
        (tmp_path / "brd.md").write_text(
            "## 6. Regulatory and Compliance\n"
            "| Regulation | Requirement | Impact | [ ] |\n\n"
            "## 8. Success Criteria\n"
            "- [ ] Real criterion\n"
        )
        assert parse_brd_success_criteria(tmp_path) == ["Real criterion"]


class TestBrdConfluenceLink:
    def test_no_base_url_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert brd_confluence_link(None) is None

    def test_no_drafts_file_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert brd_confluence_link("https://x.atlassian.net") is None

    def test_no_brd_entry_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".specify").mkdir()
        (tmp_path / ".specify" / ".confluence-drafts.json").write_text(
            json.dumps({"srd": {"page_id": "999", "title": "SRD"}})
        )
        assert brd_confluence_link("https://x.atlassian.net") is None

    def test_builds_url_from_page_id(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".specify").mkdir()
        (tmp_path / ".specify" / ".confluence-drafts.json").write_text(
            json.dumps({"brd": {"page_id": "123456", "title": "BRD"}})
        )
        url = brd_confluence_link("https://x.atlassian.net")
        assert url == "https://x.atlassian.net/wiki/pages/viewpage.action?pageId=123456"


class TestResolveConfluenceBaseUrl:
    def test_no_confluence_section_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cfg = type("Cfg", (), {"confluence": None})()
        assert _resolve_confluence_base_url(cfg) is None

    def test_missing_profile_returns_none_not_raises(self, tmp_path, monkeypatch):
        """No ~/.sdd/config.yml at all (or no matching profile) -- this is
        a purely cosmetic link, so failures here must never surface as an
        error, let alone block the Jira push."""
        from sdd.utils import atlassian_auth

        monkeypatch.setattr(atlassian_auth, "CONFIG_PATH", tmp_path / "nonexistent.yml")
        cfg = type(
            "Cfg",
            (),
            {
                "confluence": object(),
                "confluence_profile_name": lambda self: "nonexistent",
            },
        )()
        assert _resolve_confluence_base_url(cfg) is None


# ── feature_extra_fields ─────────────────────────────────────────────────────


class TestFeatureExtraFields:
    def test_uses_placeholder_when_nothing_found(self, tmp_path):
        cfg = JiraConfig(project_key="MYPROJ")
        extra = feature_extra_fields(tmp_path, cfg, "instant-credit-transfer")
        text = _flatten_adf_text(extra["description"])
        assert "Details pending" in text
        assert "/specify-brd" in text

    def test_uses_real_sections_when_present(self, tmp_path):
        (tmp_path / "brd.md").write_text(_BRD_ALL_SECTIONS)
        (tmp_path / "srd.md").write_text(
            "## 3. Non-Functional Requirements\n\n"
            "| ID | Category | Requirement |\n"
            "|---|---|---|\n"
            "| NFR-001 | Performance | < 200ms p99 |\n"
        )
        cfg = JiraConfig(project_key="MYPROJ")
        extra = feature_extra_fields(tmp_path, cfg, "instant-credit-transfer")
        text = _flatten_adf_text(extra["description"])
        for expected in (
            "Problem Statement",
            "abandon their cart",
            "Business Hypothesis",
            "fewer abandoned carts",
            "Description",
            "nutshell",
            "Business Objectives",
            "BO-001: Reduce cart abandonment",
            "Out of Scope",
            "Guest checkout redesign",
            "Success Criteria",
            "Median checkout time under 30 seconds",
            "NFR",
            "Performance: < 200ms p99",
        ):
            assert expected in text, f"missing: {expected}"

    def test_confluence_link_appended_when_brd_page_pushed(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "brd.md").write_text(_BRD_ALL_SECTIONS)
        (tmp_path / ".specify").mkdir()
        (tmp_path / ".specify" / ".confluence-drafts.json").write_text(
            json.dumps({"brd": {"page_id": "123456", "title": "BRD"}})
        )
        cfg = JiraConfig(project_key="MYPROJ")
        extra = feature_extra_fields(tmp_path, cfg, "feat", "https://x.atlassian.net")
        text = _flatten_adf_text(extra["description"])
        assert "Full Document" in text
        assert "View BRD on Confluence" in text
        link_node = extra["description"]["content"][-1]["content"][0]
        assert link_node["marks"][0]["attrs"]["href"] == (
            "https://x.atlassian.net/wiki/pages/viewpage.action?pageId=123456"
        )

    def test_no_confluence_link_when_brd_not_pushed(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "brd.md").write_text(_BRD_ALL_SECTIONS)
        cfg = JiraConfig(project_key="MYPROJ")
        extra = feature_extra_fields(tmp_path, cfg, "feat", "https://x.atlassian.net")
        text = _flatten_adf_text(extra["description"])
        assert "Full Document" not in text

    def test_section_missing_its_own_source_is_omitted_not_placeholder(self, tmp_path):
        """brd.md exists (so Problem Statement/etc. are present) but
        srd.md doesn't yet -- NFR must be silently omitted, not force the
        whole description into the "nothing found" placeholder."""
        (tmp_path / "brd.md").write_text(_BRD_ALL_SECTIONS)
        cfg = JiraConfig(project_key="MYPROJ")
        extra = feature_extra_fields(tmp_path, cfg, "instant-credit-transfer")
        text = _flatten_adf_text(extra["description"])
        assert "Problem Statement" in text
        assert "NFR" not in text
        assert "Details pending" not in text

    def test_priority_is_high(self, tmp_path):
        cfg = JiraConfig(project_key="MYPROJ")
        extra = feature_extra_fields(tmp_path, cfg, "feat")
        assert extra["priority"] == {"name": "High"}

    def test_epic_name_field_set_only_when_configured(self, tmp_path):
        cfg = JiraConfig(
            project_key="MYPROJ", custom_fields={"epic_name": "customfield_10011"}
        )
        extra = feature_extra_fields(tmp_path, cfg, "instant-credit-transfer")
        assert extra["customfield_10011"] == "instant-credit-transfer"

    def test_epic_name_field_absent_when_not_configured(self, tmp_path):
        cfg = JiraConfig(project_key="MYPROJ")
        extra = feature_extra_fields(tmp_path, cfg, "feat")
        assert not any(k.startswith("customfield_") for k in extra)


# ── Fake Jira client for _push / _upsert_issue tests ────────────────────────


class FakeJiraClient:
    """In-memory double for JiraClient — enough surface for _push/_upsert_issue,
    no real HTTP. Tracks every created/updated issue's fields and every
    parent link set, so tests can assert on them directly."""

    def __init__(self):
        self.by_label: dict[str, dict] = {}
        self.created: list[dict] = []
        self.updated: list[tuple[str, dict]] = []
        self.parents: list[tuple[str, str, str]] = []
        self._next_key = 1

    def find_by_label(self, project_key, label):
        return self.by_label.get(label)

    def create_issue(self, fields):
        key = f"PROJ-{self._next_key}"
        self._next_key += 1
        self.created.append(fields)
        # register under whichever label was passed, so a later find works
        for label in fields.get("labels", []):
            if label.startswith("sdd"):
                self.by_label[label] = {"key": key}
        return {"key": key}

    def update_issue(self, key, fields):
        self.updated.append((key, fields))

    def set_parent(self, child_key, parent_key, parent_field="parent"):
        self.parents.append((child_key, parent_key, parent_field))


class TestUpsertIssue:
    def test_creates_when_not_found(self):
        client = FakeJiraClient()
        key, created = _upsert_issue(
            client,
            "MYPROJ",
            "Task",
            "My summary",
            {},
            "sdd:feat:TASK-001",
            ["sdd-generated"],
        )
        assert created is True
        assert key == "PROJ-1"
        assert client.created[0]["summary"] == "My summary"
        assert "sdd:feat:TASK-001" in client.created[0]["labels"]

    def test_updates_when_found(self):
        client = FakeJiraClient()
        client.by_label["sdd:feat:TASK-001"] = {"key": "PROJ-9"}
        key, created = _upsert_issue(
            client,
            "MYPROJ",
            "Task",
            "My summary",
            {},
            "sdd:feat:TASK-001",
            ["sdd-generated"],
        )
        assert created is False
        assert key == "PROJ-9"
        assert client.updated[0][0] == "PROJ-9"


class TestPushContentParity:
    """End-to-end through _push(): confirms Story/Task always carry
    Acceptance Criteria (the bug fixed in this pass) and the Feature/Epic
    gets real content, using the fake client instead of real HTTP."""

    @pytest.fixture(autouse=True)
    def _isolate_cwd(self, tmp_path, monkeypatch):
        # _push() writes a best-effort docs/jira/{feature}/keys.yml summary
        # relative to cwd -- chdir into tmp_path so that write can never
        # land in the real repo tree during a test run.
        monkeypatch.chdir(tmp_path)

    def _cfg(self):
        return JiraConfig(project_key="MYPROJ")

    def test_story_description_always_includes_acceptance_criteria(self, tmp_path):
        client = FakeJiraClient()
        story = Story(
            id="STORY-001",
            title="Login",
            moscow="must-have",
            description="As a user I want to log in",
            acceptance_criteria=["Given valid creds, user is logged in"],
            story_points=3,
            satisfies=["FR-001"],
        )
        _push(client, "feat", tmp_path, [story], [], self._cfg())

        story_issue = client.created[1]  # [0] is the Feature
        text = _flatten_adf_text(story_issue["description"])
        assert "Acceptance Criteria" in text
        assert "Given valid creds, user is logged in" in text

    def test_task_description_always_includes_acceptance_criteria(self, tmp_path):
        """Regression test for the bug found during manual QA: Task AC was
        parsed but never written anywhere in the CLI push path."""
        client = FakeJiraClient()
        task = Task(
            id="TASK-001",
            title="Implement login endpoint",
            story_id=None,
            satisfies=["FR-001"],
            estimate="~50 lines",
            description="Build the /login endpoint",
            acceptance_criteria=["Returns 200 on valid credentials"],
        )
        _push(client, "feat", tmp_path, [], [task], self._cfg())

        task_issue = client.created[1]  # [0] is the Feature
        text = _flatten_adf_text(task_issue["description"])
        assert "Acceptance Criteria" in text
        assert "Returns 200 on valid credentials" in text

    def test_task_with_no_acceptance_criteria_has_no_ac_line(self, tmp_path):
        client = FakeJiraClient()
        task = Task(
            id="TASK-001",
            title="Refactor",
            story_id=None,
            satisfies=[],
            estimate=None,
            description="Cleanup",
            acceptance_criteria=[],
        )
        _push(client, "feat", tmp_path, [], [task], self._cfg())
        task_issue = client.created[1]
        text = _flatten_adf_text(task_issue["description"])
        assert "Acceptance Criteria" not in text

    def test_feature_gets_structured_description(self, tmp_path):
        (tmp_path / "brd.md").write_text(_BRD_ALL_SECTIONS)
        client = FakeJiraClient()
        _push(client, "feat", tmp_path, [], [], self._cfg())
        feature_issue = client.created[0]
        text = _flatten_adf_text(feature_issue["description"])
        assert "Problem Statement" in text
        assert "abandon their cart" in text
        assert "Business Hypothesis" in text

    def test_story_parented_to_feature(self, tmp_path):
        client = FakeJiraClient()
        story = Story(
            id="STORY-001",
            title="Login",
            moscow="must-have",
            description="",
            acceptance_criteria=[],
            story_points=None,
            satisfies=[],
        )
        _push(client, "feat", tmp_path, [story], [], self._cfg())

        feature_key = client.by_label["sdd-feature:feat"]["key"]
        story_key = client.by_label["sdd:feat:STORY-001"]["key"]
        assert len(client.parents) == 1
        child_key, parent_key, _ = client.parents[0]
        assert child_key == story_key
        assert parent_key == feature_key

    def test_task_parented_to_story(self, tmp_path):
        client = FakeJiraClient()
        story = Story(
            id="STORY-001",
            title="Login",
            moscow="must-have",
            description="",
            acceptance_criteria=[],
            story_points=None,
            satisfies=[],
        )
        task = Task(
            id="TASK-001",
            title="Endpoint",
            story_id="STORY-001",
            satisfies=[],
            estimate=None,
            description="",
            acceptance_criteria=[],
        )
        _push(client, "feat", tmp_path, [story], [task], self._cfg())

        story_key = client.by_label["sdd:feat:STORY-001"]["key"]
        task_key = client.by_label["sdd:feat:TASK-001"]["key"]
        # two parent links: story->feature, task->story
        assert len(client.parents) == 2
        task_parent = next(p for p in client.parents if p[0] == task_key)
        assert task_parent[1] == story_key


def _flatten_adf_text(adf: dict) -> str:
    """Flatten an ADF doc's paragraph/bulletList text nodes into one string
    for simple substring assertions in tests."""
    out = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "text":
                out.append(node["text"])
            for child in node.get("content", []):
                walk(child)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(adf)
    return " ".join(out)
