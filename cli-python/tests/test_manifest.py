# Unit tests for sdd/utils/manifest.py — atomic writes and corrupt-file
# handling. manifest.yml is the one config file every command depends on to
# know which project/feature/scope it's operating on, so unlike the
# dashboard's best-effort auxiliary caches (.local-approvals.yml, etc.),
# a corrupt manifest should fail loudly rather than silently degrade.
from pathlib import Path

import pytest

from sdd.utils.manifest import (
    ManifestError,
    patch_manifest,
    read_manifest,
    write_manifest,
)


def test_read_manifest_returns_none_when_missing(tmp_path):
    assert read_manifest(str(tmp_path / "manifest.yml")) is None


def test_read_manifest_returns_dict_for_valid_yaml(tmp_path):
    p = tmp_path / "manifest.yml"
    p.write_text("project:\n  name: Demo\n")
    assert read_manifest(str(p)) == {"project": {"name": "Demo"}}


def test_read_manifest_raises_manifest_error_on_corrupt_yaml(tmp_path):
    p = tmp_path / "manifest.yml"
    # Unbalanced flow-mapping brace -- a real YAML syntax error, not just
    # unexpected structure.
    p.write_text("project: {name: Demo\n  scope: pilot\n")
    with pytest.raises(ManifestError) as excinfo:
        read_manifest(str(p))
    assert str(p) in str(excinfo.value)


def test_read_manifest_error_message_mentions_recovery_options(tmp_path):
    p = tmp_path / "manifest.yml"
    p.write_text("project: {broken\n")
    with pytest.raises(ManifestError) as excinfo:
        read_manifest(str(p))
    msg = str(excinfo.value).lower()
    assert (
        "sdd init" in msg or "git" in msg
    )  # points at a way out, not just "it's broken"


def test_read_manifest_recovers_from_cp1252_em_dash_and_self_heals(tmp_path):
    """Regression: a manifest.yml written by an sdd version older than
    3.7.1, on a Windows box whose system locale is cp1252, encodes an
    em-dash as the single byte 0x97 instead of UTF-8's three bytes (E2 80
    94). Reported live: `sdd upgrade` crashed with UnicodeDecodeError on
    exactly this byte. read_manifest() must recover the content via the
    cp1252 fallback AND rewrite the file as real UTF-8 so every other
    command reading the same file afterward doesn't hit the same crash."""
    p = tmp_path / "manifest.yml"
    # Raw byte 0x97 -- cp1252's single-byte em-dash, where UTF-8 needs
    # three bytes (E2 80 94). A bytes literal, not a str.encode(), so this
    # is exactly the on-disk byte an old sdd version would have written.
    raw = b"# SDD Manifest \x97 schema\nproject:\n  name: Demo\n"
    p.write_bytes(raw)

    manifest = read_manifest(str(p))

    assert manifest == {"project": {"name": "Demo"}}
    # Self-healed: the file on disk is now valid UTF-8 with the real em-dash.
    healed = p.read_text(encoding="utf-8")
    assert "—" in healed  # em-dash
    assert b"\x97" not in p.read_bytes()


def test_read_manifest_raises_clear_error_when_neither_utf8_nor_cp1252_valid(tmp_path):
    p = tmp_path / "manifest.yml"
    # 0x81 is undefined in cp1252 and is not valid standalone UTF-8 either.
    p.write_bytes(b"project:\n  name: \x81Demo\n")
    with pytest.raises(ManifestError) as excinfo:
        read_manifest(str(p))
    msg = str(excinfo.value).lower()
    assert "utf-8" in msg and "1252" in msg
    assert "sdd init" in msg or "git" in msg


def test_write_manifest_creates_parent_directories(tmp_path):
    p = tmp_path / "nested" / "dir" / "manifest.yml"
    write_manifest({"project": {"name": "Demo"}}, str(p))
    assert p.exists()
    assert read_manifest(str(p)) == {"project": {"name": "Demo"}}


def test_write_manifest_leaves_no_temp_file_behind(tmp_path):
    p = tmp_path / "manifest.yml"
    write_manifest({"project": {"name": "Demo"}}, str(p))
    leftovers = [f for f in tmp_path.iterdir() if f.name != "manifest.yml"]
    assert leftovers == []


def test_write_manifest_round_trips_unicode(tmp_path):
    p = tmp_path / "manifest.yml"
    write_manifest({"project": {"name": "café-service"}}, str(p))
    assert read_manifest(str(p))["project"]["name"] == "café-service"


def test_write_manifest_is_atomic_via_temp_file_and_replace(tmp_path, monkeypatch):
    """Verifies the actual mechanism, not just the end result: write_manifest
    must never call write_text() directly on the target path (the old,
    non-atomic behavior) -- it must write to a temp file in the same
    directory and os.replace() it into place. The mechanism itself now
    lives in sdd.utils.atomic_write (see tests/test_atomic_write.py for
    the full failure-cleanup coverage); this just confirms write_manifest
    actually routes through it end to end."""
    import sdd.utils.atomic_write as atomic_write_mod

    p = tmp_path / "manifest.yml"
    p.write_text("project:\n  name: Original\n")  # pre-existing file

    replace_calls = []
    original_replace = atomic_write_mod.os.replace

    def spy_replace(src, dst):
        # At the moment of replace, the destination must still hold the
        # OLD content and the temp source must hold the NEW content --
        # proving the write happened out-of-place, not in-place.
        assert Path(dst).read_text() == "project:\n  name: Original\n"
        assert "Updated" in Path(src).read_text()
        replace_calls.append((src, dst))
        return original_replace(src, dst)

    monkeypatch.setattr(atomic_write_mod.os, "replace", spy_replace)
    write_manifest({"project": {"name": "Updated"}}, str(p))

    assert len(replace_calls) == 1
    assert read_manifest(str(p))["project"]["name"] == "Updated"


def test_patch_manifest_still_raises_filenotfound_when_missing(tmp_path):
    p = tmp_path / "manifest.yml"
    with pytest.raises(FileNotFoundError):
        patch_manifest({"project": {"name": "x"}}, str(p))


def test_patch_manifest_deep_merges_and_persists(tmp_path):
    p = tmp_path / "manifest.yml"
    write_manifest({"project": {"name": "Demo", "scope": "pilot"}}, str(p))
    result = patch_manifest({"project": {"scope": "mvp"}}, str(p))
    assert result["project"] == {"name": "Demo", "scope": "mvp"}
    assert read_manifest(str(p))["project"] == {"name": "Demo", "scope": "mvp"}
