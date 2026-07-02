import shutil
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
}

ALL_PACKS = list(PACK_DESCRIPTIONS.keys())
UNIVERSAL_PACK = "sdd-universal"


def get_packs_dir() -> Path:
    """
    Resolve the directory that contains the sdd-* pack folders.

    Search order:
    1. Bundled packs inside the installed package  (pip install sddkit)
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
        "  Installed via pip?  Try: pip install --force-reinstall sddkit\n"
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
