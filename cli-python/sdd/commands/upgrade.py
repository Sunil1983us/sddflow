from pathlib import Path
import click
from rich.console import Console

from sdd.utils.manifest import read_manifest, patch_manifest, MANIFEST_PATH, SDD_VERSION

console = Console()

# Version migration table — extend when releasing a new pack version.
# Each migrate() stamps its own "to" version so chained upgrades stay truthful.
MIGRATIONS = [
    {
        "from":        None,       # None = pre-versioning (no sdd_version field)
        "to":          "2.0.0",
        "description": "Initial versioned release",
        "notes": [
            "Added sdd_version field to manifest.yml for upgrade tracking",
            "setup.sh/setup.ps1 rewritten — eliminates injection bugs",
            "Input validation: project/feature names with \" are rejected early",
            "Detection order fix: mobile (react-native) now checked before fullstack",
            "Python CLI added alongside Node.js CLI (pip install sddflow)",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.0.0"},
    },
    {
        "from":        "2.0.0",
        "to":          "2.7.0",
        "description": "Content release — no manifest schema changes",
        "notes": [
            "/change command: type-aware change requests at any SDLC stage",
            "/jira-push: progressive Jira export (Epic/Story/Task/CHG)",
            "Review gates: three modes (chat / local / jira) — Jira now optional",
            "sdd review approve --local also updates the doc's Confluence page",
            "setup.sh/setup.ps1 safe in non-interactive runs (CI, piped input)",
            "Re-copy the pack (or run sdd init over it) to pick up new prompt files",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.0"},
    },
    {
        "from":        "2.7.0",
        "to":          "2.7.1",
        "description": "Content release — no manifest schema changes",
        "notes": [
            "/create-context: Endpoints and NFRs now get a proposed "
            "scope-appropriate starting default, marked "
            "(SUGGESTED DEFAULT — edit or confirm), instead of always "
            "falling back to [MISSING — ask user]",
            "Re-copy the pack (or run sdd init over it) to pick up the "
            "updated .github/prompts/create-context.prompt.md",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.1"},
    },
    {
        "from":        "2.7.1",
        "to":          "2.7.3",
        "description": "Version scheme unified — one number instead of two",
        "notes": [
            "sdd_version no longer tracks a separate content/schema "
            "counter — it now always matches the installed sddflow "
            "package version (sdd --version), so this file and the CLI "
            "never show two different numbers again",
            "No framework content changed in this step beyond the "
            "version scheme itself",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.3"},
    },
    {
        "from":        "2.7.3",
        "to":          "2.7.4",
        "description": "Content release — no manifest schema changes",
        "notes": [
            "/change: when a CR fundamentally broadens or narrows what a "
            "feature IS (not just a detail change) — e.g. a fixed "
            "pain.001→pacs.008 converter generalized into a generic ISO "
            "20022 parser — the agent now recommends renaming the "
            "feature slug to match, and will perform the rename "
            "(directory, manifest.yml, context file) if you approve",
            "changeset-template.md: added a 'Feature renamed' row to §1 "
            "Change Description",
            "Re-copy the pack (or run sdd init over it) to pick up the "
            "updated .github/prompts/change.prompt.md and "
            "changeset-template.md",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.4"},
    },
    {
        "from":        "2.7.4",
        "to":          "2.7.5",
        "description": "Security fix — no manifest schema changes",
        "notes": [
            "sdd confluence / sdd cr / sdd jira now validate the feature "
            "name against path traversal before touching disk, matching "
            "sdd pr / sdd review, which already did this — previously "
            "a feature name containing '../' sequences (e.g. from a "
            "manifest.yml value not everyone on the project reviewed "
            "carefully) could read or write files outside "
            "'.specify/features/', including pushing arbitrary local "
            "file contents to Confluence/Jira",
            "Also fixed a bypass in the underlying containment check "
            "itself: a feature name resolving to a sibling directory "
            "sharing a string prefix with the base directory (e.g. "
            "'features-legacy' next to 'features') incorrectly passed "
            "validation — it now correctly requires the resolved path "
            "to be inside the base directory, not just prefix-matching",
            "No action needed unless you use --feature or "
            "project.feature values with '../' in them, which was never "
            "valid usage",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.5"},
    },
    {
        "from":        "2.7.5",
        "to":          "2.7.6",
        "description": "Content release — new .specify/service/ directory",
        "notes": [
            "data-model.md, security-design.md, and the API design section "
            "of design.md are now living, service-level documents instead "
            "of being regenerated per feature — they live at "
            "'.specify/service/{doc}.md' and get extended/amended by every "
            "feature after the first one that needs them, instead of each "
            "feature getting its own independent (and eventually "
            "contradictory) copy",
            "docs/runbook/local-setup.md, docs/openapi.yaml, and "
            "docker-compose.yml/k8s manifests now have explicit "
            "check-before-regenerate guidance for the same reason",
            "If you already have per-feature data-model.md/security-design.md "
            "files from before this release, they are NOT automatically "
            "moved or merged — the first time you run /specify-doc "
            "data-model (or security) again, it creates a fresh "
            "'.specify/service/' copy. You'll want to manually reconcile "
            "any existing per-feature versions into that one file yourself",
            "Re-copy the pack (or run sdd init over it) to pick up the "
            "updated .github/prompts/specify-doc.prompt.md and "
            "plan-design.prompt.md",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.6"},
    },
]


@click.command()
def upgrade_command():
    """Migrate manifest.yml to the current pack version."""
    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print(f"  [bold cyan]SDD Framework[/bold cyan] — upgrade")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()

    if not Path(MANIFEST_PATH).exists():
        console.print(f"[red]✗  {MANIFEST_PATH} not found — run from the pack root directory.[/red]")
        raise SystemExit(1)

    manifest = read_manifest()
    current_version = manifest.get("sdd_version") if manifest else None

    if current_version == SDD_VERSION:
        console.print(f"  [green]✓  Already at v{SDD_VERSION} — nothing to do.[/green]")
        console.print()
        return

    console.print(f"  Current version : [yellow]{current_version or 'pre-versioning (v1.x)'}[/yellow]")
    console.print(f"  Target version  : [green]{SDD_VERSION}[/green]")
    console.print()

    pending = [
        m for m in MIGRATIONS
        if (current_version is None and m["from"] is None)
        or m["from"] == current_version
    ]

    if not pending:
        console.print("[yellow]  No migration path found. See CHANGELOG.md for manual steps.[/yellow]")
        console.print()
        return

    for migration in pending:
        console.print(f"  [bold]Migrating → v{migration['to']}: {migration['description']}[/bold]")
        for note in migration["notes"]:
            console.print(f"    [dim]•[/dim] {note}")
        console.print()

        updated = migration["migrate"](read_manifest())
        patch_manifest({"sdd_version": updated["sdd_version"]})
        console.print(f"  [green]✓[/green]  {MANIFEST_PATH} updated to v{migration['to']}")
        console.print()

    final_version = (read_manifest() or {}).get("sdd_version")
    if final_version != SDD_VERSION:
        console.print(
            f"  [yellow]Now at v{final_version} — run [cyan]sdd upgrade[/cyan] again "
            f"to continue to v{SDD_VERSION}.[/yellow]"
        )
        console.print()

    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("  [bold green]Upgrade complete![/bold green]")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()
