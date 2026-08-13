"""Tests for `sdd doctor` (sdd/commands/doctor.py) -- CLI-level: manifest
handling, --pack override, exit codes, and the pack-identity-uncertainty
warning. Hashing/classification logic itself is covered directly in
test_managed_files.py; these tests exercise the command wrapper."""

from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

import sdd.utils.managed_files as managed_files_mod
from sdd.commands.doctor import doctor_command


def _write_manifest(root: Path, **fields) -> None:
    (root / ".specify").mkdir(exist_ok=True)
    manifest = {"project": {"name": "Test", "feature": "widget", "scope": "mvp"}}
    manifest.update(fields)
    (root / ".specify" / "manifest.yml").write_text(yaml.dump(manifest))


def _fake_pack(packs_dir: Path, name: str = "sdd-fake") -> Path:
    pack = packs_dir / name
    (pack / ".specify" / "templates").mkdir(parents=True)
    (pack / ".specify" / "templates" / "brd-template.md").write_text("brd v1\n")
    return pack


def test_missing_manifest_errors_clearly(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(doctor_command)
    assert result.exit_code == 1
    assert "manifest.yml not found" in result.output


def test_unknown_pack_override_errors(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    result = CliRunner().invoke(doctor_command, ["--pack", "sdd-nonexistent"])
    assert result.exit_code == 1
    assert "Unknown pack" in result.output


def test_clean_project_exits_zero(tmp_path, monkeypatch):
    packs_dir = tmp_path / "packs"
    _fake_pack(packs_dir)
    monkeypatch.setattr(managed_files_mod, "get_packs_dir", lambda: packs_dir)

    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    _write_manifest(project, pack="sdd-fake")
    (project / ".specify" / "templates").mkdir(parents=True, exist_ok=True)
    (project / ".specify" / "templates" / "brd-template.md").write_text("brd v1\n")

    result = CliRunner().invoke(doctor_command)
    assert result.exit_code == 0
    assert "up to date" in result.output.lower()


def test_dirty_project_exits_nonzero_and_lists_files(tmp_path, monkeypatch):
    packs_dir = tmp_path / "packs"
    _fake_pack(packs_dir)
    monkeypatch.setattr(managed_files_mod, "get_packs_dir", lambda: packs_dir)

    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    _write_manifest(project, pack="sdd-fake")
    # brd-template.md never scaffolded -> MISSING

    result = CliRunner().invoke(doctor_command)
    assert result.exit_code == 1
    assert "brd-template.md" in result.output
    assert "need attention" in result.output


def test_quiet_flag_omits_up_to_date_files(tmp_path, monkeypatch):
    packs_dir = tmp_path / "packs"
    pack = _fake_pack(packs_dir)
    (pack / ".github" / "prompts").mkdir(parents=True)
    (pack / ".github" / "prompts" / "specify.prompt.md").write_text("v1\n")
    monkeypatch.setattr(managed_files_mod, "get_packs_dir", lambda: packs_dir)

    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    _write_manifest(project, pack="sdd-fake")
    (project / ".specify" / "templates").mkdir(parents=True, exist_ok=True)
    (project / ".specify" / "templates" / "brd-template.md").write_text("brd v1\n")
    # specify.prompt.md never scaffolded -> MISSING, should still show

    result = CliRunner().invoke(doctor_command, ["--quiet"])
    assert result.exit_code == 1
    assert "brd-template.md" not in result.output  # up to date, suppressed
    assert "specify.prompt.md" in result.output  # dirty, still shown


def test_inferred_pack_shows_uncertainty_warning(tmp_path, monkeypatch):
    packs_dir = tmp_path / "packs"
    _fake_pack(packs_dir)
    monkeypatch.setattr(managed_files_mod, "get_packs_dir", lambda: packs_dir)
    # Register the fake pack as a real recognized project_type mapping so
    # _resolve_pack's inference path is exercised, not just its default.
    import sdd.commands.upgrade as upgrade_mod

    monkeypatch.setitem(upgrade_mod.TYPE_TO_PACK, "widget-type", "sdd-fake")

    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    _write_manifest(project, project_type="widget-type")
    (project / ".specify" / "templates").mkdir(parents=True, exist_ok=True)
    (project / ".specify" / "templates" / "brd-template.md").write_text("brd v1\n")

    result = CliRunner().invoke(doctor_command)
    assert "guess, not a certainty" in result.output
    assert "inferred from project_type" in result.output


def test_explicit_pack_field_shows_no_uncertainty_warning(tmp_path, monkeypatch):
    packs_dir = tmp_path / "packs"
    _fake_pack(packs_dir)
    monkeypatch.setattr(managed_files_mod, "get_packs_dir", lambda: packs_dir)

    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    _write_manifest(project, pack="sdd-fake")
    (project / ".specify" / "templates").mkdir(parents=True, exist_ok=True)
    (project / ".specify" / "templates" / "brd-template.md").write_text("brd v1\n")

    result = CliRunner().invoke(doctor_command)
    assert "guess, not a certainty" not in result.output
