# Unit tests for jira.py's Phase 2 work: --level-scoped pushes (parent
# links found live via Jira labels, not a local cache), CHG support parsed
# from a changeset's §4 table, and the best-effort keys.yml summary writer.
from __future__ import annotations
from pathlib import Path

import pytest
import yaml

from sdd.commands.jira import (
    parse_changeset, _push, _push_chg, _keys_path, _push_uc_draft_stories, _push_stories,
)
from sdd.utils.integrations import JiraConfig
from sdd.utils.sdd_parser import Story, Task, UseCase


class FakeJiraClient:
    """Same in-memory double as test_jira_push_content.py's — duplicated
    here (rather than imported) so this file has no import-order coupling
    to the other test module."""
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
        for label in fields.get("labels", []):
            if label.startswith("sdd"):
                self.by_label[label] = {"key": key}
        return {"key": key}

    def update_issue(self, key, fields):
        self.updated.append((key, fields))

    def set_parent(self, child_key, parent_key, parent_field="parent"):
        self.parents.append((child_key, parent_key, parent_field))


def _cfg(**kw):
    return JiraConfig(project_key="MYPROJ", **kw)


def _story(id="STORY-001", satisfies=None):
    return Story(id=id, title="Login", moscow="must-have", description="",
                 acceptance_criteria=[], story_points=None,
                 satisfies=satisfies or [])


def _write_changeset(tmp_path: Path, cr_id: str, rows: list[tuple[str, str, str, int]]) -> None:
    table = "\n".join(
        f"| {sdd_id} | {desc} | {satisfies} | ~{lines} | single | Pending |"
        for sdd_id, desc, satisfies, lines in rows
    )
    text = (
        "## 4. CHG-NNN Implementation Tasks\n\n"
        "| CHG-NNN | Description | Satisfies | Estimated Lines | PR | Status |\n"
        "|---|---|---|---|---|---|\n"
        f"{table}\n"
    )
    path = tmp_path / "changesets" / f"{cr_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class TestParseChangeset:
    def test_missing_changeset_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            parse_changeset(tmp_path, "CR-001")

    def test_parses_chg_rows_skips_header(self, tmp_path):
        _write_changeset(tmp_path, "CR-001", [
            ("CHG-001", "Add validation", "FR-003", 40),
            ("CHG-002", "Fix rate limit", "FR-004", 20),
        ])
        rows = parse_changeset(tmp_path, "CR-001")
        assert len(rows) == 2
        assert rows[0] == {"sdd_id": "CHG-001", "description": "Add validation",
                            "satisfies": "FR-003", "est_lines": 40}
        assert rows[1]["sdd_id"] == "CHG-002"


class TestLevelScopedPush:
    @pytest.fixture(autouse=True)
    def _isolate_cwd(self, tmp_path, monkeypatch):
        # _push() writes a best-effort docs/jira/{feature}/keys.yml summary
        # relative to cwd -- chdir into tmp_path so that write can never
        # land in the real repo tree during a test run.
        monkeypatch.chdir(tmp_path)

    def test_level_epic_only_creates_feature(self, tmp_path):
        client = FakeJiraClient()
        story = _story()
        _push(client, "feat", tmp_path, [story], [], _cfg(), level="epic")
        assert len(client.created) == 1
        assert "sdd-feature:feat" in client.created[0]["labels"]

    def test_level_story_finds_epic_live_without_repushing_it(self, tmp_path):
        client = FakeJiraClient()
        # Simulate a prior `--level epic` push already having created the Epic.
        client.by_label["sdd-feature:feat"] = {"key": "PROJ-1"}
        story = _story()
        _push(client, "feat", tmp_path, [story], [], _cfg(), level="story")
        # Only the Story should be newly created -- the Epic already existed.
        assert len(client.created) == 1
        assert client.created[0]["summary"] == "STORY-001 — Login"
        story_key = client.by_label["sdd:feat:STORY-001"]["key"]
        assert client.parents == [(story_key, "PROJ-1", "parent")]

    def test_level_story_without_epic_warns_but_still_pushes(self, tmp_path, capsys):
        client = FakeJiraClient()
        story = _story()
        _push(client, "feat", tmp_path, [story], [], _cfg(), level="story")
        assert len(client.created) == 1
        assert client.parents == []  # no epic to link to

    def test_level_task_finds_story_live_without_repushing_it(self, tmp_path):
        client = FakeJiraClient()
        client.by_label["sdd:feat:STORY-001"] = {"key": "PROJ-9"}
        story = _story()
        task = Task(id="TASK-001", title="Endpoint", story_id="STORY-001",
                    satisfies=[], estimate=None, description="", acceptance_criteria=[])
        _push(client, "feat", tmp_path, [story], [task], _cfg(), level="task")
        assert len(client.created) == 1  # only the Task, not the Story
        assert client.parents == [("PROJ-1", "PROJ-9", "parent")]

    def test_level_all_still_pushes_everything(self, tmp_path):
        client = FakeJiraClient()
        story = _story()
        task = Task(id="TASK-001", title="Endpoint", story_id="STORY-001",
                    satisfies=[], estimate=None, description="", acceptance_criteria=[])
        _push(client, "feat", tmp_path, [story], [task], _cfg(), level="all")
        assert len(client.created) == 3  # Feature + Story + Task


class RecordingFakeJiraClient(FakeJiraClient):
    """Same fake, but also records the project_key argument every
    find_by_label call was made with -- lets tests confirm a level's
    lookup used the *overridden* key, not just that create used it."""
    def __init__(self):
        super().__init__()
        self.find_by_label_calls: list[tuple[str, str]] = []

    def find_by_label(self, project_key, label):
        self.find_by_label_calls.append((project_key, label))
        return super().find_by_label(project_key, label)


class TestProjectKeysOverride:
    """cfg.key_for(level) wiring -- when project_keys overrides a level,
    every create_issue/find_by_label call for that level must use the
    override, while un-overridden levels keep falling back to
    project_key. Exercised through the public _push() entry point so
    these tests catch regressions in the call-site wiring, not just in
    JiraConfig.key_for() itself (already covered in
    test_config_and_integrations.py)."""

    @pytest.fixture(autouse=True)
    def _isolate_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

    def _cfg_with_override(self, **project_keys):
        return JiraConfig(project_key="SUN", project_keys=project_keys)

    def test_epic_create_uses_feature_override(self, tmp_path):
        client = RecordingFakeJiraClient()
        cfg = self._cfg_with_override(feature="SUNF")
        _push(client, "feat", tmp_path, [_story()], [], cfg, level="epic")
        assert client.created[0]["project"]["key"] == "SUNF"

    def test_epic_falls_back_to_project_key_when_not_overridden(self, tmp_path):
        client = RecordingFakeJiraClient()
        cfg = self._cfg_with_override(story="SUNT")  # only story overridden
        _push(client, "feat", tmp_path, [_story()], [], cfg, level="epic")
        assert client.created[0]["project"]["key"] == "SUN"

    def test_story_create_and_epic_lookup_use_their_own_overrides(self, tmp_path):
        client = RecordingFakeJiraClient()
        client.by_label["sdd-feature:feat"] = {"key": "SUNF-1"}
        cfg = self._cfg_with_override(feature="SUNF", story="SUNT")
        _push(client, "feat", tmp_path, [_story()], [], cfg, level="story")

        # Epic lookup (to find the parent to link under) used the feature key
        assert ("SUNF", "sdd-feature:feat") in client.find_by_label_calls
        # The Story itself was created under the story-level override
        assert client.created[0]["project"]["key"] == "SUNT"

    def test_task_create_and_story_lookup_use_their_own_overrides(self, tmp_path):
        client = RecordingFakeJiraClient()
        client.by_label["sdd:feat:STORY-001"] = {"key": "SUNT-1"}
        cfg = self._cfg_with_override(story="SUNT", task="SUNK")
        task = Task(id="TASK-001", title="Endpoint", story_id="STORY-001",
                    satisfies=[], estimate=None, description="", acceptance_criteria=[])
        _push(client, "feat", tmp_path, [_story()], [task], cfg, level="task")

        # Story lookup (to find the parent to link the Task under) used the story key
        assert ("SUNT", "sdd:feat:STORY-001") in client.find_by_label_calls
        # The Task itself was created under the task-level override
        assert client.created[0]["project"]["key"] == "SUNK"

    def test_uc_draft_story_create_uses_story_override(self, tmp_path):
        client = RecordingFakeJiraClient()
        cfg = self._cfg_with_override(story="SUNT")
        uc = UseCase(id="UC-001", title="Login")
        _push_uc_draft_stories(client, "feat", [uc], cfg, epic_key=None)
        assert client.created[0]["project"]["key"] == "SUNT"


class TestChgPush:
    @pytest.fixture(autouse=True)
    def _isolate_cwd(self, tmp_path, monkeypatch):
        # test_full_push_level_chg_end_to_end calls _push(), which writes a
        # best-effort docs/jira/{feature}/keys.yml summary relative to cwd.
        monkeypatch.chdir(tmp_path)

    def test_chg_parented_to_story_via_fr_reference(self, tmp_path):
        _write_changeset(tmp_path, "CR-001", [("CHG-001", "Add validation", "FR-003", 40)])
        client = FakeJiraClient()
        story = _story(satisfies=["FR-003"])
        story_key_map = {"STORY-001": "PROJ-5"}
        chg_map = _push_chg(client, "feat", _cfg(), "CR-001", tmp_path,
                             [story], story_key_map, epic_key="PROJ-1")
        chg_key = chg_map["CHG-001"]
        assert client.parents == [(chg_key, "PROJ-5", "parent")]

    def test_chg_falls_back_to_epic_when_no_fr_match(self, tmp_path):
        _write_changeset(tmp_path, "CR-001", [("CHG-001", "Unrelated fix", "NFR-002", 10)])
        client = FakeJiraClient()
        chg_map = _push_chg(client, "feat", _cfg(), "CR-001", tmp_path,
                             [], {}, epic_key="PROJ-1")
        assert client.parents == [(chg_map["CHG-001"], "PROJ-1", "parent")]

    def test_chg_idempotency_label_is_feature_and_id_qualified(self, tmp_path):
        _write_changeset(tmp_path, "CR-001", [("CHG-001", "Add validation", "FR-003", 40)])
        client = FakeJiraClient()
        _push_chg(client, "feat", _cfg(), "CR-001", tmp_path, [], {}, epic_key=None)
        assert "sdd:feat:CHG-001" in client.created[0]["labels"]

    def test_full_push_level_chg_end_to_end(self, tmp_path):
        """`--level chg` through the top-level _push() orchestrator: Story
        key is found live (not re-pushed), CHG is created and parented."""
        _write_changeset(tmp_path, "CR-001", [("CHG-001", "Add validation", "FR-003", 40)])
        client = FakeJiraClient()
        client.by_label["sdd-feature:feat"] = {"key": "PROJ-1"}
        client.by_label["sdd:feat:STORY-001"] = {"key": "PROJ-2"}
        story = _story(satisfies=["FR-003"])
        _push(client, "feat", tmp_path, [story], [], _cfg(), level="chg", cr="CR-001")

        assert len(client.created) == 1  # only the CHG issue -- Feature/Story already existed
        chg_key = client.by_label["sdd:feat:CHG-001"]["key"]
        assert client.parents == [(chg_key, "PROJ-2", "parent")]


class TestFrReferenceCustomField:
    @pytest.fixture(autouse=True)
    def _isolate_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

    def test_story_fr_reference_custom_field_set_when_configured(self, tmp_path):
        client = FakeJiraClient()
        story = _story(satisfies=["FR-001", "FR-002"])
        cfg = _cfg(custom_fields={"fr_reference": "customfield_10101"})
        _push(client, "feat", tmp_path, [story], [], cfg, level="story")
        assert client.created[0]["customfield_10101"] == "FR-001, FR-002"

    def test_story_moscow_priority_custom_field_set_when_configured(self, tmp_path):
        client = FakeJiraClient()
        story = _story()
        cfg = _cfg(custom_fields={"moscow_priority": "customfield_10105"})
        _push(client, "feat", tmp_path, [story], [], cfg, level="story")
        assert client.created[0]["customfield_10105"] == "must-have"

    def test_custom_fields_absent_when_not_configured(self, tmp_path):
        client = FakeJiraClient()
        story = _story(satisfies=["FR-001"])
        _push(client, "feat", tmp_path, [story], [], _cfg(), level="story")
        assert not any(k.startswith("customfield_") for k in client.created[0])


class TestKeysYmlSummary:
    def test_keys_yml_written_after_push(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        client = FakeJiraClient()
        story = _story()
        _push(client, "feat", tmp_path, [story], [], _cfg(), level="all")
        path = _keys_path("feat")
        assert path.exists()
        data = yaml.safe_load(path.read_text())
        assert data["epic"] == "PROJ-1"
        assert data["stories"]["STORY-001"] == "PROJ-2"

    def test_keys_yml_merges_across_separate_level_pushes(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        client = FakeJiraClient()
        _push(client, "feat", tmp_path, [], [], _cfg(), level="epic")
        story = _story()
        client.by_label["sdd-feature:feat"] = {"key": "PROJ-1"}
        _push(client, "feat", tmp_path, [story], [], _cfg(), level="story")

        data = yaml.safe_load(_keys_path("feat").read_text())
        assert data["epic"] == "PROJ-1"
        assert data["stories"]["STORY-001"] == "PROJ-2"

    def test_no_keys_yml_written_when_nothing_pushed(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        client = FakeJiraClient()
        _push(client, "feat", tmp_path, [], [], _cfg(), level="story")
        assert not _keys_path("feat").exists()


class RaisingParentClient(FakeJiraClient):
    """set_parent always fails, like a company-managed Jira project
    rejecting the "parent" field on a Story/Task -- used to confirm a
    failed link now prints a diagnosable warning instead of silently
    vanishing (regression test for the bug found during manual QA)."""
    def set_parent(self, child_key, parent_key, parent_field="parent"):
        raise RuntimeError('HTTP 400 — cannot set field "parent"')


class TestParentLinkFailureIsVisible:
    def test_story_parent_link_failure_prints_warning(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        client = RaisingParentClient()
        client.by_label["sdd-feature:feat"] = {"key": "PROJ-1"}
        story = _story()
        _push(client, "feat", tmp_path, [story], [], _cfg(), level="story")
        out = capsys.readouterr().out
        assert "was not linked under" in out
        assert "PROJ-1" in out
        assert "cannot set field" in out

    def test_task_parent_link_failure_prints_warning(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        client = RaisingParentClient()
        client.by_label["sdd:feat:STORY-001"] = {"key": "PROJ-9"}
        story = _story()
        task = Task(id="TASK-001", title="Endpoint", story_id="STORY-001",
                    satisfies=[], estimate=None, description="", acceptance_criteria=[])
        _push(client, "feat", tmp_path, [story], [task], _cfg(), level="task")
        out = capsys.readouterr().out
        assert "was not linked under" in out
        assert "PROJ-9" in out

    def test_push_does_not_crash_when_link_fails(self, tmp_path, monkeypatch):
        """A failed parent link must never abort the whole push -- the
        issue itself was still created successfully."""
        monkeypatch.chdir(tmp_path)
        client = RaisingParentClient()
        client.by_label["sdd-feature:feat"] = {"key": "PROJ-1"}
        story = _story()
        _push(client, "feat", tmp_path, [story], [], _cfg(), level="story")
        assert len(client.created) == 1


class TestUcDraftStories:
    def test_creates_one_draft_story_per_uc(self):
        client = FakeJiraClient()
        use_cases = [
            UseCase(id="UC-001", title="Submit payment"),
            UseCase(id="UC-002", title="Reconcile settlement"),
        ]
        result = _push_uc_draft_stories(client, "feat", use_cases, _cfg(), epic_key=None)

        assert len(client.created) == 2
        assert result == {"UC-001": "PROJ-1", "UC-002": "PROJ-2"}
        assert client.created[0]["summary"] == "UC-001 — Submit payment (draft)"
        assert client.created[0]["issuetype"] == {"name": "Story"}
        assert "sdd:feat:UC-001" in client.created[0]["labels"]

    def test_parents_draft_stories_to_epic_when_given(self):
        client = FakeJiraClient()
        use_cases = [UseCase(id="UC-001", title="Submit payment")]
        _push_uc_draft_stories(client, "feat", use_cases, _cfg(), epic_key="PROJ-1")
        assert client.parents == [("PROJ-1", "PROJ-1", "parent")]

    def test_rerun_updates_existing_draft_instead_of_duplicating(self):
        client = FakeJiraClient()
        client.by_label["sdd:feat:UC-001"] = {"key": "PROJ-9"}
        use_cases = [UseCase(id="UC-001", title="Submit payment")]
        result = _push_uc_draft_stories(client, "feat", use_cases, _cfg(), epic_key=None)

        assert client.created == []
        assert len(client.updated) == 1
        assert client.updated[0][0] == "PROJ-9"
        assert result == {"UC-001": "PROJ-9"}

    def test_story_derived_from_uc_finalizes_the_draft_in_place(self):
        """A stories.md Story with '**Derived from:** UC-001' must reuse
        the UC's idempotency label -- finalizing the SAME issue
        --level uc-draft created, not creating a second one."""
        client = FakeJiraClient()
        client.by_label["sdd:feat:UC-001"] = {"key": "PROJ-9"}
        story = Story(id="STORY-001", title="Submit payment", moscow="must-have",
                      description="As a user I want to pay",
                      acceptance_criteria=[], story_points=3, satisfies=["FR-001"],
                      derived_uc="UC-001")

        story_key_map = _push_stories(client, "feat", [story], _cfg(), epic_key=None)

        assert client.created == []  # updated the draft, not a new issue
        assert len(client.updated) == 1
        assert client.updated[0][0] == "PROJ-9"
        assert client.updated[0][1]["summary"] == "STORY-001 — Submit payment"
        assert story_key_map == {"STORY-001": "PROJ-9"}

    def test_story_without_derived_uc_uses_its_own_story_id_label(self):
        """Unchanged behavior: a Story with no single-UC origin still gets
        its own sdd:{feature}:STORY-NNN label, exactly as before this
        feature existed."""
        client = FakeJiraClient()
        story = _story()  # derived_uc defaults to None
        assert story.derived_uc is None

        _push_stories(client, "feat", [story], _cfg(), epic_key=None)

        assert len(client.created) == 1
        assert "sdd:feat:STORY-001" in client.created[0]["labels"]
