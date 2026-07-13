# Unit tests for sdd/utils/scaffold.py -- pack file copying, and
# sync_pack_prompts() specifically (re-copies .github/prompts/ and
# .claude/commands/ into an already-scaffolded project, since `sdd upgrade`
# alone never touches these files after the initial `sdd init`).
from pathlib import Path

import pytest

import sdd.utils.scaffold as scaffold_mod
from sdd.utils.scaffold import scaffold_pack, sync_pack_prompts


@pytest.fixture()
def fake_pack(tmp_path, monkeypatch):
    """A minimal fake pack tree with a prompts file, a commands file, and
    a template file outside the synced dirs -- isolated from the real
    packs/ directory so these tests don't drift with real pack content."""
    packs_dir = tmp_path / "packs"
    pack = packs_dir / "sdd-fake"
    (pack / ".github" / "prompts").mkdir(parents=True)
    (pack / ".claude" / "commands").mkdir(parents=True)
    (pack / ".specify" / "templates").mkdir(parents=True)

    (pack / ".github" / "prompts" / "specify.prompt.md").write_text("v1 specify prompt\n")
    (pack / ".claude" / "commands" / "specify.md").write_text("v1 specify command\n")
    (pack / ".specify" / "templates" / "brd-template.md").write_text("template content\n")

    monkeypatch.setattr(scaffold_mod, "get_packs_dir", lambda: packs_dir)
    monkeypatch.setattr(scaffold_mod, "ALL_PACKS", ["sdd-fake"])
    return pack


@pytest.fixture()
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_scaffold_pack_never_overwrites_existing_files(fake_pack, project):
    (project / ".github" / "prompts").mkdir(parents=True)
    (project / ".github" / "prompts" / "specify.prompt.md").write_text("locally customized\n")

    n = scaffold_pack("sdd-fake", dest=str(project))

    assert (project / ".github" / "prompts" / "specify.prompt.md").read_text() == "locally customized\n"
    assert (project / ".claude" / "commands" / "specify.md").read_text() == "v1 specify command\n"
    assert n == 2  # commands + template copied; prompt skipped (already existed)


def test_sync_prompts_adds_missing_files(fake_pack, project):
    result = sync_pack_prompts("sdd-fake", dest=str(project))
    assert result["added"] == [
        ".claude/commands/specify.md",
        ".github/prompts/specify.prompt.md",
    ]
    assert result["updated"] == []
    assert (project / ".github" / "prompts" / "specify.prompt.md").read_text() == "v1 specify prompt\n"


def test_sync_prompts_leaves_identical_files_alone(fake_pack, project):
    scaffold_pack("sdd-fake", dest=str(project))
    result = sync_pack_prompts("sdd-fake", dest=str(project))
    assert result["updated"] == []
    assert result["added"] == []
    assert sorted(result["unchanged"]) == [
        ".claude/commands/specify.md",
        ".github/prompts/specify.prompt.md",
    ]


def test_sync_prompts_overwrites_changed_files_and_backs_up_first(fake_pack, project):
    prompts_dir = project / ".github" / "prompts"
    prompts_dir.mkdir(parents=True)
    (prompts_dir / "specify.prompt.md").write_text("stale v0 content\n")

    result = sync_pack_prompts("sdd-fake", dest=str(project))

    assert result["updated"] == [".github/prompts/specify.prompt.md"]
    assert (prompts_dir / "specify.prompt.md").read_text() == "v1 specify prompt\n"
    assert result["backup_dir"] is not None
    backup_file = project / result["backup_dir"] / ".github" / "prompts" / "specify.prompt.md"
    assert backup_file.read_text() == "stale v0 content\n"


def test_sync_prompts_never_touches_files_outside_synced_dirs(fake_pack, project):
    templates_dir = project / ".specify" / "templates"
    templates_dir.mkdir(parents=True)
    (templates_dir / "brd-template.md").write_text("locally edited template\n")

    sync_pack_prompts("sdd-fake", dest=str(project))

    assert (templates_dir / "brd-template.md").read_text() == "locally edited template\n"


def test_sync_prompts_dry_run_does_not_write_anything(fake_pack, project):
    prompts_dir = project / ".github" / "prompts"
    prompts_dir.mkdir(parents=True)
    (prompts_dir / "specify.prompt.md").write_text("stale v0 content\n")

    result = sync_pack_prompts("sdd-fake", dest=str(project), dry_run=True)

    assert result["updated"] == [".github/prompts/specify.prompt.md"]
    assert (prompts_dir / "specify.prompt.md").read_text() == "stale v0 content\n"  # unchanged
    assert not (project / ".specify" / ".prompt-sync-backups").exists()
    assert not (project / ".claude").exists()  # the missing "added" file was never written either


def test_sync_prompts_unknown_pack_raises(fake_pack, project):
    with pytest.raises(RuntimeError, match="not found"):
        sync_pack_prompts("does-not-exist", dest=str(project))
