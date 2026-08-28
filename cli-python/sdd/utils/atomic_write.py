# Write-to-temp-then-rename, so a process killed mid-write never leaves a
# truncated file behind. Extracted from manifest.py's write_manifest(),
# which had this pattern first -- shared here so every other write site
# doesn't have to duplicate it (or skip it).
from __future__ import annotations

import os
import tempfile
from pathlib import Path


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
