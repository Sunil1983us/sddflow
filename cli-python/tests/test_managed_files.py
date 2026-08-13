# Unit tests for sdd/utils/managed_files.py -- the inventory/hashing/
# classification logic behind `sdd doctor` (sdd/commands/doctor.py).
# Isolated from the real packs/ directory (a fake pack tree, same pattern
# as test_scaffold.py's fake_pack fixture) so these tests don't drift
# with real pack content, and stay fast/deterministic.

import json

import pytest

import sdd.utils.managed_files as managed_files_mod
from sdd.utils.managed_files import (
    STATUS_DIFFERS_UNKNOWN,
    STATUS_MISSING,
    STATUS_NEEDS_UPDATE,
    STATUS_UP_TO_DATE,
    STATUS_USER_MODIFIED,
    apply_managed_files,
    canonical_inventory,
    check_managed_files,
    classify_file,
    load_baseline,
    project_inventory,
    write_baseline,
)


@pytest.fixture()
def fake_pack(tmp_path, monkeypatch):
    packs_dir = tmp_path / "packs"
    pack = packs_dir / "sdd-fake"
    (pack / ".specify" / "templates").mkdir(parents=True)
    (pack / ".github" / "prompts").mkdir(parents=True)
    (pack / ".claude" / "commands").mkdir(parents=True)
    # A directory NOT in MANAGED_DIRS -- must never show up in the
    # inventory, even though it sits right next to managed ones.
    (pack / ".specify" / "memory").mkdir(parents=True)

    (pack / ".specify" / "templates" / "brd-template.md").write_text("brd v1\n")
    (pack / ".github" / "prompts" / "specify.prompt.md").write_text("specify v1\n")
    (pack / ".claude" / "commands" / "specify.md").write_text("cmd v1\n")
    (pack / "setup.sh").write_text("#!/bin/sh\necho v1\n")
    (pack / ".specify" / "memory" / "constitution.md").write_text(
        "should never be tracked\n"
    )

    monkeypatch.setattr(managed_files_mod, "get_packs_dir", lambda: packs_dir)
    return pack


@pytest.fixture()
def project(tmp_path):
    return tmp_path / "project"


class TestCanonicalInventory:
    def test_only_managed_dirs_and_files_are_included(self, fake_pack):
        inv = canonical_inventory("sdd-fake")
        assert set(inv.keys()) == {
            ".specify/templates/brd-template.md",
            ".github/prompts/specify.prompt.md",
            ".claude/commands/specify.md",
            "setup.sh",
        }
        assert ".specify/memory/constitution.md" not in inv

    def test_hash_is_content_based(self, fake_pack):
        inv = canonical_inventory("sdd-fake")
        import hashlib

        expected = hashlib.sha256(b"brd v1\n").hexdigest()
        assert inv[".specify/templates/brd-template.md"] == expected

    def test_unknown_pack_raises(self, fake_pack):
        with pytest.raises(RuntimeError, match="not found"):
            canonical_inventory("sdd-does-not-exist")

    def test_missing_managed_dir_is_skipped_not_an_error(self, tmp_path, monkeypatch):
        # A pack with none of the managed dirs (e.g. sdd-micro lacks
        # .github/instructions and .github/workflows) shouldn't error --
        # just produces a smaller inventory.
        packs_dir = tmp_path / "packs"
        pack = packs_dir / "sdd-bare"
        pack.mkdir(parents=True)
        monkeypatch.setattr(managed_files_mod, "get_packs_dir", lambda: packs_dir)
        assert canonical_inventory("sdd-bare") == {}


class TestProjectInventory:
    def test_existing_and_missing_files(self, project):
        project.mkdir(parents=True)
        (project / "a.md").write_text("hello\n")
        result = project_inventory(project, ["a.md", "b.md"])
        assert result["b.md"] is None
        import hashlib

        assert result["a.md"] == hashlib.sha256(b"hello\n").hexdigest()


class TestLoadBaseline:
    def test_missing_file_returns_empty_dict(self, project):
        project.mkdir(parents=True)
        assert load_baseline(project) == {}

    def test_malformed_json_returns_empty_dict_not_raise(self, project):
        (project / ".specify").mkdir(parents=True)
        (project / ".specify" / ".managed-files.json").write_text("{not json")
        assert load_baseline(project) == {}

    def test_non_dict_json_returns_empty_dict(self, project):
        (project / ".specify").mkdir(parents=True)
        (project / ".specify" / ".managed-files.json").write_text("[1, 2, 3]")
        assert load_baseline(project) == {}

    def test_valid_baseline_loads(self, project):
        (project / ".specify").mkdir(parents=True)
        data = {"a.md": {"hash": "abc123", "pack_version": "3.1.1"}}
        (project / ".specify" / ".managed-files.json").write_text(json.dumps(data))
        assert load_baseline(project) == data


class TestClassifyFile:
    def test_missing_file(self):
        assert classify_file("canon", None, None) == STATUS_MISSING

    def test_matches_canonical_is_up_to_date_even_with_stale_baseline(self):
        # local == canonical wins outright, regardless of what baseline
        # says -- a file could match canonical for reasons unrelated to
        # the baseline (e.g. the user happened to hand-edit it back to
        # the exact same content) and that's still "up to date" by any
        # reasonable definition.
        assert (
            classify_file("hash-c", "hash-c", {"hash": "hash-stale"})
            == STATUS_UP_TO_DATE
        )

    def test_no_baseline_and_differs_is_unknown_reason(self):
        assert classify_file("hash-c", "hash-local", None) == STATUS_DIFFERS_UNKNOWN

    def test_local_matches_baseline_but_not_canonical_is_needs_update(self):
        # The exact case a real `sdd upgrade` should auto-apply: the user
        # never touched the file (it still matches what they were last
        # given), but the pack's canonical content has since moved on.
        assert (
            classify_file("hash-canonical-new", "hash-old", {"hash": "hash-old"})
            == STATUS_NEEDS_UPDATE
        )

    def test_local_matches_neither_is_user_modified(self):
        assert (
            classify_file("hash-canonical", "hash-local-edit", {"hash": "hash-old"})
            == STATUS_USER_MODIFIED
        )


class TestCheckManagedFiles:
    def test_full_report_end_to_end(self, fake_pack, project):
        project.mkdir(parents=True)
        # brd-template.md: untouched, matches canonical -> up to date
        (project / ".specify" / "templates").mkdir(parents=True)
        (project / ".specify" / "templates" / "brd-template.md").write_text("brd v1\n")
        # specify.prompt.md: hand-edited, no baseline recorded
        (project / ".github" / "prompts").mkdir(parents=True)
        (project / ".github" / "prompts" / "specify.prompt.md").write_text(
            "hand-edited\n"
        )
        # specify.md (command): never scaffolded
        # setup.sh: never scaffolded

        report = check_managed_files(project, "sdd-fake")

        assert (
            report[".specify/templates/brd-template.md"]["status"] == STATUS_UP_TO_DATE
        )
        assert (
            report[".github/prompts/specify.prompt.md"]["status"]
            == STATUS_DIFFERS_UNKNOWN
        )
        assert report[".claude/commands/specify.md"]["status"] == STATUS_MISSING
        assert report["setup.sh"]["status"] == STATUS_MISSING

    def test_report_respects_recorded_baseline(self, fake_pack, project):
        project.mkdir(parents=True)
        (project / ".specify" / "templates").mkdir(parents=True)
        # Local file matches neither canonical nor an old baseline that
        # doesn't exist for it -- but DOES match a recorded baseline that
        # differs from canonical -> NEEDS_UPDATE, not USER_MODIFIED.
        (project / ".specify" / "templates" / "brd-template.md").write_text(
            "brd v0 (old baseline)\n"
        )
        (project / ".specify" / ".managed-files.json").write_text(
            json.dumps(
                {
                    ".specify/templates/brd-template.md": {
                        "hash": __import__("hashlib")
                        .sha256(b"brd v0 (old baseline)\n")
                        .hexdigest(),
                        "pack_version": "3.0.0",
                    }
                }
            )
        )

        report = check_managed_files(project, "sdd-fake")
        assert (
            report[".specify/templates/brd-template.md"]["status"]
            == STATUS_NEEDS_UPDATE
        )


class TestWriteBaseline:
    def test_writes_new_baseline(self, project):
        project.mkdir(parents=True)
        write_baseline(project, {"a.md": {"hash": "abc", "pack_version": "1.0.0"}})
        assert load_baseline(project) == {
            "a.md": {"hash": "abc", "pack_version": "1.0.0"}
        }

    def test_merges_with_existing_entries_not_replaces(self, project):
        project.mkdir(parents=True)
        write_baseline(project, {"a.md": {"hash": "abc", "pack_version": "1.0.0"}})
        write_baseline(project, {"b.md": {"hash": "def", "pack_version": "1.0.0"}})
        assert load_baseline(project) == {
            "a.md": {"hash": "abc", "pack_version": "1.0.0"},
            "b.md": {"hash": "def", "pack_version": "1.0.0"},
        }

    def test_overwrites_only_the_given_keys(self, project):
        project.mkdir(parents=True)
        write_baseline(project, {"a.md": {"hash": "old", "pack_version": "1.0.0"}})
        write_baseline(project, {"a.md": {"hash": "new", "pack_version": "1.1.0"}})
        assert load_baseline(project) == {
            "a.md": {"hash": "new", "pack_version": "1.1.0"}
        }


class TestApplyManagedFiles:
    def test_missing_file_is_added_no_backup(self, fake_pack, project):
        project.mkdir(parents=True)
        result = apply_managed_files(project, "sdd-fake", pack_version="9.9.9")
        assert "setup.sh" in result["added"]
        assert result["backup_dir"] is None
        assert (project / "setup.sh").read_text() == "#!/bin/sh\necho v1\n"
        # Baseline recorded for the newly-added file
        baseline = load_baseline(project)
        assert baseline["setup.sh"]["pack_version"] == "9.9.9"

    def test_needs_update_is_applied_and_backed_up(self, fake_pack, project):
        project.mkdir(parents=True)
        (project / ".specify" / "templates").mkdir(parents=True)
        (project / ".specify" / "templates" / "brd-template.md").write_text(
            "brd v0 (old baseline)\n"
        )
        write_baseline(
            project,
            {
                ".specify/templates/brd-template.md": {
                    "hash": __import__("hashlib")
                    .sha256(b"brd v0 (old baseline)\n")
                    .hexdigest(),
                    "pack_version": "1.0.0",
                }
            },
        )

        result = apply_managed_files(project, "sdd-fake", pack_version="9.9.9")

        assert ".specify/templates/brd-template.md" in result["updated"]
        assert result["backup_dir"] is not None
        assert (
            project / ".specify" / "templates" / "brd-template.md"
        ).read_text() == "brd v1\n"
        backup_file = (
            project
            / result["backup_dir"]
            / ".specify"
            / "templates"
            / "brd-template.md"
        )
        assert backup_file.read_text() == "brd v0 (old baseline)\n"

    def test_user_modified_is_left_alone_without_force(self, fake_pack, project):
        project.mkdir(parents=True)
        (project / ".github" / "prompts").mkdir(parents=True)
        (project / ".github" / "prompts" / "specify.prompt.md").write_text(
            "hand-edited, no baseline\n"
        )

        result = apply_managed_files(project, "sdd-fake", pack_version="9.9.9")

        assert ".github/prompts/specify.prompt.md" in result["skipped_conflicts"]
        assert (
            project / ".github" / "prompts" / "specify.prompt.md"
        ).read_text() == "hand-edited, no baseline\n"
        # Conflict left alone -> no baseline entry recorded for it
        assert ".github/prompts/specify.prompt.md" not in load_baseline(project)

    def test_user_modified_is_overwritten_and_backed_up_with_force(
        self, fake_pack, project
    ):
        project.mkdir(parents=True)
        (project / ".github" / "prompts").mkdir(parents=True)
        (project / ".github" / "prompts" / "specify.prompt.md").write_text(
            "hand-edited, no baseline\n"
        )

        result = apply_managed_files(
            project, "sdd-fake", pack_version="9.9.9", force=True
        )

        assert ".github/prompts/specify.prompt.md" in result["updated"]
        assert result["skipped_conflicts"] == []
        assert (
            project / ".github" / "prompts" / "specify.prompt.md"
        ).read_text() == "specify v1\n"
        backup_file = (
            project / result["backup_dir"] / ".github" / "prompts" / "specify.prompt.md"
        )
        assert backup_file.read_text() == "hand-edited, no baseline\n"

    def test_up_to_date_file_gets_baseline_recorded_too(self, fake_pack, project):
        # A file that already matches canonical (no baseline yet) should
        # still get a baseline entry written -- so a *future* pack update
        # can tell NEEDS_UPDATE apart from USER_MODIFIED for it.
        project.mkdir(parents=True)
        (project / ".specify" / "templates").mkdir(parents=True)
        (project / ".specify" / "templates" / "brd-template.md").write_text("brd v1\n")

        result = apply_managed_files(project, "sdd-fake", pack_version="9.9.9")

        assert ".specify/templates/brd-template.md" in result["unchanged"]
        baseline = load_baseline(project)
        assert baseline[".specify/templates/brd-template.md"]["pack_version"] == "9.9.9"

    def test_dry_run_changes_nothing_on_disk_or_baseline(self, fake_pack, project):
        project.mkdir(parents=True)
        result = apply_managed_files(
            project, "sdd-fake", pack_version="9.9.9", dry_run=True
        )
        assert "setup.sh" in result["added"]
        assert not (project / "setup.sh").exists()
        assert load_baseline(project) == {}

    def test_unknown_pack_raises(self, fake_pack, project):
        project.mkdir(parents=True)
        with pytest.raises(RuntimeError, match="not found"):
            apply_managed_files(project, "sdd-does-not-exist", pack_version="9.9.9")
