from __future__ import annotations
import re
from pathlib import Path
import click
from rich.console import Console

from sdd.utils.atlassian_auth import load_profile, build_session
from sdd.utils.integrations import load_integrations
from sdd.utils.jira_client import JiraClient
from sdd.utils.confluence_client import ConfluenceClient
from sdd.utils.md_to_cf import md_to_storage
from sdd.utils.manifest import read_manifest
from sdd.utils.validate import safe_feature_path

console = Console()


def _cr_path(feature: str, cr_id: str) -> Path:
    return safe_feature_path(Path(".specify") / "features", feature) / "changesets" / f"{cr_id}.md"


def _extract_cr_summary(text: str) -> str:
    """Pull the one-line description from the CR record (§1 Change Description)."""
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("|") and len(line) > 10:
            return line[:120]
    return "Change Request"


@click.group()
def cr_command():
    """Change Request lifecycle — submit, check, status."""


@cr_command.command("submit")
@click.option("--cr",      required=True,
              help="CR identifier, e.g. CR-001")
@click.option("--profile", default=None)
@click.option("--feature", default=None,
              help="Feature name (default: from manifest.yml)")
@click.option("--reviewer", default=None,
              help="Jira accountId of the reviewer (overrides integrations.yml cr_reviewer)")
@click.option("--dry-run", is_flag=True)
def cr_submit(cr, profile, feature, reviewer, dry_run):
    """Push a CR record to Confluence and create a Jira review task.

    Run this automatically after /change saves the changeset record.
    Stakeholders review and comment in Confluence; the Jira task tracks
    formal approval exactly like sdd review submit does for spec docs.
    """
    cr_id = cr.upper()
    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    label = f"  [bold cyan]CR Submit[/bold cyan] — {cr_id}"
    if dry_run:
        label += "  [yellow](dry run)[/yellow]"
    console.print(label)
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()

    try:
        cfg = load_integrations()
    except FileNotFoundError as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)

    manifest     = read_manifest() or {}
    proj         = manifest.get("project") or {}
    project_name = proj.get("name", "Project")
    feature_name = feature or proj.get("feature", "")

    try:
        cr_file = _cr_path(feature_name, cr_id)
    except ValueError as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)
    if not cr_file.exists():
        console.print(f"  [red]✗  CR file not found: {cr_file}[/red]")
        console.print("  Run /change first to generate the changeset record.")
        raise SystemExit(1)

    cr_text    = cr_file.read_text()
    cr_summary = _extract_cr_summary(cr_text)
    page_title = f"{project_name} — {cr_id}: {cr_summary}"[:200]

    console.print(f"  CR file  : [cyan]{cr_file}[/cyan]")
    console.print(f"  Title    : [cyan]{page_title}[/cyan]")

    if dry_run:
        console.print()
        console.print("  [dim]would push to Confluence + create Jira review task[/dim]")
        console.print()
        return

    try:
        prof    = load_profile(profile or cfg.profile)
        session = build_session(prof)
    except Exception as e:
        console.print(f"  [red]✗  Auth error: {e}[/red]")
        raise SystemExit(1)

    page_url = ""

    # ── Push CR record to Confluence ─────────────────────────────────────────
    if cfg.confluence:
        cf_client = ConfluenceClient(session, prof.base_url)
        body_html = md_to_storage(cr_text)
        try:
            page, created = cf_client.upsert_page(
                cfg.confluence.space_key,
                page_title,
                body_html,
                cfg.confluence.parent_page_id,
            )
            action   = "[green]created[/green]" if created else "[dim]updated[/dim]"
            web_ui   = page.get("_links", {}).get("webui", "")
            page_url = f"{prof.base_url}/wiki{web_ui}" if web_ui else ""
            console.print(f"  {action}  Confluence: [cyan]{page_title}[/cyan]")
            if page_url:
                console.print(f"          [underline cyan]{page_url}[/underline cyan]")
        except Exception as e:
            console.print(f"  [yellow]⚠  Confluence error: {e} — continuing to Jira[/yellow]")
    else:
        console.print("  [dim]·[/dim]  Confluence not configured — skipping page push")

    # ── Create / update Jira review task ─────────────────────────────────────
    if cfg.jira:
        jira_client      = JiraClient(session, prof.base_url)
        idempotency_label = f"sdd-cr:{cr_id.lower()}"
        cr_project_key    = cfg.jira.key_for("cr")
        existing          = jira_client.find_by_label(cr_project_key, idempotency_label)

        reviewer_id = (
            reviewer
            or getattr(cfg, "cr_reviewer", None)
        )

        desc_text = (
            f"Please review Change Request {cr_id}.\n\n"
            f"Summary: {cr_summary}\n\n"
            + (f"Confluence: {page_url}\n\n" if page_url else "")
            + f"To APPROVE: set task to Done and comment 'Approved'.\n"
            f"To REQUEST CHANGES: add comments and leave the task open."
        )
        fields: dict = {
            "project":   {"key": cr_project_key},
            "issuetype": {"name": cfg.jira.issue_hierarchy.get("task", "Task")},
            "summary":   f"Review: {project_name} — {cr_id}",
            "labels":    ["sdd-cr", idempotency_label],
            "description": {
                "type": "doc", "version": 1,
                "content": [{"type": "paragraph", "content": [
                    {"type": "text", "text": desc_text}
                ]}],
            },
        }
        if reviewer_id:
            fields["assignee"] = {"accountId": reviewer_id}

        try:
            if existing:
                jira_client.update_issue(existing["key"], fields)
                task_key = existing["key"]
                console.print(f"  [dim]·[/dim]   Jira task updated: [cyan]{task_key}[/cyan]")
            else:
                result   = jira_client.create_issue(fields)
                task_key = result["key"]
                console.print(f"  [green]✓[/green]  Jira task created: [cyan]{task_key}[/cyan]")
        except Exception as e:
            console.print(f"  [yellow]⚠  Jira error: {e}[/yellow]")
    else:
        console.print("  [dim]·[/dim]  Jira not configured — skipping review task")

    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print(f"  [bold green]{cr_id} submitted![/bold green]")
    console.print("  Stakeholders can review and comment in Confluence.")
    console.print("  Reviewer approves in Jira when ready.")
    console.print(f"  Check status: [cyan]sdd cr check --cr {cr_id}[/cyan]")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()


@cr_command.command("check")
@click.option("--cr",      required=True)
@click.option("--profile", default=None)
def cr_check(cr, profile):
    """Check approval status of a CR in Jira.
    Exit codes: 0=approved 1=needs-revision 2=pending 3=not-submitted.
    """
    cr_id = cr.upper()
    console.print()

    try:
        cfg     = load_integrations()
        prof    = load_profile(profile or cfg.profile)
        session = build_session(prof)
    except Exception as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)

    if not cfg.jira:
        console.print("  [red]✗  No jira: section in integrations.yml[/red]")
        raise SystemExit(1)

    client = JiraClient(session, prof.base_url)
    issue  = client.find_by_label(cfg.jira.key_for("cr"), f"sdd-cr:{cr_id.lower()}")

    if not issue:
        console.print(f"  [dim]·  {cr_id} — NOT SUBMITTED[/dim]")
        console.print(f"     Run [cyan]sdd cr submit --cr {cr_id}[/cyan] first.")
        console.print()
        raise SystemExit(3)

    jira_status = issue.get("fields", {}).get("status", {}).get("name", "")
    comments    = client.get_comments(issue["key"])

    approved_statuses  = cfg.approved_statuses
    approved_keywords  = cfg.approved_keywords

    if jira_status in approved_statuses:
        console.print(f"  [green]✓  {cr_id} — APPROVED[/green]  [dim](Jira status: {jira_status})[/dim]")
        console.print()
        raise SystemExit(0)

    for c in comments:
        body = c.get("body", "")
        text = body if isinstance(body, str) else " ".join(
            n.get("text", "") for n in _walk_adf(body)
        )
        if any(kw in text.lower() for kw in approved_keywords):
            console.print(f"  [green]✓  {cr_id} — APPROVED[/green]  [dim](via comment keyword)[/dim]")
            console.print()
            raise SystemExit(0)

    if comments:
        console.print(f"  [yellow]✗  {cr_id} — NEEDS REVISION[/yellow]")
        console.print()
        console.print("  [bold]Review comments:[/bold]")
        for c in comments:
            author = (c.get("author") or {}).get("displayName", "?")
            body   = c.get("body", "")
            text   = body if isinstance(body, str) else " ".join(
                n.get("text", "") for n in _walk_adf(body)
            )
            console.print(f"  [cyan]{author}[/cyan]: {text.strip()[:300]}")
        console.print()
        raise SystemExit(1)

    console.print(f"  [dim]⏳  {cr_id} — PENDING[/dim]  Waiting for reviewer.")
    console.print()
    raise SystemExit(2)


def _walk_adf(node: dict) -> list[dict]:
    """Flatten ADF doc into text nodes."""
    out: list[dict] = []
    if node.get("type") == "text":
        out.append(node)
    for child in node.get("content", []):
        out.extend(_walk_adf(child))
    return out
