# Write-to-temp-then-rename, so a process killed mid-write never leaves a
# truncated file behind. Extracted from manifest.py's write_manifest(),
# which had this pattern first -- shared here so every other write site
# doesn't have to duplicate it (or skip it).
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def read_text_resilient(path: str | Path) -> tuple[str, bool]:
    """Read a text file, tolerating pre-3.7.1 cp1252 content on Windows.

    Every write in this codebase has produced real UTF-8 since v3.7.1 (see
    atomic_write_text() below), but a file written before that fix, on a
    system whose locale defaulted to something else -- cp1252 on most
    Windows installs -- still has whatever that locale wrote: most
    commonly a single-byte em-dash/curly-quote (e.g. 0x97) where UTF-8
    needs multiple bytes. Reported live: `sdd upgrade`/`sdd config test`
    crashing with UnicodeDecodeError on manifest.yml/integrations.yml/
    ~/.sdd/config.yml written before the fix.

    Tries UTF-8 first; falls back to cp1252 (which decodes every byte
    0-255 except 5 undefined code points, so it's a safe near-total
    fallback and the overwhelmingly likely culprit given our own
    write-side history). Returns (text, was_repaired) -- a caller that can
    safely rewrite the file should do so when was_repaired is True (write
    back this same `text`, not a re-serialized structure, so any hand-added
    comments/formatting survive byte-for-byte), so this only needs to
    happen once per file. Raises UnicodeDecodeError (the cp1252 failure)
    if neither encoding can decode it -- callers should catch this and
    raise their own domain-specific error with file-specific recovery
    instructions.
    """
    raw = Path(path).read_bytes()
    try:
        return raw.decode("utf-8"), False
    except UnicodeDecodeError:
        return raw.decode("cp1252"), True


def atomic_write_text(path: str | Path, content: str) -> None:
    """Write `content` to `path` atomically.

    Writes to a temp file in the *same directory* as `path` (required for
    os.replace() to be atomic on both POSIX and Windows) then renames it
    into place. A crash or kill mid-write leaves either the old file
    untouched or the new one complete -- never a partial write.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, target)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise
