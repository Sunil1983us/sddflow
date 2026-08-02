from __future__ import annotations

from pathlib import Path

import click
import questionary
from rich.console import Console

from sdd.utils.detect import PROJECT_TYPES, detect_project_type
from sdd.utils.manifest import MANIFEST_PATH, SDD_VERSION, patch_manifest, read_manifest
from sdd.utils.scaffold import (
    ALL_PACKS,
    PACK_DESCRIPTIONS,
    TYPE_TO_PACK,
    recommended_pack,
    scaffold_pack,
)
from sdd.utils.validate import assert_valid_name, validate_name

# Reverse of TYPE_TO_PACK — packs dedicated to one project type don't need
# to ask (or auto-detect) project_type at all, since choosing the pack
# already answers that question. Only sdd-universal (not in this map)
# genuinely branches its tech-stack tables on project_type.
PACK_TO_TYPE: dict[str, str] = {v: k for k, v in TYPE_TO_PACK.items()}

AI_TOOLS = [
    questionary.Choice("Claude Code    — type /specify", value="claude-code"),
    questionary.Choice("GitHub Copilot — type /specify", value="copilot"),
    questionary.Choice(
        "Cursor         — chat: Read and follow the prompt file", value="cursor"
    ),
    questionary.Choice("Windsurf       — chat: Run specify", value="windsurf"),
    questionary.Choice("Other / not sure", value="other"),
]

# Friendly aliases for --scope -- manifest.yml's own schema only ever
# stores pilot/mvp/full (every gate/command in every pack checks for those
# three exact values), so aliases are resolved here, before anything is
# written, rather than teaching every downstream check about them. Mirrors
# the same alias handling in setup.sh/setup.ps1.
_SCOPE_ALIASES: dict[str, str] = {
    "lean": "pilot",
    "standard": "mvp",
    "regulated": "full",
}
_VALID_SCOPES = {"pilot", "mvp", "full"}


def _resolve_scope(scope: str | None) -> str | None:
    if not scope:
        return scope
    resolved = _SCOPE_ALIASES.get(scope, scope)
    if resolved not in _VALID_SCOPES:
        raise click.BadParameter(
            f"'{scope}' — must be one of: pilot (lean), mvp (standard), full (regulated)",
            param_hint="'-s' / '--scope'",
        )
    return resolved


_AI_TOOL_NEXT_STEP: dict[str, str] = {
    "claude-code": "Open this folder in Claude Code and type:  [bold]/specify[/bold]",
    "copilot": "Open in VS Code with Copilot Chat and type:  [bold]/specify[/bold]",
    "cursor": "In Cursor chat, type:\n     [bold]Read and follow .github/prompts/specify.prompt.md exactly[/bold]",
    "windsurf": "In Windsurf chat, type:  [bold]Run specify[/bold]",
    "other": "Copy [cyan].github/prompts/specify.prompt.md[/cyan] and paste into your AI tool",
}

console = Console()

_BANNER = f"""
[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]
  [bold cyan]SDD Framework[/bold cyan] [dim]v{SDD_VERSION}[/dim]
[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]"""


@click.command()
@click.option("-p", "--project", "project_name", default=None, help="Project name")
@click.option(
    "-f", "--feature", "feature_name", default=None, help="First feature name"
)
@click.option(
    "-s",
    "--scope",
    default=None,
    help="pilot (lean) | mvp (standard) | full (regulated)",
)
@click.option(
    "-t",
    "--type",
    "project_type",
    default=None,
    help="Project type (auto-detected if omitted)",
)
@click.option("--pack", default=None, help=f"Pack to scaffold: {', '.join(ALL_PACKS)}")
@click.option("--plan-mode", default=None, help="unified | separate")
@click.option("--reading-mode", default=None, help="auto | summary | full")
@click.option(
    "--ai-tool",
    default=None,
    help=f"AI tool: {', '.join(c.value for c in AI_TOOLS)}",
)
def init_command(
    project_name,
    feature_name,
    scope,
    project_type,
    pack,
    plan_mode,
    reading_mode,
    ai_tool,
):
    """Initialize an SDD pack in the current project directory."""
    console.print(_BANNER)
    scope = _resolve_scope(scope)
    if ai_tool is not None and ai_tool not in {c.value for c in AI_TOOLS}:
        raise click.BadParameter(
            f"'{ai_tool}' — must be one of: {', '.join(c.value for c in AI_TOOLS)}",
            param_hint="'--ai-tool'",
        )

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
    existing = read_manifest() or {} if chosen_pack is None else {}
    if chosen_pack == "sdd-micro":
        is_micro = True
    elif chosen_pack is None:
        is_micro = "project_type" not in existing and "scope" not in existing.get(
            "project", {}
        )
    else:
        is_micro = False

    # A pack dedicated to one project type already answers the question —
    # asking again (or running detection a second time, right after
    # scaffold_pack just copied that pack's own files into the directory)
    # is redundant and, worse, offers irrelevant choices like "mobile" for
    # a project the user just told us is sdd-backend-service.
    pack_name = chosen_pack or existing.get("pack")
    pinned_type = PACK_TO_TYPE.get(pack_name)

    # ── Project type (needed for manifest even in fill mode) ─────────────────
    if not is_micro and not project_type and pinned_type:
        project_type = pinned_type
        console.print(
            f"[dim]  Project type:[/dim] [green]{project_type}[/green] [dim](from {pack_name})[/dim]"
        )
    elif not is_micro and not project_type:
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
                questionary.Choice(
                    "pilot  — quick prototype, minimal docs", value="pilot"
                ),
                questionary.Choice(
                    "mvp    — production-ready (+ api-spec, data-model, LLD, ADR)",
                    value="mvp",
                ),
                questionary.Choice(
                    "full   — enterprise (+ resilience, investigation, security-design)",
                    value="full",
                ),
            ],
        ).ask()

    # sdd-micro has neither field in its manifest.yml template (3-command,
    # no plan/design gates to choose a style for) -- same is_micro guard
    # as scope above.
    if not is_micro and not plan_mode:
        plan_mode = questionary.select(
            "Plan document style:",
            choices=[
                questionary.Choice(
                    "unified  — one combined design.md (architecture + diagrams + "
                    "API design + decisions). Good for small teams, fast delivery, "
                    "single review gate.",
                    value="unified",
                ),
                questionary.Choice(
                    "separate — three focused documents reviewed one by one "
                    "(arch.md → hld.md → adr.md, mvp+ only). Good for larger "
                    "teams, separate approvals, detailed audit trail.",
                    value="separate",
                ),
            ],
        ).ask()

    if not is_micro and not reading_mode:
        reading_mode = questionary.select(
            "Document reading mode (token economy — see summary-rules.md):",
            choices=[
                questionary.Choice(
                    "auto    — use each doc's .summary.md when present, fall back "
                    "to the full doc (and generate a summary) when missing. Good "
                    "for almost everyone — self-heals, never stuck.",
                    value="auto",
                ),
                questionary.Choice(
                    "summary — always use .summary.md; warns instead of reading "
                    "the full doc if one is missing. Good for strict token "
                    "budgets.",
                    value="summary",
                ),
                questionary.Choice(
                    "full    — always read the full document, every command. "
                    "Good for deep debugging, or migrating a project with no "
                    "summaries.",
                    value="full",
                ),
            ],
        ).ask()

    if not ai_tool:
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
        console.print(f"  Plan    : [cyan]{plan_mode}[/cyan]")
        console.print(f"  Reading : [cyan]{reading_mode}[/cyan]")
    console.print(f"  AI tool : [cyan]{ai_tool}[/cyan]")
    console.print()

    # ── Update manifest.yml via PyYAML (no string injection possible) ─────────
    project_patch = {
        "name": project_name,
        "feature": feature_name,
        "context_file": f"{feature_name}.md",
    }
    manifest_patch = {
        "project": project_patch,
        "sdd_version": SDD_VERSION,
        "ai_tool": ai_tool,
    }
    if not is_micro:
        project_patch["scope"] = scope
        manifest_patch["project_type"] = project_type
        manifest_patch["plan_mode"] = plan_mode
        manifest_patch["reading_mode"] = reading_mode
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
    console.print("  [bold green]Setup complete![/bold green]  Next steps:")
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
        choices.append(
            questionary.Choice(
                f"{rec}  ({PACK_DESCRIPTIONS[rec]})  ← recommended for {project_type}",
                value=rec,
            )
        )
        choices.append(
            questionary.Choice(
                f"sdd-universal  ({PACK_DESCRIPTIONS['sdd-universal']})",
                value="sdd-universal",
            )
        )
    else:
        label = f"for {project_type}" if project_type else "when type is unclear"
        choices.append(
            questionary.Choice(
                f"sdd-universal  ({PACK_DESCRIPTIONS['sdd-universal']})  ← recommended {label}",
                value="sdd-universal",
            )
        )

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
