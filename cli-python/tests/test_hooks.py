"""Tests for `sdd hooks` -- the post-commit git hook that automates
per-commit `sdd token-log --command implement` calls, so real usage
logging can't be silently skipped mid a long /implement run regardless
of whether the AI agent remembers to call it itself (see CHANGELOG
v3.0.1 for the prompt-side half of this fix, and the live user report
that motivated this deterministic, code-level half)."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from sdd.commands.hooks import _MARKER, hooks_command


def _init_git_repo(root: Path) -> Path:
    hooks_dir = root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    return hooks_dir


def test_install_creates_hook_in_fresh_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_git_repo(tmp_path)
    runner = CliRunner()
    result = runner.invoke(hooks_command, ["install"])
    assert result.exit_code == 0, result.output
    target = tmp_path / ".git" / "hooks" / "post-commit"
    assert target.is_file()
    assert _MARKER in target.read_text()
    # Must be executable -- a non-executable post-commit hook is silently
    # never run by git at all, which would make this whole feature a no-op.
    assert target.stat().st_mode & 0o111


def test_install_outside_git_repo_fails_clearly(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(hooks_command, ["install"])
    assert result.exit_code == 1
    assert "not a git repository" in result.output.lower()


def test_install_is_idempotent_on_our_own_hook(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_git_repo(tmp_path)
    runner = CliRunner()
    first = runner.invoke(hooks_command, ["install"])
    second = runner.invoke(hooks_command, ["install"])
    assert first.exit_code == 0
    assert second.exit_code == 0, second.output


def test_install_refuses_to_clobber_a_foreign_hook_without_force(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hooks_dir = _init_git_repo(tmp_path)
    foreign = hooks_dir / "post-commit"
    foreign.write_text("#!/bin/sh\necho 'my own lint hook'\n")

    runner = CliRunner()
    result = runner.invoke(hooks_command, ["install"])
    assert result.exit_code == 2
    # The foreign hook must survive untouched.
    assert foreign.read_text() == "#!/bin/sh\necho 'my own lint hook'\n"


def test_install_force_overwrites_a_foreign_hook(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hooks_dir = _init_git_repo(tmp_path)
    foreign = hooks_dir / "post-commit"
    foreign.write_text("#!/bin/sh\necho 'my own lint hook'\n")

    runner = CliRunner()
    result = runner.invoke(hooks_command, ["install", "--force"])
    assert result.exit_code == 0, result.output
    assert _MARKER in foreign.read_text()


def test_status_reports_not_installed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_git_repo(tmp_path)
    runner = CliRunner()
    result = runner.invoke(hooks_command, ["status"])
    assert result.exit_code == 0
    assert "no post-commit hook installed" in result.output.lower()


def test_status_reports_installed_after_install(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_git_repo(tmp_path)
    runner = CliRunner()
    runner.invoke(hooks_command, ["install"])
    result = runner.invoke(hooks_command, ["status"])
    assert result.exit_code == 0
    assert "installed" in result.output.lower()
    assert "✓" in result.output


def test_status_flags_a_foreign_hook_distinctly(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hooks_dir = _init_git_repo(tmp_path)
    (hooks_dir / "post-commit").write_text("#!/bin/sh\necho foreign\n")
    runner = CliRunner()
    result = runner.invoke(hooks_command, ["status"])
    assert result.exit_code == 0
    normalized = " ".join(result.output.lower().split())
    assert "wasn't installed by sdd" in normalized


def test_status_outside_git_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(hooks_command, ["status"])
    assert result.exit_code == 0
    assert "not a git repository" in result.output.lower()


def test_uninstall_removes_our_hook(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hooks_dir = _init_git_repo(tmp_path)
    runner = CliRunner()
    runner.invoke(hooks_command, ["install"])
    assert (hooks_dir / "post-commit").exists()

    result = runner.invoke(hooks_command, ["uninstall"])
    assert result.exit_code == 0, result.output
    assert not (hooks_dir / "post-commit").exists()


def test_uninstall_refuses_a_foreign_hook(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hooks_dir = _init_git_repo(tmp_path)
    foreign = hooks_dir / "post-commit"
    foreign.write_text("#!/bin/sh\necho foreign\n")

    runner = CliRunner()
    result = runner.invoke(hooks_command, ["uninstall"])
    assert result.exit_code == 2
    assert foreign.exists()
    assert foreign.read_text() == "#!/bin/sh\necho foreign\n"


def test_uninstall_when_nothing_installed_is_a_quiet_noop(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_git_repo(tmp_path)
    runner = CliRunner()
    result = runner.invoke(hooks_command, ["uninstall"])
    assert result.exit_code == 0
    assert (
        "nothing to remove" in result.output.lower()
        or "no post-commit" in result.output.lower()
    )


def test_hook_script_always_exits_zero_and_never_uses_set_dash_e():
    """The installed script must never be able to fail the commit it's
    attached to -- no `set -e`, and the final `exit 0` is unconditional."""
    from sdd.commands.hooks import _HOOK_SCRIPT

    assert "set -e" not in _HOOK_SCRIPT
    assert _HOOK_SCRIPT.strip().endswith("exit 0")
