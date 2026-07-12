from pathlib import Path
import click
import questionary
from rich.console import Console

from sdd.utils.detect import detect_project_type, PROJECT_TYPES
from sdd.utils.validate import validate_name, assert_valid_name
from sdd.utils.manifest import patch_manifest, read_manifest, MANIFEST_PATH, SDD_VERSION
from sdd.utils.scaffold import (
    recommended_pack, scaffold_pack,
    PACK_DESCRIPTIONS, ALL_PACKS, TYPE_TO_PACK,
)

AI_TOOLS = [
    questionary.Choice("Claude Code    — type /specify",                                value="claude-code"),
    questionary.Choice("GitHub Copilot — type /specify",                                value="copilot"),
    questionary.Choice("Cursor         — chat: Read and follow the prompt file",        value="cursor"),
    questionary.Choice("Windsurf       — chat: Run specify",                            value="windsurf"),
    questionary.Choice("Other / not sure",                                              value="other"),
]

_AI_TOOL_NEXT_STEP: dict[str, str] = {
    "claude-code": "Open this folder in Claude Code and type:  [bold]/specify[/bold]",
    "copilot":     "Open in VS Code with Copilot Chat and type:  [bold]/specify[/bold]",
    "cursor":      "In Cursor chat, type:\n     [bold]Read and follow .github/prompts/specify.prompt.md exactly[/bold]",
    "windsurf":    "In Windsurf chat, type:  [bold]Run specify[/bold]",
    "other":       "Copy [cyan].github/prompts/specify.prompt.md[/cyan] and paste into your AI tool",
}

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
    chosen_pack = None
    if not Path(MANIFEST_PATH).exists():
        chosen_pack = _scaffold_mode(project_type, pack)

    # ── Fill mode: manifest.yml already exists ────────────────────────────────
    # (also reached after scaffold_mode copies the pack)

    # sdd-micro has no scope/project_type ceremony — its manifest.yml
    # template has neither key, which is how we detect it in fill mode
    # (existing manifest, chosen_pack unknown) without tracking the pack
    # name anywhere persistent.
    if chosen_pack == "sdd-micro":
        is_micro = True
    elif chosen_pack is None:
        existing = read_manifest() or {}
        is_micro = "project_type" not in existing and "scope" not in existing.get("project", {})
    else:
        is_micro = False

    # ── Project type (needed for manifest even in fill mode) ─────────────────
    if not is_micro and not project_type:
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

    if not is_micro and not scope:
        scope = questionary.select(
            "Scope:",
            choices=[
                questionary.Choice("pilot  — quick prototype, minimal docs", value="pilot"),
                questionary.Choice("mvp    — production-ready (+ api-spec, data-model, LLD, ADR)", value="mvp"),
                questionary.Choice("full   — enterprise (+ resilience, investigation, security-design)", value="full"),
            ],
        ).ask()

    ai_tool = questionary.select(
        "Which AI tool will you use?",
        choices=AI_TOOLS,
    ).ask()

    # Validate CLI-supplied values (questionary validates interactive ones)
    assert_valid_name(project_name, "Project name")
    assert_valid_name(feature_name, "Feature name")

    console.print()
    console.print("  Setting up:")
    console.print(f"  Project : [cyan]{project_name}[/cyan]")
    if not is_micro:
        console.print(f"  Type    : [cyan]{project_type}[/cyan]")
    console.print(f"  Feature : [cyan]{feature_name}[/cyan]")
    if not is_micro:
        console.print(f"  Scope   : [cyan]{scope}[/cyan]")
    console.print(f"  AI tool : [cyan]{ai_tool}[/cyan]")
    console.print()

    # ── Update manifest.yml via PyYAML (no string injection possible) ─────────
    project_patch = {
        "name":         project_name,
        "feature":      feature_name,
        "context_file": f"{feature_name}.md",
    }
    manifest_patch = {
        "project":      project_patch,
        "sdd_version":  SDD_VERSION,
        "ai_tool":      ai_tool,
    }
    if not is_micro:
        project_patch["scope"] = scope
        manifest_patch["project_type"] = project_type
    # Records which pack this project was scaffolded from — nothing else
    # persists this (project_type is ambiguous: sdd-universal can produce
    # any project_type too), and `sdd upgrade --sync-prompts` needs it to
    # know which pack's .github/prompts/ to copy from. chosen_pack is only
    # set on a fresh scaffold; in fill mode (manifest.yml already existed)
    # leave whatever "pack" the manifest already has, if any.
    if chosen_pack:
        manifest_patch["pack"] = chosen_pack
    patch_manifest(manifest_patch)
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
    next_step = _AI_TOOL_NEXT_STEP.get(ai_tool, _AI_TOOL_NEXT_STEP["other"])
    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print(f"  [bold green]Setup complete![/bold green]  Next steps:")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()
    console.print(f"  1. Edit [cyan]{context_path}[/cyan]")
    console.print("     Fill in: What it does, actors, key flows, tech stack, NFRs")
    console.print("     (or run /create-context to build it interactively)")
    console.print()
    console.print(f"  2. {next_step}")
    console.print()
    console.print("  See QUICKSTART.md for the full walkthrough.")
    console.print()


def _scaffold_mode(project_type: str | None, pack_override: str | None) -> str:
    """
    No SDD pack found — detect project type, recommend a pack, copy it here.
    Exits (raises SystemExit) only on error; on success the manifest will now
    exist, init_command continues normally, and the chosen pack name is
    returned so callers can branch on pack-specific manifest shape (e.g.
    sdd-micro skips the scope/project_type questions).
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

    return chosen_pack


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
