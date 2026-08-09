"""Tests for `sdd feature list`/`sdd feature status` -- terminal windows
onto the same build_project_status()/build_feature_status() data the
dashboard renders, plus list_feature_names() (promoted from status.py's
private _list_feature_names)."""

from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from sdd.commands.feature import feature_command
from sdd.utils.status import list_feature_names


def _write_manifest(root: Path, feature: str = "validation-service") -> None:
    (root / ".specify").mkdir(exist_ok=True)
    (root / ".specify" / "manifest.yml").write_text(
        yaml.dump(
            {
                "project": {"name": "Validation", "feature": feature, "scope": "mvp"},
                "plan_mode": "unified",
            }
        )
    )


def _write_constitution(root: Path) -> None:
    (root / ".specify" / "memory").mkdir(parents=True, exist_ok=True)
    (root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\nPart 2: v1.0 (Finalized)\n"
    )


def _write_doc(
    root: Path, feature: str, name: str, header: str, body: str = ""
) -> Path:
    fd = root / ".specify" / "features" / feature
    fd.mkdir(parents=True, exist_ok=True)
    p = fd / f"{name}.md"
    p.write_text(
        f"# {name.upper()}\n> Version: 1.0 | {header} | Date: 2026-08-01 | Author: Maya\n\n{body}\n"
    )
    return p


class TestListFeatureNames:
    def test_no_features_dir_returns_empty(self, tmp_path):
        assert list_feature_names(tmp_path) == []

    def test_returns_sorted_folder_names(self, tmp_path):
        (tmp_path / ".specify" / "features" / "billing").mkdir(parents=True)
        (tmp_path / ".specify" / "features" / "auth").mkdir(parents=True)
        assert list_feature_names(tmp_path) == ["auth", "billing"]

    def test_ignores_non_directory_entries(self, tmp_path):
        features = tmp_path / ".specify" / "features"
        features.mkdir(parents=True)
        (features / "auth").mkdir()
        (features / "stray-file.txt").write_text("not a feature")
        assert list_feature_names(tmp_path) == ["auth"]


class TestFeatureListCommand:
    def test_no_features_yet(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        result = CliRunner().invoke(feature_command, ["list"])
        assert result.exit_code == 0
        assert "No features yet" in result.output

    def test_lists_every_feature_with_current_marker(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path, feature="validation-service")
        _write_constitution(tmp_path)
        _write_doc(tmp_path, "validation-service", "brd", "Status: Approved")
        _write_doc(tmp_path, "rule-management-ui", "brd", "Status: Draft")

        result = CliRunner().invoke(feature_command, ["list"])
        assert result.exit_code == 0, result.output
        assert "validation-service" in result.output
        assert "rule-management-ui" in result.output
        assert "(current)" in result.output
        # The (current) marker must land on the right feature, not just
        # appear somewhere in the output.
        for line in result.output.splitlines():
            if "validation-service" in line:
                assert "(current)" in line
            if "rule-management-ui" in line:
                assert "(current)" not in line


class TestFeatureStatusCommand:
    def test_no_feature_specified_and_none_in_manifest(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".specify").mkdir()
        (tmp_path / ".specify" / "manifest.yml").write_text(
            yaml.dump({"project": {"name": "Demo"}})
        )
        result = CliRunner().invoke(feature_command, ["status"])
        assert result.exit_code == 2
        assert "No feature specified" in result.output

    def test_unknown_feature_lists_known_ones(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_constitution(tmp_path)
        _write_doc(tmp_path, "validation-service", "brd", "Status: Draft")

        result = CliRunner().invoke(feature_command, ["status", "--feature", "bogus"])
        assert result.exit_code == 2
        assert "validation-service" in result.output

    def test_shows_pipeline_and_approvals(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_constitution(tmp_path)
        p = _write_doc(tmp_path, "validation-service", "brd", "Status: Approved")
        p.write_text(
            p.read_text() + "\n## Approvals\n"
            "| Role | Approver | Status | Date |\n"
            "|---|---|---|---|\n"
            "| Product Owner (accountable) | Sunil PO | Approved | 2026-08-01 |\n"
            "| Business Analyst | | Pending | |\n"
        )

        result = CliRunner().invoke(feature_command, ["status"])
        assert result.exit_code == 0, result.output
        assert "Pipeline" in result.output
        assert "Document Approvals" in result.output
        assert "Sunil PO" in result.output
        assert "Pending" in result.output
        assert "Next:" in result.output

    def test_works_with_no_jira_confluence_configured_at_all(
        self, tmp_path, monkeypatch
    ):
        """The whole point vs. `sdd review status`: no integrations.yml
        needed at all -- reads only the local .md files."""
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path)
        _write_constitution(tmp_path)
        _write_doc(tmp_path, "validation-service", "brd", "Status: Draft")
        assert not (tmp_path / ".specify" / "integrations.yml").exists()

        result = CliRunner().invoke(feature_command, ["status"])
        assert result.exit_code == 0, result.output

    def test_explicit_feature_flag_overrides_manifest(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path, feature="validation-service")
        _write_constitution(tmp_path)
        _write_doc(tmp_path, "validation-service", "brd", "Status: Draft")
        _write_doc(tmp_path, "rule-management-ui", "brd", "Status: Approved")

        result = CliRunner().invoke(
            feature_command, ["status", "--feature", "rule-management-ui"]
        )
        assert result.exit_code == 0, result.output
        assert "rule-management-ui" in result.output
