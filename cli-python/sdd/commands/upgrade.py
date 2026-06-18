from pathlib import Path
import click
from rich.console import Console

from sdd.utils.manifest import read_manifest, patch_manifest, MANIFEST_PATH, SDD_VERSION

console = Console()

# Version migration table — extend when releasing a new pack version.
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
            "Python CLI added alongside Node.js CLI (pip install sdd-init)",
        ],
        "migrate": lambda m: {**m, "sdd_version": SDD_VERSION},
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

    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("  [bold green]Upgrade complete![/bold green]")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()
