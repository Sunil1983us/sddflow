from __future__ import annotations
from datetime import date
from pathlib import Path
import json
import re
import yaml
import click
from rich.console import Console

from sdd.utils.atlassian_auth import load_profile, build_session
from sdd.utils.integrations import load_integrations, IntegrationsConfig
from sdd.utils.jira_client import JiraClient
from sdd.utils.confluence_client import ConfluenceClient
from sdd.utils.md_to_cf import md_to_storage
from sdd.utils.manifest import read_manifest
from sdd.utils.status import persona_for
from sdd.utils.validate import resolve_doc_path, LIVING_SERVICE_DOCS
from sdd.utils.dashboard_comments import unacknowledged, acknowledge

console = Console()

_LOCAL_APPROVALS_FILE = Path(".specify") / ".local-approvals.yml"


# ── Local approval record (fallback when Jira not configured) ─────────────────

def _load_local_approvals() -> dict:
    if _LOCAL_APPROVALS_FILE.exists():
        return yaml.safe_load(_LOCAL_APPROVALS_FILE.read_text()) or {}
    return {}


def _save_local_approval(doc: str, approved_by: str, note: str = "") -> None:
    approvals = _load_local_approvals()
    approvals[doc] = {
        "approved_by": approved_by,
        "approved_at": str(date.today()),
        "note":        note,
    }
    _LOCAL_APPROVALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LOCAL_APPROVALS_FILE.write_text(
        "# Local approval record — used when Jira is not configured\n"
        "# Written by `sdd review approve --local` or AI fallback flow\n"
        + yaml.dump(approvals, default_flow_style=False)
    )


def _is_locally_approved(doc: str) -> bool:
    return doc in _load_local_approvals()


def _doc_md_path(doc: str, feature: str | None) -> Path | None:
    """Resolve the on-disk path for a doc key, or None if unresolvable.

    Living/service-level docs (data-model, security-design, api-spec) resolve
    to .specify/service/{doc}.md regardless of feature. Everything else
    resolves to .specify/features/{feature}/{doc}.md."""
    if doc in LIVING_SERVICE_DOCS:
        return resolve_doc_path(doc, "")
    manifest     = read_manifest() or {}
    proj         = manifest.get("project") or {}
    feature_name = feature or proj.get("feature", "")
    if not feature_name:
        return None
    try:
        return resolve_doc_path(doc, feature_name)
    except ValueError:
        return None


def _mark_approvals_table(text: str, date_str: str) -> str:
    """Flip every 'Pending' row inside the '## Approvals' section to
    'Approved', filling the Date column. Scoped to that section only — a
    coincidental 'Pending' cell anywhere else in the doc is left alone.

    Local-mode approval records a single approver for the whole document
    (see _save_local_approval), not one per RACI row, so every Pending row
    is flipped together — matching the document-level 'Status: Approved'
    header rather than trying to attribute individual rows to reviewers
    the CLI/dashboard were never told about."""
    heading = re.search(r"^## Approvals\s*$", text, flags=re.IGNORECASE | re.MULTILINE)
    if not heading:
        return text
    start = heading.end()
    next_heading = re.search(r"^## ", text[start:], flags=re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    section = text[start:end]
    new_section = re.sub(
        r"^\|([^|\n]*)\|\s*Pending\s*\|[^|\n]*\|[ \t]*$",
        lambda m: f"|{m.group(1)}| Approved | {date_str} |",
        section,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    return text[:start] + new_section + text[end:]


def _mark_md_approved(md_path: Path) -> bool:
    """Flip the document header to 'Status: Approved' and fill any
    'Pending' rows in the '## Approvals' table with today's date.

    Handles the pre-approval statuses case-insensitively: Draft (most docs)
    and Proposed (ADR lifecycle). Returns True if the file was changed by
    either edit, False if both were already up to date. This is the safety
    net for direct CLI/dashboard usage (the AI approval flow normally does
    both edits itself in chat) — running it again also self-heals a doc
    whose header was flipped before this function updated the Approvals
    table too."""
    text = md_path.read_text()
    new  = re.sub(r"Status:\s*(Draft|Proposed)\b", "Status: Approved",
                  text, count=1, flags=re.IGNORECASE)
    new  = _mark_approvals_table(new, str(date.today()))
    if new == text:
        return False
    md_path.write_text(new)
    return True


def _push_doc_page(doc: str, md_path: Path, feature_name: str) -> str | None:
    """Upsert the document's Confluence page so it reflects the approved .md.

    Returns the page title on success, or None when Confluence is not
    configured. Raises on push errors — callers decide how fatal that is.
    Page title resolution matches `sdd review submit`: document_reviews entry
    first, then the confluence page_map, then a sensible default."""
    try:
        cfg = load_integrations()
    except FileNotFoundError:
        return None
    if not cfg.confluence:
        return None

    manifest     = read_manifest() or {}
    proj         = manifest.get("project") or {}
    project_name = proj.get("name", "Project")

    if doc in cfg.document_reviews:
        title = cfg.document_reviews[doc].confluence_page
    else:
        title = cfg.confluence.page_map.get(doc, f"{{project}} — {doc.upper()}")
    # {feature} must always be substituted, not just {project} -- Confluence
    # enforces title uniqueness per SPACE, so two features pushing the same
    # doc type without {feature} in the title would silently overwrite each
    # other's page (this was the exact bug fixed for confluence.py's
    # page_map templates; document_reviews.confluence_page had the same gap).
    title = title.replace("{project}", project_name).replace("{feature}", feature_name)

    prof      = load_profile(cfg.profile)
    session   = build_session(prof)
    cf_client = ConfluenceClient(session, prof.base_url)
    body_html, attachments, diagram_warnings = md_to_storage(md_path.read_text(), cfg.confluence.diagrams)
    from sdd.commands.confluence import resolve_doc_parent_id, upload_diagram_attachments
    parent_id = resolve_doc_parent_id(cf_client, cfg.confluence, project_name, feature_name, doc)
    page, _created = cf_client.upsert_page(
        cfg.confluence.space_key, title, body_html, parent_id,
    )
    upload_diagram_attachments(cf_client, page["id"], attachments)
    for w in diagram_warnings:
        console.print(f"  [yellow]!  {w}[/yellow]")
    return title


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

def _print_local_comments_if_any(doc: str, feature_name: str) -> bool:
    """Pure-local-mode fallback for `sdd review check` when no jira: section
    exists to poll: dashboard comments have no external ticket to check, so
    print any not yet acknowledged (see dashboard_comments.py) in the same
    shape as the Jira NEEDS_REVISION branch. Returns True if any were
    printed (caller should exit 1), False otherwise (caller falls through
    to its existing NOT SUBMITTED message)."""
    comments = unacknowledged(feature_name, doc)
    if not comments:
        return False
    console.print(f"  [yellow]✗  {doc.upper()} — NEEDS REVISION[/yellow]  [dim](local dashboard comments)[/dim]")
    console.print()
    console.print("  [bold]Review comments:[/bold]")
    console.print()
    for c in comments:
        console.print(f"  [cyan]{c.get('by', 'Unknown')}[/cyan]  [dim]{c.get('at', '')[:10]}[/dim]")
        for line in c.get("text", "").splitlines():
            console.print(f"  {line}")
        console.print()
    return True


def _get_review_status(
    doc_key: str,
    client: JiraClient,
    project_key: str,
    cfg: IntegrationsConfig,
    feature_name: str,
) -> tuple[str, list[dict]]:
    """Return (status, comments).
    status: APPROVED | NEEDS_REVISION | PENDING | NOT_SUBMITTED

    Label is feature-qualified — must match the label `review_submit` writes,
    or a submitted review would never be found again.
    """
    issue = client.find_by_label(project_key, f"sdd-doc:{feature_name}:{doc_key}")
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
    feature_name: str,
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
    status, _ = _get_review_status(pred_key, client, cfg.jira.key_for("review"), cfg, feature_name)
    return (status == "APPROVED"), (None if status == "APPROVED" else pred_key)


def _record_confluence_draft_link(doc: str, page: dict, page_title: str) -> None:
    """`sdd review submit` is now the only step needed to get a document in
    front of both stakeholders (Confluence) and the formal reviewer (Jira)
    -- there is no separate "draft first, submit later" stage. Recording
    this page in the same drafts file `sdd confluence draft` uses means
    `sdd confluence pull --doc {doc}` still works afterward if the user
    wants to pull in edits/comments left on this page."""
    from sdd.commands.confluence import _load_drafts, _save_drafts
    drafts = _load_drafts()
    drafts[doc] = {"page_id": page.get("id", ""), "title": page_title}
    _save_drafts(drafts)


_REVIEW_LINKS_FILE = Path(".specify") / ".jira-review-links.json"


def _load_review_links() -> dict:
    if _REVIEW_LINKS_FILE.exists():
        return json.loads(_REVIEW_LINKS_FILE.read_text())
    return {}


def _save_review_links(links: dict) -> None:
    _REVIEW_LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _REVIEW_LINKS_FILE.write_text(json.dumps(links, indent=2))


def _record_review_link(doc: str, issue_key: str) -> None:
    """Persist the review-gate Jira ticket's key locally, mirroring
    _record_confluence_draft_link's pattern -- the dashboard's per-document
    Jira pill previously had no local fallback at all (unlike Confluence's,
    which reads .confluence-drafts.json), so it stayed blank until the
    user manually clicked "Check Jira/Confluence review links". Same
    not-feature-scoped limitation as that file: one entry per doc key,
    last feature to submit/apply wins on a multi-feature project -- the
    live /api/review-links check is still what's authoritative."""
    links = _load_review_links()
    links[doc] = {"key": issue_key}
    _save_review_links(links)


def _ensure_epic(jira_client: JiraClient, jira_cfg, feature_name: str) -> str | None:
    """Create the Feature/Epic container if it doesn't already exist yet,
    using the same content and idempotency label `sdd jira push` uses — so a
    review ticket submitted before any dev Story/Task exists still lands
    under the same Epic those will use later. Business Objectives are
    already available at this point since BRD (the first document
    reviewed) is always drafted before its own review ticket is submitted.
    Never blocks the review submission — prints a warning and returns None
    if Epic creation/lookup fails for any reason."""
    from sdd.commands.jira import _upsert_issue, feature_extra_fields
    from sdd.utils.validate import safe_feature_path

    try:
        features_dir = safe_feature_path(Path(".specify") / "features", feature_name)
        extra = feature_extra_fields(features_dir, jira_cfg, feature_name)
        h = jira_cfg.issue_hierarchy
        key, _ = _upsert_issue(
            jira_client, jira_cfg.key_for("feature"), h["feature"], feature_name,
            extra, f"sdd-feature:{feature_name}", jira_cfg.labels,
        )
        return key
    except Exception as e:
        console.print(
            f"  [yellow]!  Could not create/find the Epic — review ticket "
            f"will not have a parent link ({e})[/yellow]"
        )
        return None


def _link_review_story_to_epic(jira_client: JiraClient, story_key: str,
                                epic_key: str, jira_cfg) -> None:
    """Best-effort: parent the review ticket under the Feature/Epic. Never
    blocks the review submission — the ticket itself was already created
    successfully. Reuses jira.py's _warn_parent_link_failed rather than a
    silent except/pass, so a failure (e.g. a company-managed Jira project
    needing the Epic Link custom field instead of "parent") is diagnosable
    instead of vanishing with no trace."""
    from sdd.commands.jira import _warn_parent_link_failed
    try:
        jira_client.set_parent(story_key, epic_key, jira_cfg.parent_field_for("review"))
    except Exception as e:
        _warn_parent_link_failed(jira_client, story_key, epic_key, jira_cfg.key_for("review"), e)


# ── Command group ──────────────────────────────────────────────────────────────

@click.group()
def review_command():
    """Document-level review gates — submit, check, apply, status."""


# ── sdd review submit ──────────────────────────────────────────────────────────

@review_command.command("submit")
@click.option("--doc",     required=True,
              help="Document key: brd, use-cases, srd, design (unified) / arch, hld, adr (separate), lld, tasks, runbook, release")
@click.option("--profile", default=None)
@click.option("--feature", default=None)
def review_submit(doc, profile, feature):
    """Push a document to Confluence and create a Jira review story for it."""
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
    ok, blocking = _check_predecessor(doc, cfg, jira_client, feature_name)
    if not ok:
        console.print(f"  [red]✗  Cannot submit {doc.upper()} — {blocking.upper()} is not yet approved.[/red]")
        console.print(f"     Run [cyan]sdd review check --doc {blocking}[/cyan] to see its status.")
        raise SystemExit(1)

    # ── Push to Confluence ────────────────────────────────────────────────────
    try:
        md_path = resolve_doc_path(doc, feature_name)
    except ValueError as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)
    if not md_path.exists():
        console.print(f"  [red]✗  {md_path} not found — run the SDD command that generates it first[/red]")
        raise SystemExit(1)

    page_title = doc_cfg.confluence_page.replace("{project}", project_name).replace("{feature}", feature_name)
    body_html, attachments, diagram_warnings = md_to_storage(md_path.read_text(), cfg.confluence.diagrams)
    from sdd.commands.confluence import resolve_doc_parent_id, upload_diagram_attachments
    parent_id = resolve_doc_parent_id(cf_client, cfg.confluence, project_name, feature_name, doc)
    page, created = cf_client.upsert_page(
        cfg.confluence.space_key, page_title, body_html, parent_id,
    )
    upload_diagram_attachments(cf_client, page["id"], attachments)
    page_url = f"{prof.base_url}/wiki{page.get('_links', {}).get('webui', '')}"
    action   = "[green]created[/green]" if created else "[dim]updated[/dim]"
    console.print(f"  {action}  Confluence: [cyan]{page_title}[/cyan]")
    console.print(f"          {page_url}")
    for w in diagram_warnings:
        console.print(f"          [yellow]!  {w}[/yellow]")

    _record_confluence_draft_link(doc, page, page_title)

    # ── Ensure a Feature/Epic exists ──────────────────────────────────────────
    # So every review ticket -- and later every dev Story/Task from
    # `sdd jira push` -- nests under one place in Jira. Self-bootstrapping
    # here (rather than requiring a separate manual step) works because
    # BRD is always the first document reviewed, and its Business
    # Objectives are already written the moment /specify-brd finishes --
    # well before this review ticket exists to need a parent.
    epic_key = _ensure_epic(jira_client, cfg.jira, feature_name)

    # ── Create / update Jira review story ─────────────────────────────────────
    # Issue type is "story" (not "task") so review tickets sit at the same
    # hierarchy level as dev Stories under the Epic -- Epic -> Story -> Task
    # throughout, review tickets included, not a separate shape.
    # Label is feature-qualified for the same reason Story/Task labels are
    # (see jira.py's _item_label): an un-qualified "sdd-doc:brd" would let
    # a second feature's BRD review submission find and silently overwrite
    # the first feature's review ticket.
    idempotency_label = f"sdd-doc:{feature_name}:{doc}"
    review_project_key = cfg.jira.key_for("review")
    existing          = jira_client.find_by_label(review_project_key, idempotency_label)
    story_summary     = f"Review: {project_name} — {doc.upper()}"
    desc_text = (
        f"Please review the {doc.upper()} document.\n\n"
        f"Confluence: {page_url}\n\n"
        f"To APPROVE: set status to Done and comment 'Approved'.\n"
        f"To REQUEST CHANGES: add review comments and leave it open."
    )
    fields: dict = {
        "project":     {"key": review_project_key},
        "issuetype":   {"name": cfg.jira.issue_hierarchy.get("story", "Story")},
        "summary":     story_summary,
        # cfg.jira.labels (base_fields.labels, e.g. "sdd-generated") is
        # applied here the same way _upsert_issue() applies it to every
        # Epic/Story/Task/CHG issue -- review tickets aren't a separate
        # shape, they just don't route through _upsert_issue().
        "labels":      cfg.jira.labels + ["sdd-review", idempotency_label],
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
    # Fixed team stamp (base_fields.team), same as every other issue type
    # -- no other custom_fields entries apply here (story_points/
    # acceptance_criteria/etc. have no meaning on a review ticket).
    from sdd.commands.jira import _apply_team_field
    _apply_team_field(fields, cfg.jira, "review")

    if existing:
        jira_client.update_issue(existing["key"], fields)
        story_key = existing["key"]
        console.print(f"  [dim]·[/dim]   Jira review story updated: [cyan]{story_key}[/cyan]")
    else:
        result    = jira_client.create_issue(fields)
        story_key = result["key"]
        console.print(f"  [green]✓[/green]  Jira review story created: [cyan]{story_key}[/cyan]")

    _record_review_link(doc, story_key)

    if epic_key:
        _link_review_story_to_epic(jira_client, story_key, epic_key, cfg.jira)

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
@click.option("--feature", default=None, help="Feature name (default: from manifest.yml)")
def review_check(doc, profile, feature):
    """Check review status. Exit codes: 0=approved 1=needs-revision 2=pending 3=not-submitted."""
    console.print()

    # ── Local approval fast-path (no Jira needed) ─────────────────────────────
    if _is_locally_approved(doc):
        rec = _load_local_approvals()[doc]
        console.print(
            f"  [green]✓  {doc.upper()} — APPROVED[/green]  "
            f"[dim](local — by {rec.get('approved_by', '?')} on {rec.get('approved_at', '?')})[/dim]"
        )
        console.print()
        raise SystemExit(0)

    manifest     = read_manifest() or {}
    proj         = manifest.get("project") or {}
    feature_name = feature or proj.get("feature", "")

    # ── Jira check ────────────────────────────────────────────────────────────
    try:
        cfg     = load_integrations()
        prof    = load_profile(profile or cfg.profile)
        session = build_session(prof)
    except Exception as e:
        if _print_local_comments_if_any(doc, feature_name):
            raise SystemExit(1)
        console.print(
            f"  [dim]·  {doc.upper()} — NOT SUBMITTED[/dim]\n"
            f"  [dim]   (Jira not configured; no local approval recorded)[/dim]\n"
            f"  [dim]   Run `sdd review approve --doc {doc} --local` after in-chat approval.[/dim]"
        )
        raise SystemExit(3)

    if not cfg.jira:
        if _print_local_comments_if_any(doc, feature_name):
            raise SystemExit(1)
        console.print(
            f"  [dim]·  {doc.upper()} — NOT SUBMITTED[/dim]\n"
            f"  [dim]   No jira: section in integrations.yml and no local approval recorded.[/dim]"
        )
        raise SystemExit(3)

    client  = JiraClient(session, prof.base_url)
    status, comments = _get_review_status(doc, client, cfg.jira.key_for("review"), cfg, feature_name)
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
            created = c.get("created", "")[:10]
            text   = _extract_text(c.get("body", ""))
            console.print(f"  [cyan]{author}[/cyan]  [dim]{created}[/dim]")
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


# ── sdd review comments ─────────────────────────────────────────────────────────

@review_command.command("comments")
@click.option("--doc",     required=True)
@click.option("--feature", default=None, help="Feature name (default: from manifest.yml)")
@click.option("--ack",     is_flag=True, default=False,
              help="Mark every comment currently on this doc as addressed")
def review_comments(doc, feature, ack):
    """Read (or acknowledge) dashboard-left review comments directly --
    the pure-local-mode path for feedback that has no Jira ticket to poll.
    `sdd review check` already calls into this when jira: isn't configured;
    this command exists for explicit/manual use and discoverability.

    Exit codes: 0=no unacknowledged comments (or --ack succeeded), 1=some found.
    """
    console.print()
    manifest     = read_manifest() or {}
    proj         = manifest.get("project") or {}
    feature_name = feature or proj.get("feature", "")

    if ack:
        acknowledge(feature_name, doc)
        console.print(f"  [green]✓[/green]  {doc.upper()} — comments acknowledged.")
        console.print()
        raise SystemExit(0)

    comments = unacknowledged(feature_name, doc)
    if not comments:
        console.print(f"  [dim]·  {doc.upper()} — no unacknowledged comments[/dim]")
        console.print()
        raise SystemExit(0)

    console.print(f"  [yellow]{len(comments)} unacknowledged comment(s) on {doc.upper()}[/yellow]")
    console.print()
    for c in comments:
        console.print(f"  [cyan]{c.get('by', 'Unknown')}[/cyan]  [dim]{c.get('at', '')[:10]}[/dim]")
        for line in c.get("text", "").splitlines():
            console.print(f"  {line}")
        console.print()
    console.print(f"  [dim]After addressing them: sdd review comments --doc {doc} --ack[/dim]")
    console.print()
    raise SystemExit(1)


# ── sdd review approve ─────────────────────────────────────────────────────────

@review_command.command("approve")
@click.option("--doc",      required=True,
              help="Document key: brd, use-cases, srd, design (unified) / arch, hld, adr (separate), lld, ...")
@click.option("--local",    is_flag=True, required=True,
              help="Write a local approval record (fallback when Jira is not configured)")
@click.option("--by",       default="chat",
              help="Who approved — defaults to 'chat'")
@click.option("--note",     default="",
              help="Optional note (e.g. 'approved in chat session')")
@click.option("--feature",  default=None,
              help="Feature name (default: from manifest.yml)")
@click.option("--no-confluence", is_flag=True, default=False,
              help="Skip the Confluence page update even if confluence: is configured")
def review_approve(doc, local, by, note, feature, no_confluence):
    """Record a local approval for a document (used when Jira is not configured).

    The AI calls this automatically after the user says 'approved' in chat
    and sdd review submit is not available. This unblocks the next command.

    Also marks the document header 'Status: Approved' (if the AI has not
    already) and, when a confluence: section exists in integrations.yml,
    updates the document's existing Confluence page so it matches the
    approved .md. A Confluence failure never blocks the approval itself.

    Example (AI runs this):
        sdd review approve --doc brd --local --by "Product Owner" --note "approved in chat"
    """
    if not local:
        console.print("  [red]✗  Only --local approvals are supported by this command.[/red]")
        raise SystemExit(1)

    _save_local_approval(doc, by, note or "approved in chat session")

    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print(f"  [green]✓  {doc.upper()} — local approval recorded[/green]")
    console.print(f"  By    : [cyan]{by}[/cyan]")
    console.print(f"  Saved : {_LOCAL_APPROVALS_FILE}")

    # ── Mark the .md approved (safety net — AI flow usually did this) ────────
    md_path = _doc_md_path(doc, feature)
    if md_path and md_path.exists():
        if _mark_md_approved(md_path):
            console.print(f"  [green]✓[/green]  {md_path} — header set to Status: Approved")
        # ── Mirror the approved doc to its Confluence page ────────────────────
        if no_confluence:
            console.print("  [dim]·  Confluence update skipped (--no-confluence)[/dim]")
        else:
            try:
                manifest     = read_manifest() or {}
                feature_name = feature or (manifest.get("project") or {}).get("feature", "")
                title = _push_doc_page(doc, md_path, feature_name)
                if title:
                    console.print(f"  [green]✓[/green]  Confluence page updated: [cyan]{title}[/cyan]")
                else:
                    console.print("  [dim]·  Confluence not configured — page not updated[/dim]")
            except Exception as e:
                console.print(
                    f"  [yellow]!  Approval recorded, but the Confluence update failed: {e}[/yellow]\n"
                    f"     Re-try with: [cyan]sdd confluence push --doc {doc}[/cyan]"
                )
    else:
        console.print(
            f"  [dim]·  {doc}.md not found under .specify/features/ — "
            f"header + Confluence steps skipped[/dim]"
        )

    console.print()
    console.print("  [dim]sdd review check will now return exit 0 for this document.[/dim]")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()


# ── sdd review apply ───────────────────────────────────────────────────────────

@review_command.command("apply")
@click.option("--doc",     required=True)
@click.option("--profile", default=None)
@click.option("--feature", default=None)
def review_apply(doc, profile, feature):
    """After updating a document, re-push to Confluence and notify the
    reviewer in Jira -- or, in pure local mode (neither configured),
    acknowledge dashboard comments as addressed."""
    console.print()
    manifest     = read_manifest() or {}
    proj         = manifest.get("project") or {}
    feature_name = feature or proj.get("feature", "")

    try:
        cfg     = load_integrations()
        prof    = load_profile(profile or cfg.profile)
        session = build_session(prof)
    except Exception as e:
        # No integrations.yml at all -- still acknowledge any local
        # dashboard comments so `sdd review check` stops repeating them.
        acknowledge(feature_name, doc)
        console.print(
            f"  [green]✓[/green]  {doc.upper()} updated — local review comments acknowledged.\n"
            f"  [dim]   (No integrations.yml — nothing to push to Confluence/Jira.)[/dim]"
        )
        console.print()
        return

    if not cfg.jira and not cfg.confluence:
        acknowledge(feature_name, doc)
        console.print(
            f"  [green]✓[/green]  {doc.upper()} updated — local review comments acknowledged.\n"
            f"  [dim]   sdd review check will no longer repeat them for this round.[/dim]"
        )
        console.print()
        return

    if not cfg.jira or not cfg.confluence:
        console.print("  [red]✗  Both jira: and confluence: required in integrations.yml[/red]")
        raise SystemExit(1)

    doc_cfg = cfg.document_reviews.get(doc)
    if not doc_cfg:
        console.print(f"  [red]✗  '{doc}' not found in document_reviews[/red]")
        raise SystemExit(1)

    project_name = proj.get("name", "Project")

    jira_client = JiraClient(session, prof.base_url)
    cf_client   = ConfluenceClient(session, prof.base_url)

    # Re-push updated doc
    try:
        md_path = resolve_doc_path(doc, feature_name)
    except ValueError as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)
    page_url     = ""
    if md_path.exists():
        page_title = doc_cfg.confluence_page.replace("{project}", project_name).replace("{feature}", feature_name)
        body_html, attachments, diagram_warnings = md_to_storage(md_path.read_text(), cfg.confluence.diagrams)
        from sdd.commands.confluence import resolve_doc_parent_id, upload_diagram_attachments
        parent_id = resolve_doc_parent_id(cf_client, cfg.confluence, project_name, feature_name, doc)
        page, _    = cf_client.upsert_page(
            cfg.confluence.space_key, page_title, body_html, parent_id,
        )
        upload_diagram_attachments(cf_client, page["id"], attachments)
        page_url = f"{prof.base_url}/wiki{page.get('_links', {}).get('webui', '')}"
        console.print(f"  [green]✓[/green]  Confluence updated: [cyan]{page_title}[/cyan]")
        for w in diagram_warnings:
            console.print(f"  [yellow]!  {w}[/yellow]")
    else:
        console.print(f"  [dim]·[/dim]  {md_path} not found — skipping Confluence update")

    # Notify reviewer on Jira
    issue = jira_client.find_by_label(cfg.jira.key_for("review"), f"sdd-doc:{feature_name}:{doc}")
    if issue:
        msg = f"Document updated per review comments. Please re-review: {page_url}"
        jira_client.add_comment(issue["key"], msg)
        console.print(f"  [green]✓[/green]  Reviewer notified on [cyan]{issue['key']}[/cyan]")
        _record_review_link(doc, issue["key"])
    else:
        console.print(f"  [yellow]·[/yellow]  No Jira review story found for {doc.upper()}")

    console.print()
    console.print(
        f"  [bold green]{doc.upper()} updated.[/bold green]  "
        f"Run [cyan]sdd review check --doc {doc}[/cyan] after the reviewer responds."
    )
    console.print()


# ── sdd review status ──────────────────────────────────────────────────────────

@review_command.command("status")
@click.option("--profile", default=None)
@click.option("--feature", default=None, help="Feature name (default: from manifest.yml)")
def review_status(profile, feature):
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

    manifest     = read_manifest() or {}
    proj         = manifest.get("project") or {}
    feature_name = feature or proj.get("feature", "")
    scope        = proj.get("scope")

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
                st, _ = _get_review_status(key, client, cfg.jira.key_for("review"), cfg, feature_name)
                all_statuses[key] = st
                if st == "APPROVED":
                    icon, label, style = "✓ ", "Approved",       "green"
                elif st == "NEEDS_REVISION":
                    icon, label, style = "✗ ", "Needs Revision",  "yellow"
                elif st == "PENDING":
                    icon, label, style = "⏳", "Pending",         "dim"
                else:
                    icon, label, style = "· ", "Not Submitted",   "dim"

            # A doc already Approved needs no owner hint, and one that's
            # Blocked isn't ready to be worked on yet (its predecessor
            # isn't approved) -- everything else (Not Submitted, Pending,
            # Needs Revision) is a real "ask this person" moment.
            ask_hint = ""
            if all_statuses[key] not in ("APPROVED", "BLOCKED"):
                persona = persona_for(key, feature_name, scope)
                if persona:
                    ask_hint = f"  [dim]· ask {persona['name']}[/dim]"

            console.print(
                f"    [{style}]{icon}  {key.upper():<10} {label:<18}[/{style}]"
                f"  [dim]{dc.reviewer_role}[/dim]{ask_hint}"
            )

    console.print()
