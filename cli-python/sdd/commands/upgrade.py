from pathlib import Path
import click
from rich.console import Console

from sdd.utils.manifest import read_manifest, patch_manifest, MANIFEST_PATH, SDD_VERSION

console = Console()

# Version migration table — extend when releasing a new pack version.
MIGRATIONS = [
    {
        "from":        None,
        "to":          "2.0.0",
        "description": "Initial versioned release",
        "notes": [
            "Added sdd_version field to manifest.yml for upgrade tracking",
            "setup.sh/setup.ps1 rewritten — eliminates injection bugs",
            "Input validation: project/feature names with \" are rejected early",
            "Detection order fix: mobile (react-native) now checked before fullstack",
            "Python CLI added alongside Node.js CLI (pip install sdd-init)",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.0.0"},
    },
    {
        "from":        "2.0.0",
        "to":          "2.1.0",
        "description": "Document-level review gates + PR automation",
        "notes": [
            "sdd review submit/check/apply/status commands added",
            "sdd pr create command added",
            "document_reviews + pr_automation sections added to integrations.yml",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.1.0"},
    },
    {
        "from":        "2.1.0",
        "to":          "2.2.0",
        "description": "Code review gate (/pre-review + /address-review)",
        "notes": [
            "/pre-review agent command added — run before PR creation",
            "/address-review agent command added — handles human PR comments",
            "code_review section added to integrations.yml",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.2.0"},
    },
    {
        "from":        "2.2.0",
        "to":          "2.3.0",
        "description": "Explicit reading_mode enforcement",
        "notes": [
            "reading_mode field added to manifest.yml (auto/summary/full)",
            "All prompts now check reading_mode before reading feature docs",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.3.0"},
    },
    {
        "from":        "2.3.0",
        "to":          "2.4.0",
        "description": "/specify-uc use case specification command",
        "notes": [
            "/specify-uc inserted between /specify-brd and /specify-srd",
            "use-cases.md template added with actor registry, UC details, traceability",
            "SRD now derives FR-NNN from UC paths",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.4.0"},
    },
    {
        "from":        "2.4.0",
        "to":          "2.5.0",
        "description": "19 SDLC review findings fixed",
        "notes": [
            "change-rules.md dependency chain updated (use-cases between brd and srd)",
            "task.prompt.md: EP-NNN exception paths generate TC-NNN test cases",
            "security design: full STRIDE/DREAD methodology",
            "CLAUDE.md: /checklist mandatory for mvp+",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.5.0"},
    },
    {
        "from":        "2.5.0",
        "to":          "2.6.0",
        "description": "/change command + 20 stakeholder template improvements",
        "notes": [
            "/change command added — type-aware sequential change request system",
            "changeset-template.md added to .specify/templates/",
            "20 template fixes: approvals tables, BUFFER story, CVSS column, BRD investment summary",
            "/create-context: feature-hint header (# specify: sentence) added",
            "SDLC-COMPLETE-GUIDE.md and CHANGE-GUIDE.md rewritten",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.6.0"},
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
