"""`sdd feature` -- read-only, filesystem-only views of a project's
features and their pipeline status. Deliberately has no manifest.yml
schema of its own: `list` scans .specify/features/ directly (the same
scan the dashboard already uses as its source of truth), and `status`
calls the exact same build_feature_status()/build_project_status() the
dashboard's HTTP handler renders -- so this is a terminal window onto the
same data, not a second copy of it that could drift.

Unlike `sdd review status` (which requires jira: configured and shows
only Jira-tracked document reviews), this works in every review mode --
chat, local, jira -- since "Status:" headers and Approvals tables inside
the .md files themselves are the authoritative gate in every mode (see
CLAUDE.md "Document Review Gates").
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from sdd.utils.manifest import read_manifest
from sdd.utils.status import (
    build_feature_status,
    build_project_status,
    list_feature_names,
)

console = Console()

_STATE_ICON = {
    "done": ("[green]✓[/green]", None),
    "current": ("[yellow]●[/yellow]", "yellow"),
    "upcoming": ("[dim]○[/dim]", None),
    "skipped": ("[dim]┄[/dim]", None),
}


@click.group()
def feature_command():
    """List features and check per-feature pipeline/approval status."""


@feature_command.command("list")
def feature_list():
    """List every feature folder under .specify/features/, with each
    one's current pipeline stage -- the same set `sdd dashboard` shows,
    read straight from disk (nothing stored in manifest.yml to drift)."""
    root = Path(".")
    names = list_feature_names(root)
    if not names:
        console.print(
            "[dim]No features yet — run /create-context or /specify-brd to start one.[/dim]"
        )
        return

    manifest = read_manifest() or {}
    current = (manifest.get("project") or {}).get("feature")

    # One pass computes every feature's status -- build_project_status()
    # already iterates list_feature_names() internally, so calling it
    # once here (not once per name) avoids redoing that work per feature.
    project_status = build_project_status(root)
    by_name = {f["name"]: f for f in project_status["features"]}

    for name in names:
        marker = " [cyan](current)[/cyan]" if name == current else ""
        cs = (by_name.get(name) or {}).get("current_stage")
        stage_desc = (
            f"{cs['doc']} — {cs['status'] or 'in progress'}"
            if cs and cs.get("doc")
            else "not started"
        )
        console.print(f"  [bold]{name}[/bold]{marker}  [dim]{stage_desc}[/dim]")


@feature_command.command("status")
@click.option(
    "--feature", default=None, help="Feature name (default: from manifest.yml)"
)
def feature_status(feature):
    """Full pipeline + approval status for one feature -- the same view
    `sdd dashboard` renders, as terminal text. Works with no Jira/
    Confluence configured (unlike `sdd review status`), since it reads
    each document's own Status: header and Approvals table directly."""
    root = Path(".")
    manifest = read_manifest() or {}
    proj = manifest.get("project") or {}
    feature_name = feature or proj.get("feature", "")
    if not feature_name:
        console.print(
            "[red]✗  No feature specified and none set in manifest.yml "
            "(project.feature).[/red]"
        )
        raise SystemExit(2)

    known = list_feature_names(root)
    if feature_name not in known:
        console.print(
            f"[red]✗  '{feature_name}' has no .specify/features/ folder.[/red] "
            f"Known features: {', '.join(known) if known else '(none yet)'}"
        )
        raise SystemExit(2)

    scope = proj.get("scope")
    plan_mode = manifest.get("plan_mode") or "unified"
    project_type = manifest.get("project_type")
    fs = build_feature_status(
        root, feature_name, plan_mode=plan_mode, scope=scope, project_type=project_type
    )

    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print(f"  [bold cyan]Feature Status[/bold cyan] — {feature_name}")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()

    console.print("  [bold]Pipeline[/bold]")
    for step in fs["pipeline"]["steps"]:
        icon, _ = _STATE_ICON.get(step["state"], ("?", None))
        if step["state"] == "skipped":
            reason = f"  [dim](skipped — {step.get('skip')})[/dim]"
            console.print(f"    {icon}  [dim]{step['label']}[/dim]{reason}")
            continue
        hint = ""
        if step["state"] in ("current", "upcoming") and step.get("persona"):
            hint = f"  [dim]· ask {step['persona']['name']}[/dim]"
        console.print(f"    {icon}  {step['label']}{hint}")
    console.print()
    console.print(f"  [bold]Next:[/bold] {fs['pipeline']['next_action']}")
    console.print()

    docs_with_approvals = [d for d in fs["docs"] if d.get("approvals")]
    if docs_with_approvals:
        console.print("  [bold]Document Approvals[/bold]")
        for d in docs_with_approvals:
            status_style = (
                "green" if (d.get("status") or "").lower() == "approved" else "yellow"
            )
            console.print(
                f"    [{status_style}]{d['label']:<28}[/{status_style}] "
                f"{d.get('status') or 'Draft'}"
            )
            for row in d["approvals"]:
                who = (
                    row.get("approver")
                    or row.get("expected_approver")
                    or "(unassigned)"
                )
                row_status = row.get("status") or "Pending"
                row_style = "green" if row_status.lower() == "approved" else "dim"
                console.print(
                    f"        [{row_style}]{row['role']:<30} {row_status:<10} {who}[/{row_style}]"
                )
        console.print()

    t = fs["tasks"]
    if t["total"]:
        pct = round(100 * t["done"] / t["total"])
        console.print(
            f"  [bold]Tasks:[/bold] {t['done']}/{t['total']} done ({pct}%)"
            f"  [dim]{t['in_progress']} in progress, {t['not_started']} not started[/dim]"
        )
        console.print()

    if fs["business_objectives"]:
        console.print("  [bold]Business Objectives[/bold]")
        for bo in fs["business_objectives"]:
            progress = f"{bo['percent_done']}% ({bo['tasks_done']}/{bo['task_count']})"
            console.print(
                f"    {bo['bo_id']:<8} {bo.get('status', 'Not Started'):<14} "
                f"{progress:<16}  [dim]{bo.get('objective', '')[:60]}[/dim]"
            )
        console.print()
