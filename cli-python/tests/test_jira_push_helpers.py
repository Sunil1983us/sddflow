# Unit tests for the helper functions jira_push() was split into
# (_print_push_banner, _load_jira_push_config, _resolve_push_feature,
# _print_push_summary) -- each is now callable and assertable on its own,
# without driving the full Click command through CliRunner. jira_push()
# itself is still covered end-to-end by test_jira_push_content.py and
# test_jira_push_levels.py; these tests are the direct payoff of pulling
# the setup/validation/display concerns out of that one big function.
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sdd.commands.jira import (
    _load_jira_push_config,
    _print_push_banner,
    _print_push_summary,
    _resolve_push_feature,
)
from sdd.utils.integrations import JiraConfig
from sdd.utils.sdd_parser import Story, Task, UseCase


def _cfg(**kw):
    return JiraConfig(project_key="MYPROJ", **kw)


def _story(id="STORY-001"):
    return Story(
        id=id,
        title="Login",
        moscow="must-have",
        description="",
        acceptance_criteria=[],
        story_points=None,
        satisfies=[],
    )


def _task(id="TASK-001", story_id="STORY-001"):
    return Task(
        id=id,
        title="Endpoint",
        story_id=story_id,
        satisfies=[],
        estimate=None,
        description="",
        acceptance_criteria=[],
    )


class TestPrintPushBanner:
    def test_default_level_and_no_dry_run_shows_neither_suffix(self, capsys):
        _print_push_banner("all", dry_run=False)
        out = capsys.readouterr().out
        assert "SDD → Jira" in out
        assert "level:" not in out
        assert "dry run" not in out

    def test_non_default_level_is_shown(self, capsys):
        _print_push_banner("story", dry_run=False)
        out = capsys.readouterr().out
        assert "level: story" in out

    def test_dry_run_is_shown(self, capsys):
        _print_push_banner("all", dry_run=True)
        out = capsys.readouterr().out
        assert "dry run" in out


class TestLoadJiraPushConfig:
    def test_missing_integrations_yml_exits_with_message(
        self, tmp_path, monkeypatch, capsys
    ):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as excinfo:
            _load_jira_push_config()
        assert excinfo.value.code == 1
        assert "not found" in capsys.readouterr().out.lower()

    def test_integrations_yml_without_jira_section_exits_with_message(
        self, tmp_path, monkeypatch, capsys
    ):
        monkeypatch.chdir(tmp_path)
        specify_dir = tmp_path / ".specify"
        specify_dir.mkdir()
        (specify_dir / "integrations.yml").write_text(
            yaml.dump({"confluence": {"space_key": "ENG"}})
        )
        with pytest.raises(SystemExit) as excinfo:
            _load_jira_push_config()
        assert excinfo.value.code == 1
        assert "no jira:" in capsys.readouterr().out.lower()

    def test_valid_config_with_jira_section_returns_it(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        specify_dir = tmp_path / ".specify"
        specify_dir.mkdir()
        (specify_dir / "integrations.yml").write_text(
            yaml.dump(
                {
                    "profile": "work",
                    "jira": {"project_key": "PROJ"},
                }
            )
        )
        cfg = _load_jira_push_config()
        assert cfg.jira is not None
        assert cfg.jira.project_key == "PROJ"


class TestResolvePushFeature:
    def test_feature_flag_overrides_manifest(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".specify" / "features" / "checkout").mkdir(parents=True)
        specify_dir = tmp_path / ".specify"
        (specify_dir / "manifest.yml").write_text(
            yaml.dump({"project": {"name": "Payments", "feature": "login"}})
        )
        project_name, feature_name, features_dir = _resolve_push_feature("checkout")
        assert project_name == "Payments"
        assert feature_name == "checkout"
        assert features_dir == Path(".specify/features/checkout")

    def test_falls_back_to_manifest_feature_when_flag_omitted(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".specify" / "features" / "login").mkdir(parents=True)
        specify_dir = tmp_path / ".specify"
        (specify_dir / "manifest.yml").write_text(
            yaml.dump({"project": {"name": "Payments", "feature": "login"}})
        )
        _project_name, feature_name, _features_dir = _resolve_push_feature(None)
        assert feature_name == "login"

    def test_missing_feature_directory_exits_with_message(
        self, tmp_path, monkeypatch, capsys
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".specify").mkdir()
        with pytest.raises(SystemExit) as excinfo:
            _resolve_push_feature("never-created")
        assert excinfo.value.code == 1
        assert "not found" in capsys.readouterr().out.lower()

    def test_path_traversal_in_feature_name_is_rejected(
        self, tmp_path, monkeypatch, capsys
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".specify").mkdir()
        with pytest.raises(SystemExit) as excinfo:
            _resolve_push_feature("../../etc")
        assert excinfo.value.code == 1


class TestPrintPushSummary:
    def test_all_level_shows_stories_and_tasks_not_ucs_or_chg(self, capsys):
        _print_push_summary(
            "Payments",
            "checkout",
            "all",
            _cfg(),
            stories=[_story()],
            tasks=[_task()],
        )
        out = capsys.readouterr().out
        assert "Stories  :" in out and "1" in out
        assert "Tasks    :" in out
        assert "UCs" not in out
        assert "CHG" not in out

    def test_uc_draft_level_shows_ucs_only(self, capsys):
        _print_push_summary(
            "Payments",
            "checkout",
            "uc-draft",
            _cfg(),
            use_cases=[UseCase(id="UC-001", title="Login")],
            stories=[],
            tasks=[],
        )
        out = capsys.readouterr().out
        assert "UCs      :" in out
        assert "Stories  :" not in out
        assert "Tasks    :" not in out

    def test_chg_level_shows_chg_count_and_cr_id(self, capsys):
        _print_push_summary(
            "Payments",
            "checkout",
            "chg",
            _cfg(),
            stories=[],
            tasks=[],
            chg_tasks=[{"sdd_id": "CHG-001"}],
            cr="CR-042",
        )
        out = capsys.readouterr().out
        assert "CHG      :" in out
        assert "CR-042" in out

    def test_project_keys_override_shows_warning(self, capsys):
        _print_push_summary(
            "Payments",
            "checkout",
            "all",
            _cfg(project_keys={"story": "SUNT"}),
            stories=[],
            tasks=[],
        )
        out = capsys.readouterr().out
        assert "project_keys override" in out
        assert "can't link issues" in out

    def test_no_project_keys_override_shows_no_warning(self, capsys):
        _print_push_summary("Payments", "checkout", "all", _cfg(), stories=[], tasks=[])
        out = capsys.readouterr().out
        assert "override" not in out
