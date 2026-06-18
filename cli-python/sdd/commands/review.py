from __future__ import annotations
from pathlib import Path
import click
from rich.console import Console

from sdd.utils.atlassian_auth import load_profile, build_session
from sdd.utils.integrations import load_integrations, IntegrationsConfig
from sdd.utils.jira_client import JiraClient
from sdd.utils.confluence_client import ConfluenceClient
from sdd.utils.md_to_cf import md_to_storage
from sdd.utils.manifest import read_manifest

console = Console()


# ── Text extraction ────────────────────────────────────────────────────────────

def _extract_text(body) -> str:
    """Extract plain text from Jira ADF (Cloud) or string (Server/DC) comment body."""
    if isinstance(body, str):
        return body
    if isinstance(body, dict):
        texts: list[str] = []

        def walk(node: dict) -> None:
            if node.get("type") == "text":
                texts.append(node.get("text", ""))
            for child in node.get("content", []):
                walk(child)

        walk(body)
        return " ".join(texts)
    return ""


# ── Review status helpers ──────────────────────────────────────────────────────

def _get_review_status(
    doc_key: str,
    client: JiraClient,
    project_key: str,
    cfg: IntegrationsConfig,
) -> tuple[str, list[dict]]:
    """Return (status, comments).
    status: APPROVED | NEEDS_REVISION | PENDING | NOT_SUBMITTED
    """
    issue = client.find_by_label(project_key, f"sdd-doc:{doc_key}")
    if not issue:
        return "NOT_SUBMITTED", []

    jira_status = issue.get("fields", {}).get("status", {}).get("name", "")
    comments    = client.get_comments(issue["key"])

    if jira_status in cfg.approved_statuses:
        return "APPROVED", comments

    for c in comments:
        text = _extract_text(c.get("body", "")).lower()
        if any(kw in text for kw in cfg.approved_keywords):
            return "APPROVED", comments

    return ("NEEDS_REVISION" if comments else "PENDING"), comments


def _check_predecessor(
    doc_key: str,
    cfg: IntegrationsConfig,
    client: JiraClient,
) -> tuple[bool, str | None]:
    """Verify the previous doc in this phase's sequence is approved.
    Returns (ok, blocking_doc_key).
    """
    if not cfg.jira:
        return True, None
    this = cfg.document_reviews[doc_key]
    preds = [
        k for k, v in cfg.document_reviews.items()
        if v.phase == this.phase and v.sequence == this.sequence - 1
    ]
    if not preds:
        return True, None
    pred_key = preds[0]
    status, _ = _get_review_status(pred_key, client, cfg.jira.project_key, cfg)
    return (status == "APPROVED"), (None if status == "APPROVED" else pred_key)


# ── Command group ──────────────────────────────────────────────────────────────

@click.group()
def review_command():
    """Document-level review gates — submit, check, apply, status."""


# ── sdd review submit ──────────────────────────────────────────────────────────

@review_command.command("submit")
@click.option("--doc",     required=True,
              help="Document key: brd, srd, arch, hld, lld, adr, tasks, runbook, release")
@click.option("--profile", default=None)
@click.option("--feature", default=None)
def review_submit(doc, profile, feature):
    """Push a document to Confluence and create a Jira review task for it."""
    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print(f"  [bold cyan]Review Submit[/bold cyan] — {doc.upper()}")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()

    try:
        cfg = load_integrations()
    except FileNotFoundError as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)

    if doc not in cfg.document_reviews:
        console.print(
            f"  [red]✗  '{doc}' not in document_reviews in integrations.yml[/red]\n"
            f"     Available: {', '.join(cfg.document_reviews)}"
        )
        raise SystemExit(1)

    if not cfg.jira or not cfg.confluence:
        console.print(
            "  [red]✗  Both jira: and confluence: sections required in integrations.yml[/red]"
        )
        raise SystemExit(1)

    try:
        prof    = load_profile(profile or cfg.profile)
        session = build_session(prof)
    except Exception as e:
        console.print(f"  [red]✗  Auth error: {e}[/red]")
        raise SystemExit(1)

    manifest     = read_manifest() or {}
    proj         = manifest.get("project") or {}
    project_name = proj.get("name", "Project")
    feature_name = feature or proj.get("feature", "")

    jira_client = JiraClient(session, prof.base_url)
    cf_client   = ConfluenceClient(session, prof.base_url)
    doc_cfg     = cfg.document_reviews[doc]

    # ── Sequence gate ─────────────────────────────────────────────────────────
    ok, blocking = _check_predecessor(doc, cfg, jira_client)
    if not ok:
        console.print(f"  [red]✗  Cannot submit {doc.upper()} — {blocking.upper()} is not yet approved.[/red]")
        console.print(f"     Run [cyan]sdd review check --doc {blocking}[/cyan] to see its status.")
        raise SystemExit(1)

    # ── Push to Confluence ────────────────────────────────────────────────────
    features_dir = Path(".specify") / "features" / feature_name
    md_path      = features_dir / f"{doc}.md"
    if not md_path.exists():
        console.print(f"  [red]✗  {md_path} not found — run the SDD command that generates it first[/red]")
        raise SystemExit(1)

    page_title = doc_cfg.confluence_page.replace("{project}", project_name)
    body_html  = md_to_storage(md_path.read_text())
    page, created = cf_client.upsert_page(
        cfg.confluence.space_key, page_title, body_html,
        cfg.confluence.parent_page_id,
    )
    page_url = f"{prof.base_url}/wiki{page.get('_links', {}).get('webui', '')}"
    action   = "[green]created[/green]" if created else "[dim]updated[/dim]"
    console.print(f"  {action}  Confluence: [cyan]{page_title}[/cyan]")
    console.print(f"          {page_url}")

    # ── Create / update Jira review task ──────────────────────────────────────
    idempotency_label = f"sdd-doc:{doc}"
    existing          = jira_client.find_by_label(cfg.jira.project_key, idempotency_label)
    task_summary      = f"Review: {project_name} — {doc.upper()}"
    desc_text = (
        f"Please review the {doc.upper()} document.\n\n"
        f"Confluence: {page_url}\n\n"
        f"To APPROVE: set task status to Done and comment 'Approved'.\n"
        f"To REQUEST CHANGES: add review comments and leave the task open."
    )
    fields: dict = {
        "project":     {"key": cfg.jira.project_key},
        "issuetype":   {"name": cfg.jira.issue_hierarchy.get("task", "Task")},
        "summary":     task_summary,
        "labels":      ["sdd-review", idempotency_label],
        "description": {
            "type": "doc", "version": 1,
            "content": [{"type": "paragraph", "content": [
                {"type": "text", "text": desc_text}
            ]}],
        },
    }
    if doc_cfg.reviewer_jira_user:
        # accountId for Cloud; use {"name": ...} for Server/DC if needed
        fields["assignee"] = {"accountId": doc_cfg.reviewer_jira_user}

    if existing:
        jira_client.update_issue(existing["key"], fields)
        task_key = existing["key"]
        console.print(f"  [dim]·[/dim]   Jira task updated: [cyan]{task_key}[/cyan]")
    else:
        result   = jira_client.create_issue(fields)
        task_key = result["key"]
        console.print(f"  [green]✓[/green]  Jira task created: [cyan]{task_key}[/cyan]")

    console.print(
        f"          Assigned to: [cyan]{doc_cfg.reviewer_role}[/cyan]"
        f"  [dim]({doc_cfg.reviewer_jira_user})[/dim]"
    )
    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print(f"  [bold green]{doc.upper()} submitted![/bold green]  "
                  f"Run [cyan]sdd review check --doc {doc}[/cyan] to poll the outcome.")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()


# ── sdd review check ───────────────────────────────────────────────────────────

@review_command.command("check")
@click.option("--doc",     required=True)
@click.option("--profile", default=None)
def review_check(doc, profile):
    """Check review status. Exit codes: 0=approved 1=needs-revision 2=pending 3=not-submitted."""
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

    client  = JiraClient(session, prof.base_url)
    status, comments = _get_review_status(doc, client, cfg.jira.project_key, cfg)
    doc_cfg = cfg.document_reviews.get(doc)
    role    = doc_cfg.reviewer_role if doc_cfg else "reviewer"

    if status == "APPROVED":
        console.print(f"  [green]✓  {doc.upper()} — APPROVED[/green]")
        console.print()
        raise SystemExit(0)

    if status == "NEEDS_REVISION":
        console.print(f"  [yellow]✗  {doc.upper()} — NEEDS REVISION[/yellow]")
        console.print()
        console.print("  [bold]Review comments:[/bold]")
        console.print()
        for c in comments:
            author = (c.get("author") or {}).get("displayName", "Unknown")
            date   = c.get("created", "")[:10]
            text   = _extract_text(c.get("body", ""))
            console.print(f"  [cyan]{author}[/cyan]  [dim]{date}[/dim]")
            for line in text.splitlines():
                console.print(f"  {line}")
            console.print()
        raise SystemExit(1)

    if status == "PENDING":
        console.print(f"  [dim]⏳  {doc.upper()} — PENDING[/dim]")
        console.print(f"     Waiting for [cyan]{role}[/cyan] to respond.")
        console.print()
        raise SystemExit(2)

    # NOT_SUBMITTED
    console.print(f"  [dim]·  {doc.upper()} — NOT SUBMITTED[/dim]")
    console.print(f"     Run [cyan]sdd review submit --doc {doc}[/cyan] first.")
    console.print()
    raise SystemExit(3)


# ── sdd review apply ───────────────────────────────────────────────────────────

@review_command.command("apply")
@click.option("--doc",     required=True)
@click.option("--profile", default=None)
@click.option("--feature", default=None)
def review_apply(doc, profile, feature):
    """After updating a document, re-push to Confluence and notify the reviewer in Jira."""
    console.print()
    try:
        cfg     = load_integrations()
        prof    = load_profile(profile or cfg.profile)
        session = build_session(prof)
    except Exception as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)

    if not cfg.jira or not cfg.confluence:
        console.print("  [red]✗  Both jira: and confluence: required in integrations.yml[/red]")
        raise SystemExit(1)

    doc_cfg = cfg.document_reviews.get(doc)
    if not doc_cfg:
        console.print(f"  [red]✗  '{doc}' not found in document_reviews[/red]")
        raise SystemExit(1)

    manifest     = read_manifest() or {}
    proj         = manifest.get("project") or {}
    project_name = proj.get("name", "Project")
    feature_name = feature or proj.get("feature", "")

    jira_client = JiraClient(session, prof.base_url)
    cf_client   = ConfluenceClient(session, prof.base_url)

    # Re-push updated doc
    features_dir = Path(".specify") / "features" / feature_name
    md_path      = features_dir / f"{doc}.md"
    page_url     = ""
    if md_path.exists():
        page_title = doc_cfg.confluence_page.replace("{project}", project_name)
        body_html  = md_to_storage(md_path.read_text())
        page, _    = cf_client.upsert_page(
            cfg.confluence.space_key, page_title, body_html,
            cfg.confluence.parent_page_id,
        )
        page_url = f"{prof.base_url}/wiki{page.get('_links', {}).get('webui', '')}"
        console.print(f"  [green]✓[/green]  Confluence updated: [cyan]{page_title}[/cyan]")
    else:
        console.print(f"  [dim]·[/dim]  {md_path} not found — skipping Confluence update")

    # Notify reviewer on Jira
    issue = jira_client.find_by_label(cfg.jira.project_key, f"sdd-doc:{doc}")
    if issue:
        msg = f"Document updated per review comments. Please re-review: {page_url}"
        jira_client.add_comment(issue["key"], msg)
        console.print(f"  [green]✓[/green]  Reviewer notified on [cyan]{issue['key']}[/cyan]")
    else:
        console.print(f"  [yellow]·[/yellow]  No Jira review task found for {doc.upper()}")

    console.print()
    console.print(
        f"  [bold green]{doc.upper()} updated.[/bold green]  "
        f"Run [cyan]sdd review check --doc {doc}[/cyan] after the reviewer responds."
    )
    console.print()


# ── sdd review status ──────────────────────────────────────────────────────────

@review_command.command("status")
@click.option("--profile", default=None)
def review_status(profile):
    """Show review state of all documents for the current project."""
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

    # Group by phase, sort by sequence
    _PHASE_ORDER = ["specify", "validate", "planning", "tasks", "release"]
    phases: dict[str, list] = {}
    for key, dc in cfg.document_reviews.items():
        phases.setdefault(dc.phase, []).append((key, dc))
    for ph in phases:
        phases[ph].sort(key=lambda x: x[1].sequence)

    all_statuses: dict[str, str] = {}
    ordered_phases = sorted(
        phases.keys(),
        key=lambda p: _PHASE_ORDER.index(p) if p in _PHASE_ORDER else 99,
    )

    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("  [bold cyan]Review Status[/bold cyan]")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")

    for phase in ordered_phases:
        console.print(f"\n  [bold]{phase.upper()} phase[/bold]")
        for key, dc in phases[phase]:
            preds = [
                k for k, v in cfg.document_reviews.items()
                if v.phase == phase and v.sequence == dc.sequence - 1
            ]
            pred_approved = all(all_statuses.get(p) == "APPROVED" for p in preds)

            if preds and not pred_approved:
                icon, label, style = "🔒", "Blocked", "dim"
                all_statuses[key] = "BLOCKED"
            else:
                st, _ = _get_review_status(key, client, cfg.jira.project_key, cfg)
                all_statuses[key] = st
                if st == "APPROVED":
                    icon, label, style = "✓ ", "Approved",       "green"
                elif st == "NEEDS_REVISION":
                    icon, label, style = "✗ ", "Needs Revision",  "yellow"
                elif st == "PENDING":
                    icon, label, style = "⏳", "Pending",         "dim"
                else:
                    icon, label, style = "· ", "Not Submitted",   "dim"

            console.print(
                f"    [{style}]{icon}  {key.upper():<10} {label:<18}[/{style}]"
                f"  [dim]{dc.reviewer_role}[/dim]"
            )

    console.print()
