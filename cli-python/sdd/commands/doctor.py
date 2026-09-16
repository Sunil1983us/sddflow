"""`sdd doctor` -- two independent, read-only health checks:

1. Drift between this project's framework-managed files (templates,
   prompts, commands, instructions, setup scripts, and a few
   IDE-integration files) and the pack content bundled with the
   currently installed `sddflow` CLI -- see
   sdd/utils/managed_files.py's module docstring for why this exists.
2. A live check of the configured Jira Epic/Feature issue type against
   Jira's own createmeta -- catches "this push will fail" (a missing
   required custom field, a typo'd issue type name) before it does,
   using Jira's own field requirements as the source of truth instead of
   this codebase needing to know about any given organization's
   customizations in advance. Skipped entirely if Jira isn't configured;
   see --skip-jira to opt out even when it is.

Changes nothing either way.
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from sdd.commands.jira import check_epic_createmeta
from sdd.commands.upgrade import _resolve_pack
from sdd.utils.atlassian_auth import load_jira_session
from sdd.utils.integrations import IntegrationsConfigError, load_integrations
from sdd.utils.jira_client import JiraClient
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
@click.option(
    "--skip-jira",
    is_flag=True,
    help="Skip the live Jira field-requirements check (managed-files check only).",
)
def doctor_command(pack_override, quiet, skip_jira):
    """Report drift between this project's framework-managed files and
    the currently installed sddflow pack. Read-only -- never writes
    anything; run `sdd upgrade --apply-files` to actually apply pack
    content updates."""
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

    files_ok = True
    if not report:
        console.print(
            f"  [dim]No managed files defined for pack '{pack_name}' "
            "-- nothing to check.[/dim]"
        )
        console.print()
    else:
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
            console.print(
                f"  [green]✓  All {total} managed file(s) up to date.[/green]"
            )
            console.print()
        else:
            files_ok = False
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
                "  [dim]Run [/dim][bold]sdd upgrade --apply-files[/bold][dim] to apply "
                "safe updates automatically (locally-modified files are left "
                "alone unless you also pass --force).[/dim]"
            )
            console.print()

    jira_ok = True
    if not skip_jira:
        jira_ok = _check_jira_field_requirements()

    if not files_ok or not jira_ok:
        raise SystemExit(1)


def _check_jira_field_requirements() -> bool:
    """Live Jira check: validates the configured Epic/Feature issue type
    against Jira's own createmeta (see check_epic_createmeta()'s
    docstring) -- catches "this push will fail" locally, using Jira's own
    field requirements as the source of truth, without this codebase
    needing to know about any given organization's custom issue types in
    advance.

    Silently does nothing (returns True) if Jira isn't configured at all
    -- integrations.yml missing/invalid, or its jira: section absent --
    since this is an optional adapter, not something every project has
    configured (see this repo's own product-scope policy: core never
    depends on Jira/Confluence being present)."""
    try:
        cfg = load_integrations()
    except (FileNotFoundError, IntegrationsConfigError):
        return True
    if cfg.jira is None:
        return True

    console.print(
        "  [bold]Jira field requirements[/bold]  "
        "[dim](live check against createmeta)[/dim]"
    )
    console.print()

    try:
        prof, session = load_jira_session(cfg)
        client = JiraClient(session, prof.base_url, deployment=prof.deployment)
        findings = check_epic_createmeta(cfg.jira, client)
    except Exception as e:
        console.print(f"  [red]✗  Could not complete the Jira check: {e}[/red]")
        console.print()
        return False

    ok = True
    for passed, message in findings:
        symbol = "[green]✓[/green]" if passed else "[red]✗[/red]"
        console.print(f"  {symbol}  {message}")
        ok = ok and passed
    console.print()
    return ok
