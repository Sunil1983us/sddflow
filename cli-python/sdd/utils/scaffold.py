import filecmp
import shutil
from datetime import datetime, timezone
from pathlib import Path

# Types that have a dedicated pack. Everything else → sdd-universal.
TYPE_TO_PACK: dict[str, str] = {
    "backend-service": "sdd-backend-service",
    "frontend-spa":    "sdd-frontend-spa",
    "fullstack":       "sdd-fullstack",
    "mobile":          "sdd-mobile",
}

PACK_DESCRIPTIONS: dict[str, str] = {
    "sdd-backend-service": "REST APIs, microservices, databases, messaging",
    "sdd-frontend-spa":    "React / Vue / Angular single-page applications",
    "sdd-fullstack":       "Frontend + backend in the same repository",
    "sdd-mobile":          "React Native or Flutter mobile apps",
    "sdd-universal":       "Any project type — auto-detects from your codebase",
    "sdd-micro":           "Tiny/personal projects — skip the full SDLC, just constitution + tasks + code",
}

ALL_PACKS = list(PACK_DESCRIPTIONS.keys())
UNIVERSAL_PACK = "sdd-universal"


def get_packs_dir() -> Path:
    """
    Resolve the directory that contains the sdd-* pack folders.

    Search order:
    1. Bundled packs inside the installed package  (pip install sddflow)
       → cli-python/sdd/packs/
    2. Repository root packs/ directory            (pip install -e . / dev)
       → <repo-root>/packs/
    """
    # 1. Bundled (installed package): sdd/packs/ sits next to sdd/utils/
    bundled = Path(__file__).parent.parent / "packs"
    if bundled.is_dir() and any(bundled.iterdir()):
        return bundled

    # 2. Dev / editable install: walk up from cli-python/sdd/utils/ to repo root
    repo_packs = Path(__file__).resolve().parent.parent.parent.parent / "packs"
    if repo_packs.is_dir() and any(repo_packs.iterdir()):
        return repo_packs

    raise RuntimeError(
        "SDD pack files not found.\n"
        "  Installed via pip?  Try: pip install --force-reinstall sddflow\n"
        "  Running from source? Ensure you cloned the full repository."
    )


def recommended_pack(project_type: str | None) -> str:
    """Return the recommended pack name for a detected project type."""
    if project_type and project_type in TYPE_TO_PACK:
        return TYPE_TO_PACK[project_type]
    return UNIVERSAL_PACK


def scaffold_pack(pack_name: str, dest: str = ".") -> int:
    """
    Copy pack files into dest directory. Existing files are never overwritten.
    Returns the number of files copied.
    """
    packs_dir = get_packs_dir()
    pack_src = packs_dir / pack_name

    if not pack_src.is_dir():
        raise RuntimeError(
            f"Pack '{pack_name}' not found in {packs_dir}.\n"
            f"Available packs: {', '.join(ALL_PACKS)}"
        )

    dest_path = Path(dest)
    count = 0

    for src_file in pack_src.rglob("*"):
        if not src_file.is_file():
            continue
        rel = src_file.relative_to(pack_src)
        dst_file = dest_path / rel
        if not dst_file.exists():
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            count += 1

    return count


# Directories synced by sync_pack_prompts() — the "Command Triplicity"
# locations from CLAUDE.md that carry the actual command/prompt behavior.
# Deliberately narrower than the full pack tree: templates, constitution,
# and other project-owned files under .specify/ are never touched here.
SYNC_DIRS: tuple[str, ...] = (".github/prompts", ".claude/commands")


def sync_pack_prompts(pack_name: str, dest: str = ".",
                       sync_dirs: tuple[str, ...] = SYNC_DIRS,
                       dry_run: bool = False) -> dict:
    """
    Re-copy a pack's prompt/command files into an already-scaffolded
    project, overwriting whatever's there. Unlike scaffold_pack() (which
    never overwrites), this exists specifically to pull in fixes made to
    prompt file *content* after the project was first initialized --
    `sdd upgrade` alone only ever patches manifest.yml's sdd_version, it
    never touches these files, so a fix to e.g. token-usage-log-step.md
    never reaches a project scaffolded before the fix without this.

    Every file that would change is backed up first, to
    .specify/.prompt-sync-backups/{timestamp}/{relative path}, so a
    project with hand-edited prompt files doesn't just lose those edits
    silently -- the backup is the recovery path, not a confirmation
    prompt, since this is meant to be safe to run non-interactively too.

    Returns {"updated": [...], "added": [...], "unchanged": [...],
    "backup_dir": str | None} -- relative paths, for the caller to report.
    """
    packs_dir = get_packs_dir()
    pack_src = packs_dir / pack_name
    if not pack_src.is_dir():
        raise RuntimeError(
            f"Pack '{pack_name}' not found in {packs_dir}.\n"
            f"Available packs: {', '.join(ALL_PACKS)}"
        )

    dest_path = Path(dest)
    updated: list[str] = []
    added: list[str] = []
    unchanged: list[str] = []
    backup_dir: Path | None = None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for sync_dir in sync_dirs:
        src_dir = pack_src / sync_dir
        if not src_dir.is_dir():
            continue
        for src_file in src_dir.rglob("*"):
            if not src_file.is_file():
                continue
            rel = src_file.relative_to(pack_src)
            dst_file = dest_path / rel

            if not dst_file.exists():
                if not dry_run:
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                added.append(str(rel))
                continue

            if filecmp.cmp(src_file, dst_file, shallow=False):
                unchanged.append(str(rel))
                continue

            if not dry_run:
                if backup_dir is None:
                    backup_dir = dest_path / ".specify" / ".prompt-sync-backups" / timestamp
                backup_file = backup_dir / rel
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst_file, backup_file)
                shutil.copy2(src_file, dst_file)
            updated.append(str(rel))

    return {
        "updated": sorted(updated),
        "added": sorted(added),
        "unchanged": sorted(unchanged),
        "backup_dir": str(backup_dir.relative_to(dest_path)) if backup_dir else None,
    }
