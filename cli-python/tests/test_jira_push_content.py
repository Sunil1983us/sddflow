# Unit tests for jira.py's content-parity fixes: Feature/Epic gets a real
# description from brd.md, Story/Task always carry Acceptance Criteria.
from __future__ import annotations
from pathlib import Path

import pytest

from sdd.commands.jira import (
    adf_doc, parse_brd_objectives, feature_extra_fields,
    _upsert_issue, _push,
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
        assert doc["content"] == [{"type": "paragraph",
                                    "content": [{"type": "text", "text": " "}]}]


# ── parse_brd_objectives ─────────────────────────────────────────────────────

class TestParseBrdObjectives:
    def test_missing_brd_returns_empty(self, tmp_path):
        assert parse_brd_objectives(tmp_path) == []

    def test_extracts_bo_lines(self, tmp_path):
        (tmp_path / "brd.md").write_text(
            "# BRD\n\n"
            "| BO-001 | Reduce checkout time | High |\n"
            "| BO-002 | Increase conversion | Medium |\n"
        )
        objectives = parse_brd_objectives(tmp_path)
        assert len(objectives) == 2
        assert objectives[0].startswith("BO-001")
        assert "|" not in objectives[0]  # table pipes stripped

    def test_caps_at_ten(self, tmp_path):
        lines = "\n".join(f"BO-{i:03d} Objective number {i} with enough length"
                           for i in range(1, 15))
        (tmp_path / "brd.md").write_text(lines)
        assert len(parse_brd_objectives(tmp_path)) == 10

    def test_short_matches_dropped(self, tmp_path):
        (tmp_path / "brd.md").write_text("BO-1\nBO-002 A real objective line here\n")
        objectives = parse_brd_objectives(tmp_path)
        assert len(objectives) == 1
        assert objectives[0].startswith("BO-002")


# ── feature_extra_fields ─────────────────────────────────────────────────────

class TestFeatureExtraFields:
    def test_uses_placeholder_when_no_objectives_found(self, tmp_path):
        cfg = JiraConfig(project_key="MYPROJ")
        extra = feature_extra_fields(tmp_path, cfg, "instant-credit-transfer")
        bullets = extra["description"]["content"][-1]["content"]
        text = bullets[0]["content"][0]["content"][0]["text"]
        assert "See brd.md" in text

    def test_uses_real_objectives_when_present(self, tmp_path):
        (tmp_path / "brd.md").write_text("BO-001 Reduce checkout time significantly\n")
        cfg = JiraConfig(project_key="MYPROJ")
        extra = feature_extra_fields(tmp_path, cfg, "instant-credit-transfer")
        bullets = extra["description"]["content"][-1]["content"]
        text = bullets[0]["content"][0]["content"][0]["text"]
        assert text.startswith("BO-001")

    def test_priority_is_high(self, tmp_path):
        cfg = JiraConfig(project_key="MYPROJ")
        extra = feature_extra_fields(tmp_path, cfg, "feat")
        assert extra["priority"] == {"name": "High"}

    def test_epic_name_field_set_only_when_configured(self, tmp_path):
        cfg = JiraConfig(project_key="MYPROJ", custom_fields={"epic_name": "customfield_10011"})
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
        key, created = _upsert_issue(client, "MYPROJ", "Task", "My summary",
                                      {}, "sdd:feat:TASK-001", ["sdd-generated"])
        assert created is True
        assert key == "PROJ-1"
        assert client.created[0]["summary"] == "My summary"
        assert "sdd:feat:TASK-001" in client.created[0]["labels"]

    def test_updates_when_found(self):
        client = FakeJiraClient()
        client.by_label["sdd:feat:TASK-001"] = {"key": "PROJ-9"}
        key, created = _upsert_issue(client, "MYPROJ", "Task", "My summary",
                                      {}, "sdd:feat:TASK-001", ["sdd-generated"])
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
        story = Story(id="STORY-001", title="Login", moscow="must-have",
                       description="As a user I want to log in",
                       acceptance_criteria=["Given valid creds, user is logged in"],
                       story_points=3, satisfies=["FR-001"])
        _push(client, "feat", tmp_path, [story], [], self._cfg())

        story_issue = client.created[1]  # [0] is the Feature
        text = _flatten_adf_text(story_issue["description"])
        assert "Acceptance Criteria" in text
        assert "Given valid creds, user is logged in" in text

    def test_task_description_always_includes_acceptance_criteria(self, tmp_path):
        """Regression test for the bug found during manual QA: Task AC was
        parsed but never written anywhere in the CLI push path."""
        client = FakeJiraClient()
        task = Task(id="TASK-001", title="Implement login endpoint", story_id=None,
                    satisfies=["FR-001"], estimate="~50 lines",
                    description="Build the /login endpoint",
                    acceptance_criteria=["Returns 200 on valid credentials"])
        _push(client, "feat", tmp_path, [], [task], self._cfg())

        task_issue = client.created[1]  # [0] is the Feature
        text = _flatten_adf_text(task_issue["description"])
        assert "Acceptance Criteria" in text
        assert "Returns 200 on valid credentials" in text

    def test_task_with_no_acceptance_criteria_has_no_ac_line(self, tmp_path):
        client = FakeJiraClient()
        task = Task(id="TASK-001", title="Refactor", story_id=None,
                    satisfies=[], estimate=None, description="Cleanup",
                    acceptance_criteria=[])
        _push(client, "feat", tmp_path, [], [task], self._cfg())
        task_issue = client.created[1]
        text = _flatten_adf_text(task_issue["description"])
        assert "Acceptance Criteria" not in text

    def test_feature_gets_business_objectives_description(self, tmp_path):
        (tmp_path / "brd.md").write_text("BO-001 Reduce cart abandonment rate\n")
        client = FakeJiraClient()
        _push(client, "feat", tmp_path, [], [], self._cfg())
        feature_issue = client.created[0]
        text = _flatten_adf_text(feature_issue["description"])
        assert "Business Objectives" in text
        assert "BO-001" in text

    def test_story_parented_to_feature(self, tmp_path):
        client = FakeJiraClient()
        story = Story(id="STORY-001", title="Login", moscow="must-have",
                       description="", acceptance_criteria=[],
                       story_points=None, satisfies=[])
        _push(client, "feat", tmp_path, [story], [], self._cfg())

        feature_key = client.by_label["sdd-feature:feat"]["key"]
        story_key = client.by_label["sdd:feat:STORY-001"]["key"]
        assert len(client.parents) == 1
        child_key, parent_key, _ = client.parents[0]
        assert child_key == story_key
        assert parent_key == feature_key

    def test_task_parented_to_story(self, tmp_path):
        client = FakeJiraClient()
        story = Story(id="STORY-001", title="Login", moscow="must-have",
                       description="", acceptance_criteria=[],
                       story_points=None, satisfies=[])
        task = Task(id="TASK-001", title="Endpoint", story_id="STORY-001",
                    satisfies=[], estimate=None, description="",
                    acceptance_criteria=[])
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
