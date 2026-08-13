"""Tracks drift between a project's framework-managed files and the pack
content bundled with the currently installed `sddflow` CLI.

Background: `sdd upgrade` has only ever patched `manifest.yml`'s
`sdd_version` field -- it never touched the actual template/prompt/
command/instruction/setup-script files a project was scaffolded with, so
a project could report itself "upgraded" while every one of those files
still matched whatever version it was originally created at. This module
is the read side of closing that gap: it answers "what actually differs,
and do we know why" without changing anything -- see `sdd doctor`
(sdd/commands/doctor.py), the first, deliberately read-only piece of a
larger effort (a real `sdd upgrade` that can tell a safe pack-content
update apart from a project's own hand edits comes next).

Every SHA-256 hash here is of file *content*, not metadata -- line-ending
or mtime differences that don't change bytes read identically don't
count as drift.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sdd.utils.scaffold import get_packs_dir

# Directories (relative to a pack's root) whose files are framework-owned
# content, expected to be identical to the installed CLI's bundled pack
# unless a project has deliberately diverged. Mirrors this repo's own
# CLAUDE.md "Bump" bucket (cli-python/sdd/** aside, since that's CLI code,
# not project-scaffolded content) plus three directories the bump policy
# doesn't currently track but that packs do ship and that can equally go
# stale in a scaffolded project: .github/workflows, .cursor/rules,
# .vscode. Not every pack has every directory (e.g. sdd-micro has no
# .github/instructions or .github/workflows) -- missing ones are simply
# skipped, not an error.
MANAGED_DIRS: tuple[str, ...] = (
    ".specify/templates",
    ".claude/commands",
    ".github/prompts",
    ".github/instructions",
    ".github/workflows",
    ".cursor/rules",
    ".vscode",
)

# Individual files at a pack's root, outside any of the directories above.
MANAGED_FILES: tuple[str, ...] = (
    "setup.sh",
    "setup.ps1",
)

# Per-project record of which pack-content hash each managed file was
# last successfully synced to -- not written by anything yet (`sdd
# doctor` only reads it, if present); a future `sdd upgrade` rewrite is
# what will start writing it, at which point drift classification below
# gains its full four-way precision instead of falling back to "unknown".
BASELINE_PATH = Path(".specify") / ".managed-files.json"

STATUS_UP_TO_DATE = "up_to_date"
STATUS_NEEDS_UPDATE = "needs_update"
STATUS_USER_MODIFIED = "user_modified"
STATUS_DIFFERS_UNKNOWN = "differs_unknown_reason"
STATUS_MISSING = "missing"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_inventory(pack_name: str) -> dict[str, str]:
    """{relative_path: sha256} for every managed file in the pack bundled
    with the *currently installed* CLI -- i.e. what an upgrade to this
    CLI's version would produce. Raises RuntimeError if the pack itself
    isn't found (mirrors get_packs_dir()'s own error shape)."""
    packs_dir = get_packs_dir()
    pack_root = packs_dir / pack_name
    if not pack_root.is_dir():
        raise RuntimeError(f"Pack '{pack_name}' not found in {packs_dir}.")

    inventory: dict[str, str] = {}
    for rel_dir in MANAGED_DIRS:
        src_dir = pack_root / rel_dir
        if not src_dir.is_dir():
            continue
        for f in sorted(src_dir.rglob("*")):
            if f.is_file():
                rel = f.relative_to(pack_root).as_posix()
                inventory[rel] = _sha256_file(f)
    for rel_file in MANAGED_FILES:
        f = pack_root / rel_file
        if f.is_file():
            inventory[rel_file] = _sha256_file(f)
    return inventory


def project_inventory(root: Path, relative_paths) -> dict[str, str | None]:
    """{relative_path: sha256 or None} for the given paths as they
    actually exist (or don't) under `root` right now."""
    result: dict[str, str | None] = {}
    for rel in relative_paths:
        p = root / rel
        result[rel] = _sha256_file(p) if p.is_file() else None
    return result


def load_baseline(root: Path) -> dict[str, dict]:
    """{relative_path: {"hash": ..., "pack_version": ...}} last recorded
    for this project, or {} if the file is absent/unreadable (e.g. a
    project that predates this mechanism entirely -- not an error, just
    means classification below can't distinguish NEEDS_UPDATE from
    USER_MODIFIED for any file with no baseline entry)."""
    path = root / BASELINE_PATH
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def classify_file(
    canonical_hash: str,
    local_hash: str | None,
    baseline_entry: dict | None,
) -> str:
    """One of the STATUS_* constants above for a single managed file.

    Deliberately conservative: without a recorded baseline hash for a
    file that differs from canonical, there's no way to tell "the pack
    changed this since the project was scaffolded" apart from "the
    project's own edit" -- STATUS_DIFFERS_UNKNOWN says exactly that,
    rather than guessing either way."""
    if local_hash is None:
        return STATUS_MISSING
    if local_hash == canonical_hash:
        return STATUS_UP_TO_DATE
    if baseline_entry is None:
        return STATUS_DIFFERS_UNKNOWN
    if local_hash == baseline_entry.get("hash"):
        return STATUS_NEEDS_UPDATE
    return STATUS_USER_MODIFIED


def check_managed_files(root: Path, pack_name: str) -> dict[str, dict]:
    """The full report: {relative_path: {"status": STATUS_*,
    "canonical_hash": ..., "local_hash": ... or None}} for every managed
    file the currently installed CLI's pack defines. Read-only -- makes
    no filesystem writes of its own."""
    canonical = canonical_inventory(pack_name)
    local = project_inventory(root, canonical.keys())
    baseline = load_baseline(root)

    report: dict[str, dict] = {}
    for rel, chash in canonical.items():
        lhash = local[rel]
        status = classify_file(chash, lhash, baseline.get(rel))
        report[rel] = {
            "status": status,
            "canonical_hash": chash,
            "local_hash": lhash,
        }
    return report
