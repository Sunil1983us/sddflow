"""`sdd project-type` -- guided migration of an sdd-universal project's
project_type after initial setup (e.g. backend-service -> fullstack, once
a second feature of a different kind joins the project).

sdd-universal-only: the other 4 packs have a fixed tech stack baked into
their own constitution and no project_type field to migrate at all --
`show`/`migrate` both refuse cleanly with that explanation if run against
a manifest.yml with no project_type field.

This command deliberately does NOT touch constitution.md -- Tech Stack
row compatibility can't be determined mechanically, so extending the
constitution for the new type is always left as a separate, agent-guided
step (see CLAUDE.md "Migrating project_type", which points at /change,
change type Technical). This command's job is narrower and mechanical:
report what changes (which extended docs gain/lose applicability), then
-- only once the caller has reviewed that and, for a lossy migration,
explicitly acknowledged it -- update the one manifest.yml field.
"""

from __future__ import annotations

import click
from rich.console import Console

from sdd.utils.manifest import patch_manifest, read_manifest
from sdd.utils.project_type import (
    PROJECT_TYPES,
    classify_migration,
    is_valid_project_type,
)

console = Console()


def _current_project_type() -> tuple[dict, str | None] | None:
    """Reads manifest.yml. Returns (manifest, project_type) or None (with
    an error already printed) if this isn't an sdd-universal project."""
    manifest = read_manifest()
    if manifest is None:
        console.print(
            "[red]No .specify/manifest.yml found — are you in a project root?[/red]"
        )
        return None
    if manifest.get("pack") != "sdd-universal" and "project_type" not in manifest:
        console.print(
            "[red]This project has no project_type field — project-type "
            "migration only applies to sdd-universal projects.[/red] The "
            "other 4 packs (backend-service, frontend-spa, mobile, "
            "fullstack) each have one fixed tech stack baked into their "
            "own constitution.md and don't migrate between types."
        )
        return None
    return manifest, manifest.get("project_type")


@click.group(name="project-type")
def project_type_command():
    """Show or migrate an sdd-universal project's project_type."""


@project_type_command.command("show")
def project_type_show():
    """Print the current project_type and which extended docs it uses."""
    result = _current_project_type()
    if result is None:
        raise SystemExit(2)
    _manifest, current = result
    console.print(
        f"project_type: [bold]{current or '(unset — resolved by /specify)'}[/bold]"
    )
    console.print(f"Valid types: {', '.join(PROJECT_TYPES)}")


@project_type_command.command("migrate")
@click.option("--to", "to_type", required=True, help="Target project_type")
@click.option(
    "--apply",
    is_flag=True,
    default=False,
    help="Actually write manifest.yml. Without this flag, only prints the report.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Required alongside --apply when the migration is lossy (drops "
    "applicability of an extended doc type already in use).",
)
def project_type_migrate(to_type: str, apply: bool, force: bool):
    """Report (and optionally apply) what changes when project_type
    switches to TO_TYPE. Dry-run by default -- pass --apply to write."""
    if not is_valid_project_type(to_type):
        console.print(
            f"[red]'{to_type}' is not a recognized project_type.[/red] "
            f"Valid types: {', '.join(PROJECT_TYPES)}"
        )
        raise SystemExit(2)

    result = _current_project_type()
    if result is None:
        raise SystemExit(2)
    _manifest, current = result

    report = classify_migration(current, to_type)
    console.print(report.render())

    if current == to_type:
        console.print("[dim]Already this type — nothing to migrate.[/dim]")
        raise SystemExit(0)

    if not apply:
        console.print(
            "\n[dim]Dry run only — nothing was written. Re-run with "
            "--apply once you've reviewed this"
            + (
                " (add --force too — this migration drops doc applicability)"
                if report.is_lossy
                else ""
            )
            + ".[/dim]"
        )
        raise SystemExit(0)

    if report.is_lossy and not force:
        console.print(
            "\n[red]Refusing to apply: this migration drops applicability "
            "of extended docs already in use for this project. Re-run "
            "with --apply --force once you've confirmed that's "
            "intentional.[/red]"
        )
        raise SystemExit(1)

    patch_manifest({"project_type": to_type})
    console.print(
        f"\n[green]✓[/green] manifest.yml project_type updated: "
        f"{current or '(unset)'} → {to_type}"
    )
    console.print(
        "[yellow]Reminder:[/yellow] constitution.md Tech Stack was NOT "
        "changed by this command — run /change (change type: Technical) "
        "to extend it for the new type before generating anything "
        "against it."
    )
