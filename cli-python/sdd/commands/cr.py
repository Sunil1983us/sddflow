from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from sdd.utils.atlassian_auth import load_confluence_session, load_jira_session
from sdd.utils.confluence_client import ConfluenceClient
from sdd.utils.integrations import IntegrationsConfigError, load_integrations
from sdd.utils.jira_client import JiraClient
from sdd.utils.manifest import read_manifest
from sdd.utils.md_to_cf import md_to_storage
from sdd.utils.validate import safe_feature_path

console = Console()


def _cr_path(feature: str, cr_id: str) -> Path:
    return (
        safe_feature_path(Path(".specify") / "features", feature)
        / "changesets"
        / f"{cr_id}.md"
    )


def _extract_cr_summary(text: str) -> str:
    """Pull the one-line description from the CR record (§1 Change Description)."""
    for line in text.splitlines():
        line = line.strip()
        if (
            line
            and not line.startswith("#")
            and not line.startswith("|")
            and len(line) > 10
        ):
            return line[:120]
    return "Change Request"


@click.group()
def cr_command():
    """Change Request lifecycle — submit, check, status."""


@cr_command.command("submit")
@click.option("--cr", required=True, help="CR identifier, e.g. CR-001")
@click.option("--profile", default=None)
@click.option(
    "--feature", default=None, help="Feature name (default: from manifest.yml)"
)
@click.option(
    "--reviewer",
    default=None,
    help="Jira accountId of the reviewer (overrides integrations.yml cr_reviewer)",
)
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
    except (FileNotFoundError, IntegrationsConfigError) as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)

    manifest = read_manifest() or {}
    proj = manifest.get("project") or {}
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

    cr_text = cr_file.read_text()
    cr_summary = _extract_cr_summary(cr_text)
    # Feature name (not project name) keeps this collision-safe: Confluence
    # enforces title uniqueness per SPACE, so two features could otherwise
    # push the same CR id (e.g. both have a "CR-001") to the same title.
    page_title = f"{feature_name} — {cr_id}: {cr_summary}"[:200]

    console.print(f"  CR file  : [cyan]{cr_file}[/cyan]")
    console.print(f"  Title    : [cyan]{page_title}[/cyan]")

    if dry_run:
        console.print()
        console.print("  [dim]would push to Confluence + create Jira review task[/dim]")
        console.print()
        return

    try:
        if cfg.jira:
            jira_prof, jira_session = load_jira_session(cfg, profile)
        if cfg.confluence:
            cf_prof, cf_session = load_confluence_session(cfg, profile)
    except Exception as e:
        console.print(f"  [red]✗  Auth error: {e}[/red]")
        raise SystemExit(1)

    page_url = ""

    # ── Push CR record to Confluence ─────────────────────────────────────────
    if cfg.confluence:
        cf_client = ConfluenceClient(cf_session, cf_prof.base_url)
        body_html, attachments, diagram_warnings = md_to_storage(
            cr_text, cfg.confluence.diagrams
        )
        try:
            from sdd.commands.confluence import (
                resolve_feature_parent_id,
                upload_diagram_attachments,
            )

            parent_id = resolve_feature_parent_id(
                cf_client, cfg.confluence, project_name, feature_name
            )
            page, created = cf_client.upsert_page(
                cfg.confluence.space_key,
                page_title,
                body_html,
                parent_id,
            )
            upload_diagram_attachments(cf_client, page["id"], attachments)
            action = "[green]created[/green]" if created else "[dim]updated[/dim]"
            web_ui = page.get("_links", {}).get("webui", "")
            page_url = f"{cf_prof.base_url}/wiki{web_ui}" if web_ui else ""
            console.print(f"  {action}  Confluence: [cyan]{page_title}[/cyan]")
            if page_url:
                console.print(f"          [underline cyan]{page_url}[/underline cyan]")
            for w in diagram_warnings:
                console.print(f"          [yellow]!  {w}[/yellow]")
        except Exception as e:
            console.print(
                f"  [yellow]⚠  Confluence error: {e} — continuing to Jira[/yellow]"
            )
    else:
        console.print("  [dim]·[/dim]  Confluence not configured — skipping page push")

    # ── Create / update Jira review task ─────────────────────────────────────
    if cfg.jira:
        jira_client = JiraClient(jira_session, jira_prof.base_url)
        # feature_name included for the same reason page_title above is --
        # cr_id alone (e.g. "CHG-001") is scoped per feature's own tasks.md
        # counter, not globally unique across the project. Without it here,
        # two features' own "CHG-001" would resolve to the SAME Jira ticket
        # via this label lookup -- not just a display collision like the
        # summary text below, but one feature's CR review silently reusing
        # (and overwriting the fields of) an unrelated feature's ticket.
        idempotency_label = f"sdd-cr:{feature_name}:{cr_id.lower()}"
        cr_project_key = cfg.jira.key_for("cr")
        existing = jira_client.find_by_label(cr_project_key, idempotency_label)

        # So this CR review ticket nests under the same Epic every other
        # ticket for this feature does -- previously this was the only
        # Jira issue type sdd ever created with no parent link at all
        # (Epic/Story/Task/review tickets all link up; this one just sat
        # standalone in the project). Never blocks the review submission
        # -- _ensure_epic prints a warning and returns None on failure.
        from sdd.commands.review import _ensure_epic

        confluence_base_url = cf_prof.base_url if cfg.confluence else None
        epic_key = _ensure_epic(
            jira_client, cfg.jira, feature_name, confluence_base_url
        )

        reviewer_id = reviewer or getattr(cfg, "cr_reviewer", None)

        desc_text = (
            f"Please review Change Request {cr_id}.\n\n"
            f"Summary: {cr_summary}\n\n"
            + (f"Confluence: {page_url}\n\n" if page_url else "")
            + "To APPROVE: set task to Done and comment 'Approved'.\n"
            "To REQUEST CHANGES: add comments and leave the task open."
        )
        fields: dict = {
            "project": {"key": cr_project_key},
            "issuetype": {"name": cfg.jira.issue_type_for("cr")},
            "summary": f"Review: {project_name} / {feature_name} — {cr_id}",
            # cfg.jira.labels (base_fields.labels, e.g. "sdd-generated") is
            # applied here the same way _upsert_issue() applies it to every
            # Epic/Story/Task/CHG issue -- CR review tasks aren't a
            # separate shape, they just don't route through _upsert_issue().
            "labels": cfg.jira.labels + ["sdd-cr", idempotency_label],
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": desc_text}],
                    }
                ],
            },
        }
        if reviewer_id:
            fields["assignee"] = {"accountId": reviewer_id}
        # Fixed team stamp (base_fields.team), same as every other issue
        # type -- no other custom_fields entries apply here.
        from sdd.commands.jira import _apply_team_field

        _apply_team_field(fields, cfg.jira, "cr")

        try:
            if existing:
                jira_client.update_issue(existing["key"], fields)
                task_key = existing["key"]
                console.print(
                    f"  [dim]·[/dim]   Jira task updated: [cyan]{task_key}[/cyan]"
                )
            else:
                result = jira_client.create_issue(fields)
                task_key = result["key"]
                console.print(
                    f"  [green]✓[/green]  Jira task created: [cyan]{task_key}[/cyan]"
                )
            if epic_key:
                from sdd.commands.jira import _warn_parent_link_failed

                try:
                    jira_client.set_parent(
                        task_key, epic_key, cfg.jira.parent_field_for("cr")
                    )
                except Exception as e:
                    _warn_parent_link_failed(
                        jira_client, task_key, epic_key, cr_project_key, e
                    )
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
@click.option("--cr", required=True)
@click.option("--profile", default=None)
@click.option(
    "--feature", default=None, help="Feature name (default: from manifest.yml)"
)
def cr_check(cr, profile, feature):
    """Check approval status of a CR in Jira.
    Exit codes: 0=approved 1=needs-revision 2=pending 3=not-submitted.
    """
    cr_id = cr.upper()
    console.print()

    try:
        cfg = load_integrations()
        prof, session = load_jira_session(cfg, profile)
    except Exception as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)

    if not cfg.jira:
        console.print("  [red]✗  No jira: section in integrations.yml[/red]")
        raise SystemExit(1)

    manifest = read_manifest() or {}
    proj = manifest.get("project") or {}
    feature_name = feature or proj.get("feature", "")

    client = JiraClient(session, prof.base_url)
    # Must match cr_submit's idempotency_label exactly (feature-qualified) --
    # otherwise this would never find the ticket cr_submit actually created.
    issue = client.find_by_label(
        cfg.jira.key_for("cr"), f"sdd-cr:{feature_name}:{cr_id.lower()}"
    )

    if not issue:
        console.print(f"  [dim]·  {cr_id} — NOT SUBMITTED[/dim]")
        console.print(f"     Run [cyan]sdd cr submit --cr {cr_id}[/cyan] first.")
        console.print()
        raise SystemExit(3)

    jira_status = issue.get("fields", {}).get("status", {}).get("name", "")
    comments = client.get_comments(issue["key"])

    approved_statuses = cfg.approved_statuses
    approved_keywords = cfg.approved_keywords

    if jira_status in approved_statuses:
        console.print(
            f"  [green]✓  {cr_id} — APPROVED[/green]  [dim](Jira status: {jira_status})[/dim]"
        )
        console.print()
        raise SystemExit(0)

    for c in comments:
        body = c.get("body", "")
        text = (
            body
            if isinstance(body, str)
            else " ".join(n.get("text", "") for n in _walk_adf(body))
        )
        if any(kw in text.lower() for kw in approved_keywords):
            console.print(
                f"  [green]✓  {cr_id} — APPROVED[/green]  [dim](via comment keyword)[/dim]"
            )
            console.print()
            raise SystemExit(0)

    if comments:
        console.print(f"  [yellow]✗  {cr_id} — NEEDS REVISION[/yellow]")
        console.print()
        console.print("  [bold]Review comments:[/bold]")
        for c in comments:
            author = (c.get("author") or {}).get("displayName", "?")
            body = c.get("body", "")
            text = (
                body
                if isinstance(body, str)
                else " ".join(n.get("text", "") for n in _walk_adf(body))
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
