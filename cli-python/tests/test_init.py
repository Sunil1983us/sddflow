# Unit tests for `sdd init` (sdd/commands/init.py). Interactive prompts are
# mocked at the questionary function level (not via CliRunner stdin) --
# questionary's prompt_toolkit UI needs a real TTY-like input source that
# CliRunner's plain stdin feeding doesn't provide. Same pattern as
# test_config_and_integrations.py's TestConfigInitCommand.
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from sdd.commands.init import init_command


class _Answer:
    """Stand-in for questionary's Question object -- .ask() returns a
    canned value instead of driving a real prompt_toolkit UI."""

    def __init__(self, value):
        self._value = value

    def ask(self):
        return self._value


def _write_manifest(tmp_path: Path, extra: dict | None = None) -> Path:
    manifest_dir = tmp_path / ".specify"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "project": {"name": "old", "feature": "old-feature", "scope": "pilot"},
        "project_type": "backend-service",
        "pr_rules": {"max_lines_per_pr": 400, "max_files_per_pr": 5},
    }
    if extra:
        data.update(extra)
    path = manifest_dir / "manifest.yml"
    path.write_text(yaml.dump(data))
    return path


@pytest.fixture()
def runner():
    return CliRunner()


class TestFillMode:
    """manifest.yml already exists -- scaffold step is skipped entirely."""

    def test_all_cli_flags_supplied_only_ai_tool_prompted(
        self, runner, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        manifest_path = _write_manifest(tmp_path)

        with patch("questionary.select", return_value=_Answer("claude-code")):
            result = runner.invoke(
                init_command,
                [
                    "-p",
                    "payments",
                    "-f",
                    "checkout",
                    "-s",
                    "mvp",
                    "-t",
                    "backend-service",
                    "--plan-mode",
                    "unified",
                    "--reading-mode",
                    "auto",
                ],
            )

        assert result.exit_code == 0, result.output

        saved = yaml.safe_load(manifest_path.read_text())
        assert saved["project"]["name"] == "payments"
        assert saved["project"]["feature"] == "checkout"
        assert saved["project"]["scope"] == "mvp"
        assert saved["project_type"] == "backend-service"
        assert saved["ai_tool"] == "claude-code"
        assert saved["plan_mode"] == "unified"
        assert saved["reading_mode"] == "auto"
        assert saved["sdd_version"]

        assert (tmp_path / ".specify" / "contexts" / "checkout.md").exists()
        assert (tmp_path / ".specify" / "features" / "checkout").is_dir()

    @pytest.mark.parametrize(
        "alias,canonical",
        [("lean", "pilot"), ("standard", "mvp"), ("regulated", "full")],
    )
    def test_scope_alias_resolves_to_canonical_name_in_manifest(
        self, runner, tmp_path, monkeypatch, alias, canonical
    ):
        # manifest.yml's own schema only ever stores pilot/mvp/full -- the
        # alias is a friendlier --scope spelling, resolved before anything
        # is written, never persisted as-is.
        monkeypatch.chdir(tmp_path)
        manifest_path = _write_manifest(tmp_path)

        with patch("questionary.select", return_value=_Answer("claude-code")):
            result = runner.invoke(
                init_command,
                [
                    "-p",
                    "payments",
                    "-f",
                    "checkout",
                    "-s",
                    alias,
                    "-t",
                    "backend-service",
                    "--plan-mode",
                    "unified",
                    "--reading-mode",
                    "auto",
                ],
            )

        assert result.exit_code == 0, result.output
        saved = yaml.safe_load(manifest_path.read_text())
        assert saved["project"]["scope"] == canonical

    def test_invalid_scope_value_is_rejected(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)

        result = runner.invoke(
            init_command,
            [
                "-p",
                "payments",
                "-f",
                "checkout",
                "-s",
                "not-a-real-scope",
                "-t",
                "backend-service",
                "--plan-mode",
                "unified",
                "--reading-mode",
                "auto",
            ],
        )

        assert result.exit_code != 0
        assert "not-a-real-scope" in result.output

    def test_context_file_not_overwritten_if_it_already_exists(
        self, runner, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        context_path = tmp_path / ".specify" / "contexts" / "checkout.md"
        context_path.parent.mkdir(parents=True, exist_ok=True)
        context_path.write_text("# hand-written context, do not clobber\n")

        with patch("questionary.select", return_value=_Answer("claude-code")):
            result = runner.invoke(
                init_command,
                [
                    "-p",
                    "payments",
                    "-f",
                    "checkout",
                    "-s",
                    "mvp",
                    "-t",
                    "backend-service",
                    "--plan-mode",
                    "unified",
                    "--reading-mode",
                    "auto",
                ],
            )

        assert result.exit_code == 0, result.output
        assert context_path.read_text() == "# hand-written context, do not clobber\n"
        assert "already exists" in result.output

    def test_micro_manifest_skips_scope_and_type_prompts(
        self, runner, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        manifest_dir = tmp_path / ".specify"
        manifest_dir.mkdir(parents=True)
        # sdd-micro's manifest template has neither project_type nor
        # project.scope -- that absence is how init_command detects it.
        (manifest_dir / "manifest.yml").write_text(
            yaml.dump(
                {
                    "project": {"name": "old", "feature": "old-feature"},
                }
            )
        )

        with patch("questionary.select", return_value=_Answer("claude-code")):
            result = runner.invoke(init_command, ["-p", "notes-app", "-f", "capture"])

        assert result.exit_code == 0, result.output
        saved = yaml.safe_load((manifest_dir / "manifest.yml").read_text())
        assert saved["project"]["name"] == "notes-app"
        assert "scope" not in saved["project"]
        assert "project_type" not in saved
        assert "plan_mode" not in saved
        assert "reading_mode" not in saved

    def test_invalid_project_name_raises(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)

        with patch("questionary.select", return_value=_Answer("claude-code")):
            result = runner.invoke(
                init_command,
                [
                    "-p",
                    'bad"name',
                    "-f",
                    "checkout",
                    "-s",
                    "mvp",
                    "-t",
                    "backend-service",
                ],
            )

        assert result.exit_code != 0


class TestPlanAndReadingModePrompts:
    """`sdd init` previously never asked about plan_mode/reading_mode at
    all -- both silently stayed at whatever the pack's shipped
    manifest.yml template default was ("unified"/"auto"), even though
    setup.sh (a separate scaffolding entry point) has asked both
    interactively since v2.7.92. A user pointed this gap out directly
    after noticing `sdd init` never asked. Call order in fill mode with
    scope supplied via flag: plan_mode -> reading_mode -> ai_tool."""

    def test_interactive_selection_written_to_manifest(
        self, runner, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        manifest_path = _write_manifest(tmp_path)

        with patch(
            "questionary.select",
            side_effect=[
                _Answer("separate"),
                _Answer("full"),
                _Answer("claude-code"),
            ],
        ):
            result = runner.invoke(
                init_command,
                [
                    "-p",
                    "payments",
                    "-f",
                    "checkout",
                    "-s",
                    "mvp",
                    "-t",
                    "backend-service",
                ],
            )

        assert result.exit_code == 0, result.output
        saved = yaml.safe_load(manifest_path.read_text())
        assert saved["plan_mode"] == "separate"
        assert saved["reading_mode"] == "full"
        assert "Plan    : separate" in result.output
        assert "Reading : full" in result.output

    def test_cli_flags_skip_both_prompts(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        manifest_path = _write_manifest(tmp_path)

        with patch("questionary.select", side_effect=[_Answer("claude-code")]):
            result = runner.invoke(
                init_command,
                [
                    "-p",
                    "payments",
                    "-f",
                    "checkout",
                    "-s",
                    "mvp",
                    "-t",
                    "backend-service",
                    "--plan-mode",
                    "separate",
                    "--reading-mode",
                    "summary",
                ],
            )

        assert result.exit_code == 0, result.output
        saved = yaml.safe_load(manifest_path.read_text())
        assert saved["plan_mode"] == "separate"
        assert saved["reading_mode"] == "summary"

    def test_micro_manifest_never_prompts_for_either(
        self, runner, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        manifest_dir = tmp_path / ".specify"
        manifest_dir.mkdir(parents=True)
        (manifest_dir / "manifest.yml").write_text(
            yaml.dump(
                {
                    "project": {"name": "old", "feature": "old-feature"},
                }
            )
        )

        # Only one canned answer (ai_tool) -- a plan_mode/reading_mode
        # prompt would raise StopIteration and fail this test.
        with patch("questionary.select", side_effect=[_Answer("claude-code")]):
            result = runner.invoke(init_command, ["-p", "notes-app", "-f", "capture"])

        assert result.exit_code == 0, result.output


class TestScaffoldMode:
    """No manifest.yml yet -- init_command copies a pack in first."""

    def test_scaffolds_recommended_pack_and_fills_manifest(
        self, runner, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)

        def _fake_scaffold_pack(pack_name, dest="."):
            manifest_dir = Path(dest) / ".specify"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            (manifest_dir / "manifest.yml").write_text(
                yaml.dump(
                    {
                        "project": {"name": "", "feature": ""},
                        "project_type": "",
                        "pr_rules": {"max_lines_per_pr": 400, "max_files_per_pr": 5},
                    }
                )
            )
            return 42

        with (
            patch(
                "sdd.commands.init.detect_project_type", return_value="backend-service"
            ),
            patch(
                "sdd.commands.init.scaffold_pack", side_effect=_fake_scaffold_pack
            ) as scaffold,
            patch(
                "questionary.select",
                side_effect=[
                    _Answer("sdd-backend-service"),
                    _Answer("claude-code"),
                ],
            ),
            patch("questionary.confirm", return_value=_Answer(True)),
        ):
            result = runner.invoke(
                init_command,
                [
                    "-p",
                    "payments",
                    "-f",
                    "checkout",
                    "-s",
                    "pilot",
                    "--plan-mode",
                    "unified",
                    "--reading-mode",
                    "auto",
                ],
            )

        assert result.exit_code == 0, result.output
        scaffold.assert_called_once()
        assert scaffold.call_args[0][0] == "sdd-backend-service"

        saved = yaml.safe_load((tmp_path / ".specify" / "manifest.yml").read_text())
        assert saved["pack"] == "sdd-backend-service"
        assert saved["project"]["name"] == "payments"
        assert saved["project_type"] == "backend-service"

    def test_dedicated_pack_choice_skips_redundant_type_prompt(
        self, runner, tmp_path, monkeypatch
    ):
        """Regression: choosing a type-dedicated pack (e.g. sdd-backend-service)
        must not re-detect or re-ask project type afterward -- the pack choice
        already answers it. Detection here returns None (not detected, as in
        the user's original repro) and questionary.select only has 2 canned
        answers (pack choice, ai_tool) -- a third .ask() call for project type
        would raise StopIteration and fail the test."""
        monkeypatch.chdir(tmp_path)

        def _fake_scaffold_pack(pack_name, dest="."):
            manifest_dir = Path(dest) / ".specify"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            (manifest_dir / "manifest.yml").write_text(
                yaml.dump(
                    {
                        "project": {"name": "", "feature": ""},
                        "project_type": "",
                        "pr_rules": {"max_lines_per_pr": 400, "max_files_per_pr": 5},
                    }
                )
            )
            return 42

        with (
            patch("sdd.commands.init.detect_project_type", return_value=None),
            patch("sdd.commands.init.scaffold_pack", side_effect=_fake_scaffold_pack),
            patch(
                "questionary.select",
                side_effect=[
                    _Answer("__all__"),
                    _Answer("sdd-backend-service"),
                    _Answer("claude-code"),
                ],
            ),
        ):
            result = runner.invoke(
                init_command,
                [
                    "-p",
                    "payments",
                    "-f",
                    "checkout",
                    "-s",
                    "pilot",
                    "--plan-mode",
                    "unified",
                    "--reading-mode",
                    "auto",
                ],
            )

        assert result.exit_code == 0, result.output
        saved = yaml.safe_load((tmp_path / ".specify" / "manifest.yml").read_text())
        assert saved["project_type"] == "backend-service"
        assert "from sdd-backend-service" in result.output

    def test_scaffold_cancelled_exits_nonzero(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        with (
            patch("sdd.commands.init.detect_project_type", return_value=None),
            patch("questionary.select", return_value=_Answer(None)),
        ):
            result = runner.invoke(init_command, ["-p", "payments", "-f", "checkout"])

        assert result.exit_code != 0
        assert not (tmp_path / ".specify" / "manifest.yml").exists()
