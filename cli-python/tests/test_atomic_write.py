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


def test_writes_real_utf8_bytes_regardless_of_locale_default(tmp_path):
    """Belt-and-suspenders correctness check alongside the real
    regression guard, tests/test_utf8_encoding_everywhere.py's static
    scan. atomic_write_text() used to open its temp file via
    `os.fdopen(fd, "w")` with no `encoding=` -- which falls back to
    locale.getpreferredencoding(False), cp1252 on many Windows setups,
    not UTF-8. A user hit exactly this: an em-dash ("—") in a
    /create-context-generated context.md came out as "â€”" (mojibake --
    each UTF-8 byte reinterpreted as a separate cp1252 character) once
    pushed to Confluence.

    This can't actually reproduce that failure in a CI/dev environment
    whose own locale is already UTF-8 (most Linux containers) --
    os.fdopen(fd, "w") with no encoding= still happens to write UTF-8
    bytes here regardless of the missing argument. It's the static AST
    scan, not this test, that fails when `encoding=` is missing,
    independent of the runner's own locale. This test still earns its
    place as a correctness check: it reads the raw bytes off disk and
    decodes them as UTF-8 explicitly (rather than trusting
    Path.read_text()'s own implicit default, which -- see
    test_round_trips_unicode above -- would silently match whatever
    atomic_write_text() implicitly wrote with and hide a mismatch)."""
    p = tmp_path / "file.txt"
    atomic_write_text(p, "Status: Draft — review Group A and Group B")
    raw = p.read_bytes()
    assert raw.decode("utf-8") == "Status: Draft — review Group A and Group B"
    # The exact bytes an em-dash (U+2014) encodes to in UTF-8 -- if this
    # were written as cp1252, "—" would either raise (cp1252 has no
    # U+2014 mapping... it does, at 0x97, so it'd silently write the
    # wrong single byte) rather than these three UTF-8 bytes.
    assert "\xe2\x80\x94".encode("latin-1") in raw


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
