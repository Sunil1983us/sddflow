from pathlib import Path
import click
import questionary
from rich.console import Console

from sdd.utils.detect import detect_project_type, PROJECT_TYPES
from sdd.utils.validate import validate_name, assert_valid_name
from sdd.utils.manifest import patch_manifest, MANIFEST_PATH, SDD_VERSION
from sdd.utils.scaffold import (
    recommended_pack, scaffold_pack,
    PACK_DESCRIPTIONS, ALL_PACKS, TYPE_TO_PACK,
)

console = Console()

_BANNER = f"""
[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]
  [bold cyan]SDD Framework[/bold cyan] [dim]v{SDD_VERSION}[/dim]
[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]"""


@click.command()
@click.option("-p", "--project", "project_name", default=None, help="Project name")
@click.option("-f", "--feature", "feature_name", default=None, help="First feature name")
@click.option("-s", "--scope",   default=None,   help="pilot | mvp | full")
@click.option("-t", "--type",    "project_type", default=None,
              help="Project type (auto-detected if omitted)")
@click.option("--pack",          default=None,
              help=f"Pack to scaffold: {', '.join(ALL_PACKS)}")
def init_command(project_name, feature_name, scope, project_type, pack):
    """Initialize an SDD pack in the current project directory."""
    console.print(_BANNER)

    # ── Scaffold mode: no pack present yet ───────────────────────────────────
    if not Path(MANIFEST_PATH).exists():
        _scaffold_mode(project_type, pack)

    # ── Fill mode: manifest.yml already exists ────────────────────────────────
    # (also reached after scaffold_mode copies the pack)

    # ── Project type (needed for manifest even in fill mode) ─────────────────
    if not project_type:
        console.print("[dim]  Detecting project type...[/dim] ", end="")
        detected = detect_project_type(".")
        if detected:
            console.print(f"[green]{detected}[/green]")
            confirmed = questionary.confirm(
                f"  Use detected type '{detected}'?", default=True
            ).ask()
            project_type = detected if confirmed else None

        if not project_type:
            project_type = questionary.select(
                "  Project type:",
                choices=PROJECT_TYPES,
            ).ask()

    # ── Interactive prompts ───────────────────────────────────────────────────
    if not project_name:
        project_name = questionary.text(
            "Project name:",
            validate=lambda v: validate_name(v, "Project name") or True,
        ).ask()

    if not feature_name:
        feature_name = questionary.text(
            "First feature name:",
            validate=lambda v: validate_name(v, "Feature name") or True,
        ).ask()

    if not scope:
        scope = questionary.select(
            "Scope:",
            choices=[
                questionary.Choice("pilot  — quick prototype, minimal docs", value="pilot"),
                questionary.Choice("mvp    — production-ready (+ api-spec, data-model, LLD, ADR)", value="mvp"),
                questionary.Choice("full   — enterprise (+ resilience, investigation, security-design)", value="full"),
            ],
        ).ask()

    # Validate CLI-supplied values (questionary validates interactive ones)
    assert_valid_name(project_name, "Project name")
    assert_valid_name(feature_name, "Feature name")

    console.print()
    console.print("  Setting up:")
    console.print(f"  Project : [cyan]{project_name}[/cyan]")
    console.print(f"  Type    : [cyan]{project_type}[/cyan]")
    console.print(f"  Feature : [cyan]{feature_name}[/cyan]")
    console.print(f"  Scope   : [cyan]{scope}[/cyan]")
    console.print()

    # ── Update manifest.yml via PyYAML (no string injection possible) ─────────
    patch_manifest({
        "project": {
            "name":         project_name,
            "scope":        scope,
            "feature":      feature_name,
            "context_file": f"{feature_name}.md",
        },
        "project_type": project_type,
        "sdd_version":  SDD_VERSION,
    })
    console.print(f"  [green]✓[/green]  {MANIFEST_PATH} filled")

    # ── Create context file ───────────────────────────────────────────────────
    context_path = Path(".specify") / "contexts" / f"{feature_name}.md"
    context_path.parent.mkdir(parents=True, exist_ok=True)

    if not context_path.exists():
        context_path.write_text(_context_template(feature_name, project_name))
        console.print(f"  [green]✓[/green]  {context_path} created")
    else:
        console.print(f"  [dim]·[/dim]  {context_path} already exists — skipped")

    # ── Create feature output directory ──────────────────────────────────────
    feature_dir = Path(".specify") / "features" / feature_name
    feature_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"  [green]✓[/green]  {feature_dir}/ ready")

    # ── Done ──────────────────────────────────────────────────────────────────
    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print(f"  [bold green]Setup complete![/bold green]  Next steps:")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()
    console.print(f"  1. Edit [cyan]{context_path}[/cyan]")
    console.print("     Fill in: What it does, actors, key flows, tech stack, NFRs")
    console.print("     (or run /create-context to build it interactively)")
    console.print()
    console.print("  2. Open in your AI tool and run /specify")
    console.print()
    console.print("     [bold]Claude Code[/bold]  →  /specify")
    console.print("     [bold]Copilot[/bold]      →  /specify")
    console.print("     [bold]Cursor[/bold]       →  Read and follow .github/prompts/specify.prompt.md")
    console.print("     [bold]Windsurf[/bold]     →  Run specify")
    console.print()
    console.print("  See QUICKSTART.md for the full walkthrough.")
    console.print()


def _scaffold_mode(project_type: str | None, pack_override: str | None) -> None:
    """
    No SDD pack found — detect project type, recommend a pack, copy it here.
    Exits (raises SystemExit) only on error; on success the manifest will now
    exist and init_command continues normally.
    """
    console.print("  [yellow]No SDD pack found in this directory.[/yellow]")
    console.print()

    # ── Detect or accept supplied project type ────────────────────────────────
    if not project_type:
        console.print("[dim]  Detecting project type...[/dim] ", end="")
        project_type = detect_project_type(".")
        if project_type:
            console.print(f"[green]{project_type}[/green]")
        else:
            console.print("[yellow]not detected[/yellow]")

    # ── Determine recommended pack ────────────────────────────────────────────
    rec = pack_override or recommended_pack(project_type)

    # ── Ask user which pack to scaffold ──────────────────────────────────────
    console.print()

    if pack_override:
        chosen_pack = pack_override
        console.print(f"  Pack: [cyan]{chosen_pack}[/cyan]  (from --pack flag)")
    else:
        choices = _build_pack_choices(project_type, rec)
        chosen_pack = questionary.select(
            "Which pack would you like to scaffold?",
            choices=choices,
        ).ask()

        if chosen_pack == "__all__":
            chosen_pack = questionary.select(
                "Select pack:",
                choices=[
                    questionary.Choice(
                        f"{p}  —  {PACK_DESCRIPTIONS[p]}",
                        value=p,
                    )
                    for p in ALL_PACKS
                ],
            ).ask()

    if not chosen_pack:
        console.print("[red]Cancelled.[/red]")
        raise SystemExit(1)

    # ── Copy pack files ───────────────────────────────────────────────────────
    console.print()
    console.print(f"  Scaffolding [cyan]{chosen_pack}[/cyan]...")
    try:
        n = scaffold_pack(chosen_pack, dest=".")
    except RuntimeError as e:
        console.print(f"[red]✗  {e}[/red]")
        raise SystemExit(1)

    console.print(f"  [green]✓[/green]  {chosen_pack} scaffolded ({n} files copied)")
    console.print()


def _build_pack_choices(project_type: str | None, rec: str) -> list:
    """Build the questionary choices list for pack selection."""
    choices = []

    if rec != "sdd-universal":
        choices.append(questionary.Choice(
            f"{rec}  ({PACK_DESCRIPTIONS[rec]})  ← recommended for {project_type}",
            value=rec,
        ))
        choices.append(questionary.Choice(
            f"sdd-universal  ({PACK_DESCRIPTIONS['sdd-universal']})",
            value="sdd-universal",
        ))
    else:
        label = f"for {project_type}" if project_type else "when type is unclear"
        choices.append(questionary.Choice(
            f"sdd-universal  ({PACK_DESCRIPTIONS['sdd-universal']})  ← recommended {label}",
            value="sdd-universal",
        ))

    choices.append(questionary.Choice("Choose from all packs…", value="__all__"))
    return choices


def _context_template(feature_name: str, project_name: str) -> str:
    return f"""# Context: {feature_name}
# Project: {project_name}
# Fill this file, then run /specify (or /create-context to build it interactively).

## What This Does
{{describe the feature in 2-3 sentences}}

## Actors
{{who triggers or benefits from this feature?}}

## Key Flows
{{describe 2-3 main user journeys}}

## Integrations
{{list any external systems, APIs, or databases}}

## Business Rules
{{any constraints, validation rules, or compliance requirements}}

## Tech Stack
{{language, framework, database, cache, CI/CD — fill what you know}}

## Non-Functional Requirements
{{performance targets, availability, security level}}

## Out of Scope
{{explicitly list what this feature does NOT cover}}

## Open Questions
{{anything unclear that needs a decision}}
"""
