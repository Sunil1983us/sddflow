"""`sdd doctor` -- reports drift between this project's framework-managed
files (templates, prompts, commands, instructions, setup scripts, and a
few IDE-integration files) and the pack content bundled with the
currently installed `sddflow` CLI.

Read-only. Changes nothing -- see sdd/utils/managed_files.py's module
docstring for why this exists and what it's the first piece of.
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from sdd.commands.upgrade import _resolve_pack
from sdd.utils.managed_files import (
    STATUS_DIFFERS_UNKNOWN,
    STATUS_MISSING,
    STATUS_NEEDS_UPDATE,
    STATUS_UP_TO_DATE,
    STATUS_USER_MODIFIED,
    check_managed_files,
)
from sdd.utils.manifest import read_manifest

console = Console()

# (label, is_clean) -- is_clean=True doesn't affect the summary counts or
# exit code, just which symbol/color is used.
_STATUS_DISPLAY: dict[str, tuple[str, bool]] = {
    STATUS_UP_TO_DATE: ("[green]✓[/green]  up to date", True),
    STATUS_NEEDS_UPDATE: (
        "[yellow]↑[/yellow]  needs update (pack content changed)",
        False,
    ),
    STATUS_USER_MODIFIED: ("[red]✗[/red]  modified locally", False),
    STATUS_DIFFERS_UNKNOWN: (
        "[yellow]?[/yellow]  differs (no baseline recorded)",
        False,
    ),
    STATUS_MISSING: ("[dim]—[/dim]  missing", False),
}


@click.command()
@click.option(
    "--pack",
    "pack_override",
    default=None,
    help="Check against a specific pack instead of the one auto-detected from manifest.yml.",
)
@click.option(
    "--quiet",
    is_flag=True,
    help="Only print files that aren't up to date, plus the summary line.",
)
def doctor_command(pack_override, quiet):
    """Report drift between this project's framework-managed files and
    the currently installed sddflow pack. Read-only -- never writes
    anything; run `sdd upgrade` to actually apply pack content updates
    once that command covers more than manifest.yml's version stamp."""
    root = Path(".")
    manifest = read_manifest()
    if manifest is None:
        console.print(
            "  [red]✗  .specify/manifest.yml not found — are you in a "
            "scaffolded project's root?[/red]"
        )
        raise SystemExit(1)

    try:
        pack_name, source = _resolve_pack(manifest, pack_override)
    except ValueError as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)

    console.print()
    console.print(
        f"  [bold]sdd doctor[/bold]  —  pack: [cyan]{pack_name}[/cyan] "
        f"[dim]({source})[/dim]"
    )
    if "inferred" in source or "defaulting" in source:
        console.print(
            "  [yellow]⚠  Pack identity is a guess, not a certainty[/yellow] "
            "-- manifest.yml has no 'pack:' field recording which pack this\n"
            "  project was actually scaffolded from (only setup.sh's own "
            "packs write one deliberately; sdd-universal-scaffolded\n"
            "  projects handle every project_type from ONE shared set of "
            "prompt files, so a project_type guess can name the wrong,\n"
            "  type-specific pack here). If this project actually came "
            "from sdd-universal, or you're not sure, re-run with\n"
            "  [bold]--pack sdd-universal[/bold] -- otherwise every file "
            "below may show as 'differs' purely because it's being\n"
            "  compared against the wrong pack's content, not because "
            "anything is actually out of date."
        )
    console.print()

    try:
        report = check_managed_files(root, pack_name)
    except RuntimeError as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)

    if not report:
        console.print(
            f"  [dim]No managed files defined for pack '{pack_name}' "
            "-- nothing to check.[/dim]"
        )
        console.print()
        raise SystemExit(0)

    counts: dict[str, int] = {}
    for rel in sorted(report):
        status = report[rel]["status"]
        counts[status] = counts.get(status, 0) + 1
        if quiet and status == STATUS_UP_TO_DATE:
            continue
        label, _clean = _STATUS_DISPLAY[status]
        console.print(f"  {label}   [dim]{rel}[/dim]")

    console.print()
    total = len(report)
    up_to_date = counts.get(STATUS_UP_TO_DATE, 0)
    dirty = total - up_to_date
    if dirty == 0:
        console.print(f"  [green]✓  All {total} managed file(s) up to date.[/green]")
        console.print()
        raise SystemExit(0)

    parts = []
    if counts.get(STATUS_NEEDS_UPDATE):
        parts.append(f"{counts[STATUS_NEEDS_UPDATE]} need update")
    if counts.get(STATUS_USER_MODIFIED):
        parts.append(f"{counts[STATUS_USER_MODIFIED]} modified locally")
    if counts.get(STATUS_DIFFERS_UNKNOWN):
        parts.append(f"{counts[STATUS_DIFFERS_UNKNOWN]} differ (no baseline)")
    if counts.get(STATUS_MISSING):
        parts.append(f"{counts[STATUS_MISSING]} missing")
    console.print(
        f"  [yellow]{dirty}/{total} managed file(s) need attention[/yellow]: "
        + ", ".join(parts)
    )
    console.print(
        "  [dim]Note: sdd upgrade does not yet apply these -- it only "
        "stamps manifest.yml's version. This report is informational "
        "until that changes.[/dim]"
    )
    console.print()
    raise SystemExit(1)
