"""Tests for sdd.utils.project_type (classification logic) and the
`sdd project-type` CLI command (guided project_type migration for
sdd-universal projects)."""

from __future__ import annotations

import yaml
from click.testing import CliRunner

from sdd.commands.project_type import project_type_command
from sdd.utils.project_type import (
    PROJECT_TYPES,
    applicable_extended_docs,
    classify_migration,
    is_valid_project_type,
)


class TestApplicableExtendedDocs:
    def test_backend_service_has_none(self):
        assert applicable_extended_docs("backend-service") == frozenset()

    def test_frontend_spa_has_component_spec_and_ux_flow(self):
        assert applicable_extended_docs("frontend-spa") == frozenset(
            {"component-spec", "ux-flow"}
        )

    def test_mobile_has_screen_spec_and_ux_flow(self):
        assert applicable_extended_docs("mobile") == frozenset(
            {"screen-spec", "ux-flow"}
        )

    def test_unknown_type_is_empty(self):
        assert applicable_extended_docs("nonsense") == frozenset()

    def test_none_is_empty(self):
        assert applicable_extended_docs(None) == frozenset()


class TestIsValidProjectType:
    def test_every_canonical_type_is_valid(self):
        for t in PROJECT_TYPES:
            assert is_valid_project_type(t)

    def test_bogus_type_is_invalid(self):
        assert not is_valid_project_type("bogus-type")


class TestClassifyMigration:
    def test_backend_to_fullstack_is_additive_not_lossy(self):
        report = classify_migration("backend-service", "fullstack")
        assert report.added_docs == frozenset({"component-spec", "ux-flow"})
        assert report.dropped_docs == frozenset()
        assert not report.is_lossy

    def test_fullstack_to_backend_is_lossy(self):
        report = classify_migration("fullstack", "backend-service")
        assert report.dropped_docs == frozenset({"component-spec", "ux-flow"})
        assert report.is_lossy

    def test_frontend_spa_to_fullstack_is_neutral(self):
        # Same extended-doc set (component-spec, ux-flow) on both sides.
        report = classify_migration("frontend-spa", "fullstack")
        assert report.added_docs == frozenset()
        assert report.dropped_docs == frozenset()
        assert not report.is_lossy

    def test_mobile_to_fullstack_is_mixed(self):
        # mobile: {screen-spec, ux-flow} -> fullstack: {component-spec, ux-flow}
        report = classify_migration("mobile", "fullstack")
        assert report.added_docs == frozenset({"component-spec"})
        assert report.dropped_docs == frozenset({"screen-spec"})
        assert report.is_lossy

    def test_unset_from_type_treated_as_no_docs(self):
        report = classify_migration(None, "fullstack")
        assert report.from_type == "(unset)"
        assert report.added_docs == frozenset({"component-spec", "ux-flow"})
        assert not report.is_lossy

    def test_render_mentions_constitution_is_untouched(self):
        report = classify_migration("backend-service", "fullstack")
        assert "constitution.md" in report.render()


def _write_universal_manifest(project_type: str = "backend-service") -> dict:
    manifest = {
        "ai_tool": "claude-code",
        "pack": "sdd-universal",
        "plan_mode": "unified",
        "pr_rules": {"max_files_per_pr": 5, "max_lines_per_pr": 400},
        "project": {
            "context_file": "validation-service.md",
            "feature": "validation-service",
            "name": "Validation",
            "scope": "mvp",
        },
        "project_type": project_type,
        "reading_mode": "full",
        "sdd_version": "2.9.16",
        "testing_style": "tdd",
    }
    from pathlib import Path

    Path(".specify").mkdir(exist_ok=True)
    Path(".specify/manifest.yml").write_text(yaml.dump(manifest))
    return manifest


class TestProjectTypeShowCommand:
    def test_show_no_manifest(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(project_type_command, ["show"])
        assert result.exit_code == 2
        assert "No .specify/manifest.yml" in result.output

    def test_show_non_universal_pack(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from pathlib import Path

        Path(".specify").mkdir()
        Path(".specify/manifest.yml").write_text(
            yaml.dump({"pack": "sdd-backend-service", "project": {}})
        )
        result = CliRunner().invoke(project_type_command, ["show"])
        assert result.exit_code == 2
        assert "no project_type field" in result.output

    def test_show_prints_current_type(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_universal_manifest("backend-service")
        result = CliRunner().invoke(project_type_command, ["show"])
        assert result.exit_code == 0
        assert "backend-service" in result.output


class TestProjectTypeMigrateCommand:
    def test_dry_run_does_not_write_manifest(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_universal_manifest("backend-service")
        result = CliRunner().invoke(
            project_type_command, ["migrate", "--to", "fullstack"]
        )
        assert result.exit_code == 0
        assert "Dry run only" in result.output
        from sdd.utils.manifest import read_manifest

        assert read_manifest()["project_type"] == "backend-service"

    def test_invalid_target_type_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_universal_manifest("backend-service")
        result = CliRunner().invoke(
            project_type_command, ["migrate", "--to", "not-a-type"]
        )
        assert result.exit_code == 2
        assert "not a recognized project_type" in result.output

    def test_apply_safe_migration_writes_manifest(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_universal_manifest("backend-service")
        result = CliRunner().invoke(
            project_type_command, ["migrate", "--to", "fullstack", "--apply"]
        )
        assert result.exit_code == 0
        from sdd.utils.manifest import read_manifest

        assert read_manifest()["project_type"] == "fullstack"

    def test_apply_lossy_migration_without_force_refuses(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_universal_manifest("fullstack")
        result = CliRunner().invoke(
            project_type_command, ["migrate", "--to", "backend-service", "--apply"]
        )
        assert result.exit_code == 1
        assert "Refusing to apply" in result.output
        from sdd.utils.manifest import read_manifest

        assert read_manifest()["project_type"] == "fullstack"  # unchanged

    def test_apply_lossy_migration_with_force_writes(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_universal_manifest("fullstack")
        result = CliRunner().invoke(
            project_type_command,
            ["migrate", "--to", "backend-service", "--apply", "--force"],
        )
        assert result.exit_code == 0
        from sdd.utils.manifest import read_manifest

        assert read_manifest()["project_type"] == "backend-service"

    def test_migrate_to_same_type_is_a_noop(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_universal_manifest("backend-service")
        result = CliRunner().invoke(
            project_type_command,
            ["migrate", "--to", "backend-service", "--apply"],
        )
        assert result.exit_code == 0
        assert "nothing to migrate" in result.output

    def test_migrate_on_non_universal_pack_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from pathlib import Path

        Path(".specify").mkdir()
        Path(".specify/manifest.yml").write_text(
            yaml.dump({"pack": "sdd-backend-service", "project": {}})
        )
        result = CliRunner().invoke(
            project_type_command, ["migrate", "--to", "fullstack"]
        )
        assert result.exit_code == 2
        assert "no project_type field" in result.output
