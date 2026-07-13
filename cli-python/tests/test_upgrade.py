# Unit tests for the sdd upgrade migration chain.
from click.testing import CliRunner
import pytest
import yaml

import sdd.commands.upgrade as upgrade_mod
from sdd.commands.upgrade import upgrade_command, MIGRATIONS, _resolve_pack
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
    # Each invocation applies only the migration matching the current
    # version, so a long chain needs repeated invocations to converge —
    # loop rather than hardcode a count that breaks every time a new
    # migration entry is appended.
    for _ in range(len(MIGRATIONS)):
        result = CliRunner().invoke(upgrade_command)
        assert result.exit_code == 0
        if _manifest_version(project) == SDD_VERSION:
            break
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
    # subsequent runs complete the chain
    for _ in range(len(MIGRATIONS)):
        if _manifest_version(project) == SDD_VERSION:
            break
        CliRunner().invoke(upgrade_command)
    assert _manifest_version(project) == SDD_VERSION


def test_missing_manifest_exits_nonzero(project):
    result = CliRunner().invoke(upgrade_command)
    assert result.exit_code == 1


# ── --sync-prompts (re-copying prompt/command files sdd upgrade alone
# never touches) ─────────────────────────────────────────────────────────

def test_resolve_pack_prefers_explicit_override():
    pack, source = _resolve_pack({"project_type": "mobile"}, "sdd-universal")
    assert pack == "sdd-universal"
    assert source == "--pack flag"


def test_resolve_pack_rejects_unknown_override():
    with pytest.raises(ValueError, match="Unknown pack"):
        _resolve_pack({}, "not-a-real-pack")


def test_resolve_pack_prefers_stored_manifest_field():
    pack, source = _resolve_pack({"pack": "sdd-fullstack", "project_type": "mobile"}, None)
    assert pack == "sdd-fullstack"
    assert "manifest.yml" in source


def test_resolve_pack_infers_micro_from_manifest_shape():
    pack, source = _resolve_pack({"project": {"name": "x"}}, None)
    assert pack == "sdd-micro"
    assert "sdd-micro shape" in source


def test_resolve_pack_infers_from_project_type():
    pack, source = _resolve_pack({"project_type": "mobile", "project": {"scope": "pilot"}}, None)
    assert pack == "sdd-mobile"
    assert "inferred" in source


def test_resolve_pack_defaults_to_universal_when_type_unrecognized():
    pack, source = _resolve_pack({"project_type": "cli", "project": {"scope": "pilot"}}, None)
    assert pack == "sdd-universal"
    assert "defaulting" in source


def _fake_sync_result(updated=None, added=None, unchanged=None, backup_dir=None):
    return {"updated": updated or [], "added": added or [], "unchanged": unchanged or [],
            "backup_dir": backup_dir}


def test_sync_prompts_shows_preview_and_applies_on_confirm(project, monkeypatch):
    _write_manifest(project, SDD_VERSION)
    calls = []

    def fake_sync(pack_name, dry_run=False, **_):
        calls.append((pack_name, dry_run))
        if dry_run:
            return _fake_sync_result(updated=["a.md"], added=["b.md"], unchanged=["c.md"])
        return _fake_sync_result(updated=["a.md"], added=["b.md"], unchanged=["c.md"],
                                  backup_dir=".specify/.prompt-sync-backups/20260101T000000Z")

    monkeypatch.setattr(upgrade_mod, "sync_pack_prompts", fake_sync)

    result = CliRunner().invoke(upgrade_command, ["--sync-prompts", "--pack", "sdd-backend-service"],
                                 input="y\n")
    assert result.exit_code == 0
    assert calls == [
        ("sdd-backend-service", True),
        ("sdd-backend-service", False),
    ]
    assert "1 updated, 1 added, 1 unchanged" in result.output
    assert "Backups of overwritten files" in result.output


def test_sync_prompts_cancelled_does_not_apply(project, monkeypatch):
    _write_manifest(project, SDD_VERSION)
    calls = []

    def fake_sync(pack_name, dry_run=False, **_):
        calls.append(dry_run)
        return _fake_sync_result(updated=["a.md"])

    monkeypatch.setattr(upgrade_mod, "sync_pack_prompts", fake_sync)

    result = CliRunner().invoke(upgrade_command, ["--sync-prompts", "--pack", "sdd-backend-service"],
                                 input="n\n")
    assert result.exit_code == 0
    assert calls == [True]  # only the dry-run preview, never the real apply
    assert "Cancelled" in result.output


def test_sync_prompts_yes_flag_skips_confirmation(project, monkeypatch):
    _write_manifest(project, SDD_VERSION)
    monkeypatch.setattr(upgrade_mod, "sync_pack_prompts",
                         lambda pack_name, dry_run=False, **_: _fake_sync_result(added=["b.md"]))

    result = CliRunner().invoke(upgrade_command,
                                 ["--sync-prompts", "--pack", "sdd-backend-service", "--yes"])
    assert result.exit_code == 0
    assert "Proceed?" not in result.output
    assert "0 updated, 1 added" in result.output


def test_sync_prompts_already_up_to_date_skips_confirmation(project, monkeypatch):
    _write_manifest(project, SDD_VERSION)
    monkeypatch.setattr(upgrade_mod, "sync_pack_prompts",
                         lambda pack_name, dry_run=False, **_: _fake_sync_result(unchanged=["a.md"]))

    result = CliRunner().invoke(upgrade_command, ["--sync-prompts", "--pack", "sdd-backend-service"])
    assert result.exit_code == 0
    assert "already up to date" in result.output
    assert "Proceed?" not in result.output


def test_sync_prompts_runs_even_when_manifest_already_current(project, monkeypatch):
    """--sync-prompts must not be swallowed by the early-return 'nothing to
    do' path that plain `sdd upgrade` takes when already at SDD_VERSION."""
    _write_manifest(project, SDD_VERSION)
    monkeypatch.setattr(upgrade_mod, "sync_pack_prompts",
                         lambda pack_name, dry_run=False, **_: _fake_sync_result(added=["b.md"]))

    result = CliRunner().invoke(upgrade_command,
                                 ["--sync-prompts", "--pack", "sdd-backend-service", "--yes"])
    assert result.exit_code == 0
    assert "Already at" in result.output
    assert "0 updated, 1 added" in result.output


def test_sync_prompts_unknown_pack_reports_error_without_crashing(project, monkeypatch):
    _write_manifest(project, SDD_VERSION)
    result = CliRunner().invoke(upgrade_command, ["--sync-prompts", "--pack", "not-a-real-pack"])
    assert result.exit_code == 0
    assert "Unknown pack" in result.output


def test_sync_prompts_without_pack_flag_infers_from_manifest(project, monkeypatch):
    m = {"project": {"name": "Demo", "feature": "auth", "scope": "pilot"},
         "project_type": "frontend-spa", "sdd_version": SDD_VERSION}
    (project / ".specify" / "manifest.yml").write_text(yaml.dump(m))
    seen = {}

    def fake_sync(pack_name, dry_run=False, **_):
        seen["pack"] = pack_name
        return _fake_sync_result()

    monkeypatch.setattr(upgrade_mod, "sync_pack_prompts", fake_sync)
    result = CliRunner().invoke(upgrade_command, ["--sync-prompts"])
    assert result.exit_code == 0
    assert seen["pack"] == "sdd-frontend-spa"
    assert "inferred from project_type" in result.output
