# Unit tests for the sdd upgrade migration chain.
from click.testing import CliRunner
import pytest
import yaml

from sdd.commands.upgrade import upgrade_command, MIGRATIONS
from sdd.utils.manifest import SDD_VERSION


@pytest.fixture()
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".specify").mkdir()
    return tmp_path


def _write_manifest(project, version):
    m = {"project": {"name": "Demo", "feature": "auth"}}
    if version is not None:
        m["sdd_version"] = version
    (project / ".specify" / "manifest.yml").write_text(yaml.dump(m))


def _manifest_version(project):
    return yaml.safe_load(
        (project / ".specify" / "manifest.yml").read_text()
    ).get("sdd_version")


def test_migration_table_is_a_connected_chain_ending_at_current():
    """Every 'from' must be reachable and the chain must end at SDD_VERSION."""
    version = None
    for m in MIGRATIONS:
        assert m["from"] == version, f"gap in chain before {m['to']}"
        version = m["to"]
    assert version == SDD_VERSION


def test_each_migration_stamps_its_own_to_version():
    for m in MIGRATIONS:
        result = m["migrate"]({"project": {}})
        assert result["sdd_version"] == m["to"]


def test_upgrade_from_2_0_0_reaches_current(project):
    _write_manifest(project, "2.0.0")
    result = CliRunner().invoke(upgrade_command)
    assert result.exit_code == 0
    assert _manifest_version(project) == SDD_VERSION


def test_upgrade_noop_when_current(project):
    _write_manifest(project, SDD_VERSION)
    result = CliRunner().invoke(upgrade_command)
    assert result.exit_code == 0
    assert "Already at" in result.output
    assert _manifest_version(project) == SDD_VERSION


def test_pre_versioning_chain_hints_to_rerun(project):
    _write_manifest(project, None)
    result = CliRunner().invoke(upgrade_command)
    assert result.exit_code == 0
    assert _manifest_version(project) == "2.0.0"
    assert "again" in result.output  # multi-step hint
    # second run completes the chain
    CliRunner().invoke(upgrade_command)
    assert _manifest_version(project) == SDD_VERSION


def test_missing_manifest_exits_nonzero(project):
    result = CliRunner().invoke(upgrade_command)
    assert result.exit_code == 1
