# Unit tests for sdd/utils/atomic_write.py -- the shared write-to-temp-
# then-rename helper used by manifest.py and review.py (and any future
# write site that needs the same guarantee: a process killed mid-write
# never leaves a truncated file behind).
from pathlib import Path

import pytest

from sdd.utils.atomic_write import atomic_write_text


def test_creates_parent_directories(tmp_path):
    p = tmp_path / "nested" / "dir" / "file.txt"
    atomic_write_text(p, "hello")
    assert p.read_text() == "hello"


def test_leaves_no_temp_file_behind(tmp_path):
    p = tmp_path / "file.txt"
    atomic_write_text(p, "hello")
    leftovers = [f for f in tmp_path.iterdir() if f.name != "file.txt"]
    assert leftovers == []


def test_round_trips_unicode(tmp_path):
    p = tmp_path / "file.txt"
    atomic_write_text(p, "café-service")
    assert p.read_text() == "café-service"


def test_accepts_str_path(tmp_path):
    p = tmp_path / "file.txt"
    atomic_write_text(str(p), "hello")
    assert p.read_text() == "hello"


def test_is_atomic_via_temp_file_and_replace(tmp_path, monkeypatch):
    """Verifies the actual mechanism, not just the end result: this must
    never call write_text() directly on the target path (the old,
    non-atomic behavior) -- it must write to a temp file in the same
    directory and os.replace() it into place."""
    import sdd.utils.atomic_write as atomic_write_mod

    p = tmp_path / "file.txt"
    p.write_text("Original")  # pre-existing file

    replace_calls = []
    original_replace = atomic_write_mod.os.replace

    def spy_replace(src, dst):
        # At the moment of replace, the destination must still hold the
        # OLD content and the temp source must hold the NEW content --
        # proving the write happened out-of-place, not in-place.
        assert Path(dst).read_text() == "Original"
        assert Path(src).read_text() == "Updated"
        replace_calls.append((src, dst))
        return original_replace(src, dst)

    monkeypatch.setattr(atomic_write_mod.os, "replace", spy_replace)
    atomic_write_text(p, "Updated")

    assert len(replace_calls) == 1
    assert p.read_text() == "Updated"


def test_cleans_up_temp_file_on_failure(tmp_path, monkeypatch):
    import sdd.utils.atomic_write as atomic_write_mod

    p = tmp_path / "file.txt"

    def boom(*a, **kw):
        raise OSError("disk full (simulated)")

    monkeypatch.setattr(atomic_write_mod.os, "replace", boom)
    with pytest.raises(OSError):
        atomic_write_text(p, "hello")

    leftovers = list(tmp_path.iterdir())
    assert leftovers == [], (
        f"temp file(s) left behind after a failed write: {leftovers}"
    )
