from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import click
import yaml
from rich.console import Console

from sdd.utils.atlassian_auth import load_confluence_session, load_jira_session
from sdd.utils.atomic_write import atomic_write_text
from sdd.utils.confluence_client import ConfluenceClient
from sdd.utils.dashboard_comments import acknowledge, unacknowledged
from sdd.utils.integrations import (
    IntegrationsConfig,
    IntegrationsConfigError,
    load_integrations,
)
from sdd.utils.jira_client import JiraClient
from sdd.utils.manifest import read_manifest
from sdd.utils.md_to_cf import md_to_storage
from sdd.utils.status import persona_for
from sdd.utils.validate import PROJECT_SCOPED_DOCS, resolve_doc_path

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
        "approved_at": str(date.today()),  # noqa: DTZ011 -- local calendar date by design, not a UTC instant
        "note": note,
    }
    atomic_write_text(
        _LOCAL_APPROVALS_FILE,
        "# Local approval record — used when Jira is not configured\n"
        "# Written by `sdd review approve --local` or AI fallback flow\n"
        + yaml.dump(approvals, default_flow_style=False),
    )


def _is_locally_approved(doc: str) -> bool:
    return doc in _load_local_approvals()


def _doc_md_path(doc: str, feature: str | None) -> Path | None:
    """Resolve the on-disk path for a doc key, or None if unresolvable.

    "constitution", "runbook", and living/service-level docs (data-model,
    security-design, api-spec) resolve to a fixed path regardless of
    feature. Everything else resolves to .specify/features/{feature}/{doc}.md."""
    if doc in PROJECT_SCOPED_DOCS:
        return resolve_doc_path(doc, "")
    manifest = read_manifest() or {}
    proj = manifest.get("project") or {}
    feature_name = feature or proj.get("feature", "")
    if not feature_name:
        return None
    try:
        return resolve_doc_path(doc, feature_name)
    except ValueError:
        return None


def _mark_approvals_table(
    text: str,
    date_str: str,
    approver_name: str = "",
    role_filter: str | None = None,
) -> str:
    """Flip 'Pending' row(s) inside the '## Approvals' section to
    'Approved', filling the Date column and the Approver column with
    approver_name. Scoped to that section only — a coincidental 'Pending'
    cell anywhere else in the doc is left alone.

    Every current template's Approvals table is 4 columns -- 'Role |
    Approver | Status | Date' (verified against all 20 templates that
    have an Approvals section) -- not the 3-column 'Role | Status | Date'
    an earlier version of this regex assumed. That mismatch meant this
    function never matched a single real row: it silently no-opped on
    every document, including via the dashboard's "Approve" button
    (dashboard.py's _do_approve -> _mark_md_approved, called with no
    prior text edit) -- the Approvals table stayed 'Pending' forever
    under an 'Approved' Status header. Never caught because the old unit
    tests' own fixture invented the same wrong 3-column shape.

    role_filter=None (default): flip every Pending row, filling each with
    approver_name -- local-mode approval records a single approver for
    the whole document (see _save_local_approval), not one per RACI row,
    so every row is flipped together, matching the document-level
    'Status: Approved' header rather than trying to attribute individual
    rows to reviewers the CLI/dashboard were never told about.

    role_filter=<text> (jira mode, e.g. the Jira ticket's configured
    reviewer_role): only flip row(s) whose Role-column text contains
    role_filter (case-insensitive substring). Every other row is left
    Pending -- blanket-approving a Tech Lead/Stakeholder row on the
    strength of one Architect's Jira sign-off would misrepresent evidence
    nobody actually gave, same principle as validate.prompt.md's own
    per-item confirmation checkboxes. Falls back to flipping every row
    (role_filter effectively ignored) if it matches none of them -- a
    configured reviewer_role that doesn't appear in this doc's Approvals
    table at all is a config mismatch, not a reason to leave the table
    permanently stuck on Pending."""
    heading = re.search(r"^## Approvals\s*$", text, flags=re.IGNORECASE | re.MULTILINE)
    if not heading:
        return text
    start = heading.end()
    next_heading = re.search(r"^## ", text[start:], flags=re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    section = text[start:end]

    row_re = re.compile(
        r"^\|([^|\n]*)\|([^|\n]*)\|\s*Pending\s*\|([^|\n]*)\|[ \t]*$",
        flags=re.MULTILINE | re.IGNORECASE,
    )

    if role_filter and not row_re.search(section):
        role_filter = None  # no Approvals table at all here -- nothing to scope
    elif role_filter:
        needle = role_filter.casefold()
        if not any(needle in m.group(1).casefold() for m in row_re.finditer(section)):
            role_filter = None  # no row matches -- fall back to blanket flip

    def _flip(m: re.Match) -> str:
        role_text = m.group(1)
        if role_filter and role_filter.casefold() not in role_text.casefold():
            return m.group(0)  # not this row's evidence -- leave it Pending
        approver_cell = f" {approver_name} " if approver_name else " "
        return f"|{role_text}|{approver_cell}| Approved | {date_str} |"

    new_section = row_re.sub(_flip, section)
    return text[:start] + new_section + text[end:]


def _mark_md_approved(
    md_path: Path, approver_name: str = "", role_filter: str | None = None
) -> bool:
    """Flip the document header to 'Status: Approved' and fill 'Pending'
    row(s) in the '## Approvals' table with today's date and
    approver_name. See _mark_approvals_table's own docstring for
    approver_name/role_filter semantics (blanket flip vs role-scoped).

    Handles the pre-approval statuses case-insensitively: Draft (most docs)
    and Proposed (ADR lifecycle). Returns True if the file was changed by
    either edit, False if both were already up to date. This is the safety
    net for direct CLI/dashboard usage (the AI approval flow normally does
    both edits itself in chat) — running it again also self-heals a doc
    whose header was flipped before this function updated the Approvals
    table too.

    The header flip is scoped to the document's front matter (everything
    before the first '## ' section heading) -- every template's own
    '> Version: ... | Status: Draft | ...' line (or, for adr.md, '>
    Status: Proposed | ...') lives there, in the first few lines. This
    used to search/replace across the ENTIRE document unanchored, which
    matched -- and corrupted -- any content anywhere in the body
    containing the literal substring 'Status: Draft'/'Status: Proposed',
    not just the real header. Reported by a user: a data-model.md enum
    field written as 'RuleVersionStatus: DRAFT, SUBMITTED, PUBLISHED,
    RETIRED' (data-model.md's own template has no Status: header field
    at all -- see data-model-template.md -- so that enum line was the
    FIRST, and only, match in the whole document) got silently mangled
    into 'RuleVersionStatus: Approved, SUBMITTED, PUBLISHED, RETIRED'."""
    text = md_path.read_text()
    heading = re.search(r"^## ", text, flags=re.MULTILINE)
    front_matter_end = heading.start() if heading else len(text)
    front_matter = text[:front_matter_end]
    new_front_matter = re.sub(
        r"Status:\s*(Draft|Proposed)\b",
        "Status: Approved",
        front_matter,
        count=1,
        flags=re.IGNORECASE,
    )
    new = new_front_matter + text[front_matter_end:]
    new = _mark_approvals_table(  # noqa: DTZ011 -- local calendar date by design
        new, str(date.today()), approver_name=approver_name, role_filter=role_filter
    )
    if new == text:
        return False
    atomic_write_text(md_path, new)
    return True


def _mark_md_needs_revision(md_path: Path) -> bool:
    """Flip an Approved document's header back to a pre-approval status
    the moment its content changes post-approval -- e.g. /clarify patches
    an already-Approved document to apply a resolved item, or a
    reviewer's NEEDS REVISION feedback is being addressed. Called from
    `sdd review apply`, the single place every revision-driven prompt
    step already calls after re-saving a document, so this fires
    uniformly regardless of which command triggered the edit -- no
    per-prompt discipline required.

    Reverts to 'Proposed' for adr.md (its own lifecycle word) and
    'Draft' for everything else -- both are already recognized by
    _mark_md_approved's own regex (`Draft|Proposed` -> `Approved`), so
    the existing re-approval flow works unchanged on a reverted document
    with zero changes needed anywhere else.

    Scoped to front matter only, mirroring _mark_md_approved exactly and
    for the same corruption-safety reason -- see that function's
    docstring. Only flips when the current status is exactly 'Approved';
    a document still in Draft/Proposed (e.g. mid-review, addressing a
    NEEDS REVISION comment before its first approval) is left untouched
    -- there is nothing to revert for a document that was never approved
    in the first place. Returns True if the file was changed."""
    text = md_path.read_text()
    heading = re.search(r"^## ", text, flags=re.MULTILINE)
    front_matter_end = heading.start() if heading else len(text)
    front_matter = text[:front_matter_end]
    revert_to = "Proposed" if md_path.stem == "adr" else "Draft"
    new_front_matter = re.sub(
        r"Status:\s*Approved\b",
        f"Status: {revert_to}",
        front_matter,
        count=1,
        flags=re.IGNORECASE,
    )
    if new_front_matter == front_matter:
        return False
    new = new_front_matter + text[front_matter_end:]
    atomic_write_text(md_path, new)
    return True


def _jira_status_banner(issue_key: str, issue_url: str, status: str, role: str) -> str:
    """Confluence storage-format panel summarizing the Jira review ticket's
    link and current status, prepended to the page body on every push so a
    reviewer can see review state without leaving Confluence.

    Confluence's built-in panel macros are only "info", "tip", "note", and
    "warning" -- there is no "success" macro. Using an unregistered macro
    name renders as "Error loading the extension!" instead of the panel,
    which only became visible once a real document reached APPROVED (the
    PENDING/default "info" case was always valid)."""
    macro_type = {"APPROVED": "tip", "NEEDS_REVISION": "warning"}.get(status, "info")
    label = {
        "APPROVED": "Approved",
        "NEEDS_REVISION": "Needs Revision",
        "PENDING": "Pending review",
    }.get(status, status)
    return (
        f'<ac:structured-macro ac:name="{macro_type}">'
        f"<ac:rich-text-body><p>"
        f"<strong>Jira review:</strong> "
        f'<a href="{issue_url}">{issue_key}</a> — <strong>{label}</strong>'
        f" (assigned: {role})"
        f"</p></ac:rich-text-body>"
        f"</ac:structured-macro>"
    )


def _push_doc_page(
    doc: str, md_path: Path, feature_name: str
) -> tuple[str, str] | None:
    """Upsert the document's Confluence page so it reflects the current .md.

    Returns (page_title, page_url) on success, or None when Confluence is
    not configured. Raises on push errors — callers decide how fatal that
    is. Page title resolution matches `sdd review submit`: document_reviews
    entry first, then the confluence page_map, then a sensible default.

    When a Jira review ticket already exists for this doc (jira: configured
    and document_reviews has an entry for it), a status banner linking to
    that ticket is prepended to the page body -- this is what lets a
    reviewer see the Jira link + current status directly on Confluence
    instead of having to check Jira separately."""
    try:
        cfg = load_integrations()
    except (FileNotFoundError, IntegrationsConfigError):
        return None
    if not cfg.confluence:
        return None

    manifest = read_manifest() or {}
    proj = manifest.get("project") or {}
    project_name = proj.get("name", "Project")

    if doc == "constitution":
        # Project-wide, no document_reviews entry (amended via GATE-1, not
        # a Jira review ticket) -- must match confluence.py's
        # _resolve_page_title exactly, or `sdd review apply --doc
        # constitution` and `sdd confluence push --doc constitution` would
        # land on two different pages for the same document.
        title = "{project} — Constitution"
    elif doc in cfg.document_reviews:
        title = cfg.document_reviews[doc].confluence_page
    else:
        # No prior explicit template to preserve for a doc key that isn't
        # configured anywhere -- safe to include {feature} unconditionally
        # (see confluence.py's _resolve_page_title, same reasoning).
        title = cfg.confluence.page_map.get(
            doc, f"{{project}} — {{feature}} — {doc.upper()}"
        )
    # {feature} must always be substituted, not just {project} -- Confluence
    # enforces title uniqueness per SPACE, so two features pushing the same
    # doc type without {feature} in the title would silently overwrite each
    # other's page (this was the exact bug fixed for confluence.py's
    # page_map templates; document_reviews.confluence_page had the same gap).
    title = title.replace("{project}", project_name).replace("{feature}", feature_name)

    from sdd.commands.confluence import feature_collision_warning

    warning = feature_collision_warning(title, feature_name)
    if warning:
        # Non-blocking here (unlike sdd confluence push/draft's --force
        # gate) -- this helper is called from contexts with no CLI flag
        # surface of their own (the dashboard's HTTP approve endpoint
        # among them), so it can only warn, not refuse.
        console.print(f"  [yellow]⚠  {warning}[/yellow]")

    cf_prof, cf_session = load_confluence_session(cfg)
    cf_client = ConfluenceClient(cf_session, cf_prof.base_url)

    banner = ""
    if cfg.jira and doc in cfg.document_reviews:
        try:
            jira_prof, jira_session = load_jira_session(cfg)
            jira_client = JiraClient(jira_session, jira_prof.base_url)
            status, _, issue = _get_review_status(
                doc,
                jira_client,
                cfg.jira.key_for("review"),
                cfg,
                feature_name,
            )
            if issue:
                issue_url = f"{jira_prof.base_url}/browse/{issue['key']}"
                banner = _jira_status_banner(
                    issue["key"],
                    issue_url,
                    status,
                    cfg.document_reviews[doc].reviewer_role,
                )
        except Exception:  # noqa: S110 -- see comment above
            pass  # banner is a best-effort addition -- never blocks the page push itself

    body_html, attachments, diagram_warnings = md_to_storage(
        md_path.read_text(), cfg.confluence.diagrams
    )
    from sdd.commands.confluence import (
        resolve_doc_parent_id,
        upload_diagram_attachments,
    )

    parent_id = resolve_doc_parent_id(
        cf_client, cfg.confluence, project_name, feature_name, doc
    )
    page, _created = cf_client.upsert_page(
        cfg.confluence.space_key,
        title,
        banner + body_html,
        parent_id,
    )
    upload_diagram_attachments(cf_client, page["id"], attachments)
    for w in diagram_warnings:
        console.print(f"  [yellow]!  {w}[/yellow]")
    page_url = f"{cf_prof.base_url}/wiki{page.get('_links', {}).get('webui', '')}"
    return title, page_url


# ── Text extraction ────────────────────────────────────────────────────────────

_ADF_BLOCK_TYPES = {"paragraph", "heading", "codeBlock", "blockquote", "listItem"}


def _extract_text(body) -> str:
    """Extract plain text from Jira ADF (Cloud) or string (Server/DC) comment
    body, preserving line boundaries between block-level nodes as newlines.

    Jira's rich-text comment editor stores each line a user types as a
    SEPARATE paragraph node in the ADF tree, not one paragraph with embedded
    newlines -- joining every text run in the whole document with a single
    space (the previous behavior) collapsed a multi-line reply like
    pull-answers' "{doc}:NC-{NNN}: {answer}" format (one item per line) into
    one run-on line, breaking _ANSWER_LINE_RE's per-line matching entirely."""
    if isinstance(body, str):
        return body
    if isinstance(body, dict):
        lines: list[str] = []

        def walk_inline(node: dict, buf: list[str]) -> None:
            if node.get("type") == "text":
                buf.append(node.get("text", ""))
            elif node.get("type") == "hardBreak":
                buf.append("\n")
            for child in node.get("content", []):
                walk_inline(child, buf)

        def walk_block(node: dict) -> None:
            if node.get("type") in _ADF_BLOCK_TYPES:
                buf: list[str] = []
                walk_inline(node, buf)
                lines.append("".join(buf))
            else:
                for child in node.get("content", []):
                    walk_block(child)

        walk_block(body)
        return "\n".join(lines)
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
    console.print(
        f"  [yellow]✗  {doc.upper()} — NEEDS REVISION[/yellow]  [dim](local dashboard comments)[/dim]"
    )
    console.print()
    console.print("  [bold]Review comments:[/bold]")
    console.print()
    for c in comments:
        console.print(
            f"  [cyan]{c.get('by', 'Unknown')}[/cyan]  [dim]{c.get('at', '')[:10]}[/dim]"
        )
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
) -> tuple[str, list[dict], dict | None]:
    """Return (status, comments, issue).
    status: APPROVED | NEEDS_REVISION | PENDING | NOT_SUBMITTED
    issue is the raw Jira issue dict (or None if never submitted) -- callers
    that also need the issue key/link (e.g. the Confluence status banner)
    reuse this instead of a second find_by_label lookup.

    Label is feature-qualified — must match the label `review_submit` writes,
    or a submitted review would never be found again.
    """
    issue = client.find_by_label(project_key, f"sdd-doc:{feature_name}:{doc_key}")
    if not issue:
        return "NOT_SUBMITTED", [], None

    jira_status = issue.get("fields", {}).get("status", {}).get("name", "")
    comments = client.get_comments(issue["key"])

    if jira_status in cfg.approved_statuses:
        return "APPROVED", comments, issue

    for c in comments:
        text = _extract_text(c.get("body", "")).lower()
        if any(kw in text for kw in cfg.approved_keywords):
            return "APPROVED", comments, issue

    return ("NEEDS_REVISION" if comments else "PENDING"), comments, issue


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
        k
        for k, v in cfg.document_reviews.items()
        if v.phase == this.phase and v.sequence == this.sequence - 1
    ]
    if not preds:
        return True, None
    pred_key = preds[0]
    status, _, _ = _get_review_status(
        pred_key, client, cfg.jira.key_for("review"), cfg, feature_name
    )
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
    atomic_write_text(_REVIEW_LINKS_FILE, json.dumps(links, indent=2))


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


# ── Open-questions push/pull (blocked-doc Jira Q&A) ────────────────────────────
# When a document like validate.md is blocked on [NEEDS CLARIFICATION-NNN]
# markers in its source docs, `sdd review push-questions` lets a reviewer
# answer them via Jira/Confluence comments instead of waiting for direct
# chat/doc edits -- `sdd review pull-answers` reads those comments back and
# patches the answered markers directly into brd.md/use-cases.md/srd.md.

_OPEN_QUESTION_ROW_RE = re.compile(
    r"^\|\s*([a-zA-Z0-9_.-]+:NC-\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$",
    re.MULTILINE,
)
_ANSWER_LINE_RE = re.compile(
    r"^\s*([a-zA-Z0-9_.-]+):NC-(\d+)\s*:\s*(.+?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# validate.prompt.md tells the AI to cite each marker's doc as "{doc}:NC-{NNN}"
# but doesn't mandate an exact spelling -- a model writing the Locations
# column for use-cases.md has, in practice, abbreviated it "uc" (a reasonable
# guess, but resolve_doc_path's actual doc key is "use-cases", matching the
# filename). Normalize known abbreviations before ever calling
# resolve_doc_path with a doc-key parsed out of a location ID.
_DOC_KEY_ALIASES = {"uc": "use-cases", "usecases": "use-cases"}


def _normalize_doc_key(doc_key: str) -> str:
    return _DOC_KEY_ALIASES.get(doc_key.lower(), doc_key.lower())


def _parse_open_questions(doc_text: str) -> list[dict]:
    """Parse a blocked document's `| ID | Locations | Question |` table
    (see validate.prompt.md's §3a-BLOCKING format) into structured items.
    Tolerant of table-formatting drift across LLM runs -- anchors on the
    `{doc}:NC-{NNN}` ID pattern itself, not exact column headers.

    Each item's "locations" is every doc-qualified ID (e.g. "brd:NC-003")
    that a single answer should be applied to -- almost always just its
    own ID, but more than one when the same question was asked in more
    than one document."""
    items: list[dict] = []
    for m in _OPEN_QUESTION_ROW_RE.finditer(doc_text):
        primary_id, locations_raw, question = (
            m.group(1).strip(),
            m.group(2).strip(),
            m.group(3).strip(),
        )
        locations = [loc.strip() for loc in locations_raw.split(",") if loc.strip()]
        if primary_id not in locations:
            locations.append(primary_id)
        items.append({"id": primary_id, "locations": locations, "question": question})
    return items


def _parse_answers(comments: list[dict]) -> dict[str, str]:
    """Parse every Jira comment for lines like 'brd:NC-002: <answer>'.
    A later comment's answer for the same ID overrides an earlier one
    (a reviewer correcting themselves)."""
    answers: dict[str, str] = {}
    for c in comments:
        text = _extract_text(c.get("body", ""))
        for m in _ANSWER_LINE_RE.finditer(text):
            doc_key, nnn, answer = m.group(1).lower(), m.group(2), m.group(3)
            answers[f"{doc_key}:NC-{nnn}"] = answer
    return answers


def _bump_version_and_log(text: str, note: str) -> str:
    """Bump the `Version: X.Y` header to X.(Y+1) and append a row to
    `## Version History`, matching the same discipline every review-driven
    edit in this codebase uses (see specify-brd.prompt.md's Revision
    Logging). Best-effort: if either the Version header or a recognizable
    `## Version History` table isn't found, the text is returned unchanged
    rather than raising -- the marker replacement itself is what matters;
    this bookkeeping is a bonus that shouldn't block on template drift."""
    version_match = re.search(r"Version:\s*(\d+)\.(\d+)", text)
    if not version_match:
        return text
    major, minor = version_match.group(1), int(version_match.group(2)) + 1
    new_version = f"{major}.{minor}"
    text = (
        text[: version_match.start()]
        + f"Version: {new_version}"
        + text[version_match.end() :]
    )

    heading = re.search(
        r"^## Version History\s*$", text, flags=re.IGNORECASE | re.MULTILINE
    )
    if not heading:
        return text
    after = text[heading.end() :]
    sep_match = re.search(r"\n\|[-| ]+\|\s*\n", after)
    if not sep_match:
        return text
    insert_at = heading.end() + sep_match.end()
    row = f"| {new_version} | {date.today()} | Jira/Confluence | {note} | — |\n"  # noqa: DTZ011 -- local calendar date by design
    return text[:insert_at] + row + text[insert_at:]


def _patch_marker(md_path: Path, nnn: str, answer: str) -> bool:
    """Replace `[NEEDS CLARIFICATION-{nnn}: ...]` with the answer text in
    md_path, bumping its version + Version History. Returns True if a
    matching marker was found and patched, False otherwise (already
    resolved, or nnn doesn't exist in this file)."""
    if not md_path.exists():
        return False
    text = md_path.read_text()
    pattern = re.compile(r"\[NEEDS CLARIFICATION-" + re.escape(nnn) + r":\s*[^\]]*\]")
    if not pattern.search(text):
        return False
    new_text = pattern.sub(lambda _m: answer, text, count=1)
    new_text = _bump_version_and_log(
        new_text, f"NC-{nnn} resolved via Jira/Confluence comment"
    )
    atomic_write_text(md_path, new_text)
    return True


# ── clarify.md's own open items (AMB/GAP/CON/ASM/OQ/R) ─────────────────────────
# Unlike validate.md's [NEEDS CLARIFICATION-NNN] markers -- which cite OTHER
# documents (brd/srd/use-cases) via a `{doc}:NC-{NNN}` ID -- clarify.md's own
# ambiguities/gaps/conflicts/assumptions/open-questions/risks live entirely in
# clarify.md itself, tracked by its STATUS TABLE (see clarify-template.md)
# rather than an inline bracketed marker. push-questions/pull-answers only
# ever understood the NC-NNN scheme, so clarify.md could never be pushed to
# Jira for answers the way validate.md already could -- this second, parallel
# parse/patch pair gives it the same workflow.

_CLARIFY_ITEM_CODE = r"(?:AMB|GAP|CON|ASM|OQ|CF|R)-\d+"
_CLARIFY_STATUS_ROW_RE = re.compile(
    r"^\|\s*("
    + _CLARIFY_ITEM_CODE
    + r")\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*OPEN\s*\|\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_CLARIFY_ANSWER_LINE_RE = re.compile(
    r"^\s*clarify:(" + _CLARIFY_ITEM_CODE + r")\s*:\s*(.+?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_CLARIFY_FILL_RE = re.compile(r"\{FILL[^}]*\}")

# Terminal STATUS TABLE value per item-type prefix, matching the mapping
# clarify.prompt.md's own Step 2 uses ("match the item type"). ASM is not
# listed here -- it's CONFIRMED or CORRECTED depending on the answer itself
# (the template's own "Correct? Yes / No" framing), handled in
# _patch_clarify_item rather than a fixed lookup.
_CLARIFY_TERMINAL_STATUS = {
    "AMB": "RESOLVED",
    "GAP": "RESOLVED",
    "CON": "CORRECTED",
    "OQ": "DECIDED",
    "R": "RESOLVED",
}


def _clarify_item_block_text(doc_text: str, code: str) -> str | None:
    """Return the full body of a clarify.md item's own section (from its
    `### {code}: {Topic}` heading up to the next section break -- either a
    `---` divider between type-sections or the next `### ` item heading for
    consecutive same-type items), for posting as the Jira question text.
    Returns the whole block (Found in / Option A / Option B / etc, not just
    one field) since the 5 item types each label their key line
    differently and the reviewer needs full context regardless. None if no
    such heading exists in doc_text."""
    heading = re.search(r"^### " + re.escape(code) + r":.*$", doc_text, re.MULTILINE)
    if not heading:
        return None
    rest = doc_text[heading.end() :]
    end_match = re.search(r"\n---\s*\n|\n### ", rest)
    body = rest[: end_match.start()] if end_match else rest
    return (heading.group(0) + "\n" + body).strip()


def _parse_clarify_open_items(doc_text: str) -> list[dict]:
    """Parse clarify.md's STATUS TABLE for OPEN rows into the same
    {id, locations, question} shape _parse_open_questions returns, so
    push-questions/pull-answers can handle both marker schemes through the
    same downstream Jira/Confluence code. Every clarify item lives in
    clarify.md itself -- "locations" is always just the item's own ID,
    prefixed "clarify:" to match the {doc}:NC-{NNN} convention every
    answer-parsing/console-message call site already expects (e.g. the
    reviewer replies "clarify:AMB-001: <answer>", not "brd:NC-001: ...")."""
    items: list[dict] = []
    for m in _CLARIFY_STATUS_ROW_RE.finditer(doc_text):
        code = m.group(1).strip().upper()
        full_id = f"clarify:{code}"
        question = (
            _clarify_item_block_text(doc_text, code)
            or f"{m.group(2).strip()}: {m.group(3).strip()}"
        )
        items.append({"id": full_id, "locations": [full_id], "question": question})
    return items


def _parse_clarify_answers(comments: list[dict]) -> dict[str, str]:
    """Parse every Jira comment for lines like 'clarify:AMB-001: <answer>'.
    A later comment's answer for the same ID overrides an earlier one."""
    answers: dict[str, str] = {}
    for c in comments:
        text = _extract_text(c.get("body", ""))
        for m in _CLARIFY_ANSWER_LINE_RE.finditer(text):
            code, answer = m.group(1).upper(), m.group(2)
            answers[f"clarify:{code}"] = answer
    return answers


def _patch_clarify_item(md_path: Path, code: str, answer: str) -> bool:
    """Fill a clarify.md item's `{FILL...}` placeholder with the reviewer's
    answer and flip its STATUS TABLE row from OPEN to the terminal status
    for its type. Returns True if the item was found and patched, False
    otherwise (already resolved, or code doesn't exist in this file)."""
    if not md_path.exists():
        return False
    text = md_path.read_text()

    heading = re.search(r"^### " + re.escape(code) + r":.*$", text, re.MULTILINE)
    if not heading:
        return False
    rest = text[heading.end() :]
    end_match = re.search(r"\n---\s*\n|\n### ", rest)
    block_end = heading.end() + (end_match.start() if end_match else len(rest))
    fill_match = _CLARIFY_FILL_RE.search(text, heading.end(), block_end)
    if not fill_match:
        return False  # already answered

    prefix = code.split("-")[0]
    if prefix == "ASM":
        status = (
            "CONFIRMED" if answer.strip().lower().startswith("yes") else "CORRECTED"
        )
    else:
        status = _CLARIFY_TERMINAL_STATUS.get(prefix, "RESOLVED")

    new_text = text[: fill_match.start()] + answer + text[fill_match.end() :]

    status_row_re = re.compile(
        r"(^\|\s*" + re.escape(code) + r"\s*\|[^|]*\|[^|]*\|)\s*OPEN\s*(\|\s*$)",
        re.MULTILINE | re.IGNORECASE,
    )
    new_text, n = status_row_re.subn(r"\1 " + status + r" \2", new_text, count=1)
    if n == 0:
        return False  # STATUS TABLE row missing/already flipped -- don't half-patch

    new_text = _bump_version_and_log(
        new_text, f"{code} resolved via Jira/Confluence comment"
    )
    atomic_write_text(md_path, new_text)
    return True


_LEGACY_MARKER_RE = re.compile(r"\[NEEDS CLARIFICATION:\s*")


def _number_legacy_markers(md_path: Path) -> int:
    """Retroactively number any un-numbered `[NEEDS CLARIFICATION: ...]`
    markers in md_path as `[NEEDS CLARIFICATION-NNN: ...]`, in order of
    appearance, 1-indexed and zero-padded to 3 digits -- the exact
    convention specify-brd/uc/srd/doc.prompt.md now write for documents
    generated after this feature shipped.

    Projects whose brd.md/use-cases.md/srd.md predate that convention
    still have the old unnumbered form. validate.prompt.md's own
    §3a-BLOCKING table numbers them the same way (order of appearance)
    purely for DISPLAY -- it never patches the source file, since
    scanning isn't editing. Without this retrofit, that displayed
    numbering (what a reviewer's Jira/Confluence answer cites) never
    lines up with any real text in the source file, so
    push-questions/pull-answers's exact-ID matching can never find a
    marker to patch.

    The literal regex `\\[NEEDS CLARIFICATION:` (colon immediately
    after "CLARIFICATION", no dash) only matches the legacy unnumbered
    form -- an already-numbered `[NEEDS CLARIFICATION-NNN:` has a "-NNN"
    in between and is left untouched. Numbering continues after the
    highest existing NNN, so a doc with a mix of both forms doesn't
    collide. Returns the count of markers renumbered (0 if none found,
    including when the file doesn't exist)."""
    if not md_path.exists():
        return 0
    text = md_path.read_text()

    existing_nums = [int(n) for n in re.findall(r"\[NEEDS CLARIFICATION-(\d+):", text)]
    state = {"next_num": max(existing_nums, default=0) + 1, "count": 0}

    def renumber(_m: re.Match) -> str:
        replacement = f"[NEEDS CLARIFICATION-{state['next_num']:03d}: "
        state["next_num"] += 1
        state["count"] += 1
        return replacement

    new_text = _LEGACY_MARKER_RE.sub(renumber, text)
    if state["count"]:
        atomic_write_text(md_path, new_text)
    return state["count"]


def _ensure_epic(
    jira_client: JiraClient,
    jira_cfg,
    feature_name: str,
    confluence_base_url: str | None = None,
) -> str | None:
    """Create the Feature/Epic container if it doesn't already exist yet,
    using the same content and idempotency label `sdd jira push` uses — so a
    review ticket submitted before any dev Story/Task exists still lands
    under the same Epic those will use later. brd.md's Problem
    Statement/Business Hypothesis/Description/Business Objectives/Out of
    Scope/Success Criteria are already available at this point since BRD
    (the first document reviewed) is always drafted before its own review
    ticket is submitted -- NFR (from srd.md) fills in on a later re-push
    once /specify-srd runs. confluence_base_url, if given, adds a "Full
    Document" link once brd.md has actually been pushed to Confluence.
    Never blocks the review submission — prints a warning and returns None
    if Epic creation/lookup fails for any reason."""
    from sdd.commands.jira import _upsert_issue, feature_extra_fields
    from sdd.utils.validate import safe_feature_path

    try:
        features_dir = safe_feature_path(Path(".specify") / "features", feature_name)
        extra = feature_extra_fields(
            features_dir, jira_cfg, feature_name, confluence_base_url
        )
        key, _ = _upsert_issue(
            jira_client,
            jira_cfg.key_for("feature"),
            jira_cfg.issue_type_for("feature"),
            feature_name,
            extra,
            f"sdd-feature:{feature_name}",
            jira_cfg.labels,
        )
        return key
    except Exception as e:
        console.print(
            f"  [yellow]!  Could not create/find the Epic — review ticket "
            f"will not have a parent link ({e})[/yellow]"
        )
        return None


def _link_review_story_to_epic(
    jira_client: JiraClient, story_key: str, epic_key: str, jira_cfg
) -> None:
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
        _warn_parent_link_failed(
            jira_client, story_key, epic_key, jira_cfg.key_for("review"), e
        )


# ── Command group ──────────────────────────────────────────────────────────────


@click.group()
def review_command():
    """Document-level review gates — submit, check, apply, status."""


# ── sdd review submit ──────────────────────────────────────────────────────────


@review_command.command("submit")
@click.option(
    "--doc",
    required=True,
    help="Document key: brd, use-cases, srd, design (unified) / arch, hld, adr (separate), validate, analyze, clarify, lld, tasks, runbook, release",
)
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
    except (FileNotFoundError, IntegrationsConfigError) as e:
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
        jira_prof, jira_session = load_jira_session(cfg, profile)
        cf_prof, cf_session = load_confluence_session(cfg, profile)
    except Exception as e:
        console.print(f"  [red]✗  Auth error: {e}[/red]")
        raise SystemExit(1)

    manifest = read_manifest() or {}
    proj = manifest.get("project") or {}
    project_name = proj.get("name", "Project")
    feature_name = feature or proj.get("feature", "")

    jira_client = JiraClient(jira_session, jira_prof.base_url)
    cf_client = ConfluenceClient(cf_session, cf_prof.base_url)
    doc_cfg = cfg.document_reviews[doc]

    # ── Sequence gate ─────────────────────────────────────────────────────────
    ok, blocking = _check_predecessor(doc, cfg, jira_client, feature_name)
    if not ok:
        console.print(
            f"  [red]✗  Cannot submit {doc.upper()} — {blocking.upper()} is not yet approved.[/red]"
        )
        console.print(
            f"     Run [cyan]sdd review check --doc {blocking}[/cyan] to see its status."
        )
        raise SystemExit(1)

    # ── Push to Confluence ────────────────────────────────────────────────────
    try:
        md_path = resolve_doc_path(doc, feature_name)
    except ValueError as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)
    if not md_path.exists():
        console.print(
            f"  [red]✗  {md_path} not found — run the SDD command that generates it first[/red]"
        )
        raise SystemExit(1)

    page_title = doc_cfg.confluence_page.replace("{project}", project_name).replace(
        "{feature}", feature_name
    )
    from sdd.commands.confluence import (
        feature_collision_warning,
        resolve_doc_parent_id,
        upload_diagram_attachments,
    )

    _collision_warning = feature_collision_warning(page_title, feature_name)
    if _collision_warning:
        console.print(f"  [yellow]⚠  {_collision_warning}[/yellow]")

    body_html, attachments, diagram_warnings = md_to_storage(
        md_path.read_text(), cfg.confluence.diagrams
    )

    parent_id = resolve_doc_parent_id(
        cf_client, cfg.confluence, project_name, feature_name, doc
    )
    page, created = cf_client.upsert_page(
        cfg.confluence.space_key,
        page_title,
        body_html,
        parent_id,
    )
    upload_diagram_attachments(cf_client, page["id"], attachments)
    page_url = f"{cf_prof.base_url}/wiki{page.get('_links', {}).get('webui', '')}"
    action = "[green]created[/green]" if created else "[dim]updated[/dim]"
    console.print(f"  {action}  Confluence: [cyan]{page_title}[/cyan]")
    console.print(f"          {page_url}")
    for w in diagram_warnings:
        console.print(f"          [yellow]!  {w}[/yellow]")

    _record_confluence_draft_link(doc, page, page_title)

    # ── Ensure a Feature/Epic exists ──────────────────────────────────────────
    # So every review ticket -- and later every dev Story/Task from
    # `sdd jira push` -- nests under one place in Jira. Self-bootstrapping
    # here (rather than requiring a separate manual step) works because
    # BRD is always the first document reviewed, and its content is
    # already written the moment /specify-brd finishes -- well before this
    # review ticket exists to need a parent. cf_prof is already resolved
    # above (this doc was just pushed to Confluence), so the Epic's "Full
    # Document" link costs no extra auth/config lookup here.
    epic_key = _ensure_epic(jira_client, cfg.jira, feature_name, cf_prof.base_url)

    # ── Create / update Jira review story ─────────────────────────────────────
    # Issue type defaults to "Story" (not "Task") so review tickets sit at
    # the same hierarchy level as dev Stories under the Epic -- Epic ->
    # Story -> Task throughout, review tickets included, not a separate
    # shape -- but is independently overridable via issue_hierarchy.review
    # in integrations.yml (see JiraConfig.issue_type_for()).
    # Label is feature-qualified for the same reason Story/Task labels are
    # (see jira.py's _item_label): an un-qualified "sdd-doc:brd" would let
    # a second feature's BRD review submission find and silently overwrite
    # the first feature's review ticket.
    idempotency_label = f"sdd-doc:{feature_name}:{doc}"
    review_project_key = cfg.jira.key_for("review")
    existing = jira_client.find_by_label(review_project_key, idempotency_label)
    # feature_name in the summary too -- ticket lookup above is already
    # feature-safe via the label (no collision risk), but two features'
    # review tickets showing the identical summary text is still a real
    # usability problem: indistinguishable in Jira's own issue list/search.
    story_summary = f"Review: {project_name} / {feature_name} — {doc.upper()}"
    desc_text = (
        f"Please review the {doc.upper()} document.\n\n"
        f"Confluence: {page_url}\n\n"
        f"To APPROVE: set status to Done and comment 'Approved'.\n"
        f"To REQUEST CHANGES: add review comments and leave it open."
    )
    fields: dict = {
        "project": {"key": review_project_key},
        "issuetype": {"name": cfg.jira.issue_type_for("review")},
        "summary": story_summary,
        # cfg.jira.labels (base_fields.labels, e.g. "sdd-generated") is
        # applied here the same way _upsert_issue() applies it to every
        # Epic/Story/Task/CHG issue -- review tickets aren't a separate
        # shape, they just don't route through _upsert_issue().
        "labels": cfg.jira.labels + ["sdd-review", idempotency_label],
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": desc_text}]}
            ],
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
        # If this ticket started life as an `sdd review push-questions`
        # "open questions" ticket (same idempotency label -- see that
        # command), the fields update above already retitles/redescribes
        # it into a normal review request. Post a comment marking the
        # transition explicitly so the reviewer's ticket history shows
        # why the ticket suddenly changed shape, rather than reusing it
        # silently -- the "same ticket evolves in place" behavior a user
        # asked for, without ever creating a second ticket for one doc.
        was_open_questions = "sdd-open-questions" in (
            existing.get("fields", {}).get("labels") or []
        )
        jira_client.update_issue(existing["key"], fields)
        story_key = existing["key"]
        console.print(
            f"  [dim]·[/dim]   Jira review story updated: [cyan]{story_key}[/cyan]"
        )
        if was_open_questions:
            try:
                jira_client.add_comment(
                    story_key,
                    f"All open questions resolved — {doc.upper()} has been updated "
                    f"and is now ready for full review.",
                )
            except Exception:  # noqa: S110 -- see comment above
                pass  # best-effort notification only; the ticket update above already succeeded
    else:
        result = jira_client.create_issue(fields)
        story_key = result["key"]
        console.print(
            f"  [green]✓[/green]  Jira review story created: [cyan]{story_key}[/cyan]"
        )

    _record_review_link(doc, story_key)

    # ── Re-push Confluence with the now-existing Jira link/status banner ──────
    # The first push above (before the ticket existed) couldn't include this --
    # _push_doc_page's own find-by-label lookup will now find the ticket just
    # created/updated and prepend a banner showing its link + live status, so
    # a reviewer sees Jira state without leaving Confluence.
    try:
        _push_doc_page(doc, md_path, feature_name)
    except Exception as e:
        console.print(
            f"  [yellow]!  Could not stamp Jira status onto Confluence: {e}[/yellow]"
        )

    if epic_key:
        _link_review_story_to_epic(jira_client, story_key, epic_key, cfg.jira)

    console.print(
        f"          Assigned to: [cyan]{doc_cfg.reviewer_role}[/cyan]"
        f"  [dim]({doc_cfg.reviewer_jira_user})[/dim]"
    )
    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print(
        f"  [bold green]{doc.upper()} submitted![/bold green]  "
        f"Run [cyan]sdd review check --doc {doc}[/cyan] to poll the outcome."
    )
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()


# ── sdd review push-questions ───────────────────────────────────────────────────


@review_command.command("push-questions")
@click.option(
    "--doc",
    required=True,
    help="Document key whose blocking gate produced open questions, e.g. validate",
)
@click.option("--profile", default=None)
@click.option("--feature", default=None)
def review_push_questions(doc, profile, feature):
    """Push a blocked document's open [NEEDS CLARIFICATION-NNN] questions to
    Jira + Confluence, so a reviewer can answer them without waiting for
    the doc's own gate to clear first. Uses the same idempotency label
    `sdd review submit` looks for -- once every question is answered and
    the doc unblocks, `sdd review submit --doc {doc}` finds and evolves
    this same ticket in place instead of creating a second one."""
    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print(f"  [bold cyan]Push Open Questions[/bold cyan] — {doc.upper()}")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()

    try:
        cfg = load_integrations()
    except (FileNotFoundError, IntegrationsConfigError) as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)

    if doc not in cfg.document_reviews:
        console.print(
            f"  [red]✗  '{doc}' not in document_reviews in integrations.yml[/red]\n"
            f"     Available: {', '.join(cfg.document_reviews)}"
        )
        raise SystemExit(1)
    if not cfg.jira:
        console.print("  [red]✗  jira: section required in integrations.yml[/red]")
        raise SystemExit(1)

    manifest = read_manifest() or {}
    proj = manifest.get("project") or {}
    project_name = proj.get("name", "Project")
    feature_name = feature or proj.get("feature", "")

    try:
        md_path = resolve_doc_path(doc, feature_name)
    except ValueError as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)
    if not md_path.exists():
        console.print(f"  [red]✗  {md_path} not found[/red]")
        raise SystemExit(1)

    if doc == "clarify":
        items = _parse_clarify_open_items(md_path.read_text())
        not_found_msg = (
            "No OPEN items found in clarify.md's STATUS TABLE — nothing to push."
        )
    else:
        items = _parse_open_questions(md_path.read_text())
        not_found_msg = f"No open [NEEDS CLARIFICATION-NNN] items found in {md_path.name} — nothing to push."
    if not items:
        console.print(f"  [dim]{not_found_msg}[/dim]")
        raise SystemExit(0)

    try:
        jira_prof, session = load_jira_session(cfg, profile)
    except Exception as e:
        console.print(f"  [red]✗  Auth error: {e}[/red]")
        raise SystemExit(1)

    jira_client = JiraClient(session, jira_prof.base_url)
    doc_cfg = cfg.document_reviews[doc]

    # ── Also push the (blocked) doc to Confluence, so reviewers can comment there too ──
    page_title = None
    if cfg.confluence:
        try:
            pushed = _push_doc_page(doc, md_path, feature_name)
            if pushed:
                page_title, _page_url = pushed
        except Exception as e:
            console.print(f"  [yellow]!  Confluence push failed: {e}[/yellow]")

    # ── Ensure a Feature/Epic exists (same as review_submit) ──────────────────
    # No cf_prof already in scope here (the Confluence push above goes
    # through _push_doc_page's own session, not exposed to this
    # function), so resolve the base_url the same best-effort way sdd
    # jira push does -- never blocks this command if it fails.
    from sdd.commands.jira import _resolve_confluence_base_url

    epic_key = _ensure_epic(
        jira_client, cfg.jira, feature_name, _resolve_confluence_base_url(cfg)
    )

    # ── Create / update the SAME ticket review_submit will later find ─────────
    # Same idempotency_label as review_submit uses for --doc {doc} -- this
    # is what makes the ticket "evolve in place" later, with zero extra
    # bookkeeping: review_submit's own find-by-label lookup will discover
    # this ticket and update its fields, rather than creating a second one.
    idempotency_label = f"sdd-doc:{feature_name}:{doc}"
    review_project_key = cfg.jira.key_for("review")
    existing = jira_client.find_by_label(review_project_key, idempotency_label)

    table_lines = "\n".join(f"{it['id']}: {it['question']}" for it in items)
    desc_text = (
        f"{doc.upper()} is blocked on {len(items)} open question(s) before it can "
        f"go to full review.\n\n"
        f"Answer each item as a comment on THIS ticket, one line per item, "
        f"starting with its ID:\n\n{table_lines}\n\n"
        f'Example: "{items[0]["id"]}: <your answer>"\n\n'
        f"Once every item is answered, re-run /{doc} — it pulls the answers "
        f"automatically, updates the spec, and re-checks."
    )
    fields: dict = {
        "project": {"key": review_project_key},
        "issuetype": {"name": cfg.jira.issue_type_for("review")},
        "summary": f"Open Questions: {project_name} / {feature_name} — {doc.upper()}",
        "labels": cfg.jira.labels
        + ["sdd-review", "sdd-open-questions", idempotency_label],
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": desc_text}]}
            ],
        },
    }
    if doc_cfg.reviewer_jira_user:
        fields["assignee"] = {"accountId": doc_cfg.reviewer_jira_user}
    from sdd.commands.jira import _apply_team_field

    _apply_team_field(fields, cfg.jira, "review")

    if existing:
        jira_client.update_issue(existing["key"], fields)
        issue_key = existing["key"]
        console.print(f"  [dim]·[/dim]   Jira ticket updated: [cyan]{issue_key}[/cyan]")
    else:
        result = jira_client.create_issue(fields)
        issue_key = result["key"]
        console.print(
            f"  [green]✓[/green]  Jira ticket created: [cyan]{issue_key}[/cyan]"
        )

    _record_review_link(doc, issue_key)
    if epic_key:
        _link_review_story_to_epic(jira_client, issue_key, epic_key, cfg.jira)

    issue_url = f"{jira_prof.base_url}/browse/{issue_key}"
    console.print(f"          {issue_url}")
    if page_title:
        console.print(f"          Also on Confluence: [cyan]{page_title}[/cyan]")
    console.print(
        f"          Assigned to: [cyan]{doc_cfg.reviewer_role}[/cyan]"
        f"  [dim]({doc_cfg.reviewer_jira_user})[/dim]"
    )
    console.print()
    console.print(
        f"  [bold]{len(items)} open question(s)[/bold] pushed. Reviewer replies as a comment"
    )
    console.print(f'  starting with the item\'s ID, e.g. "{items[0]["id"]}: <answer>".')
    console.print(
        f"  Run [cyan]sdd review pull-answers --doc {doc}[/cyan] (or just re-run /{doc}) once answered."
    )
    console.print()


# ── sdd review pull-answers ──────────────────────────────────────────────────────


@review_command.command("pull-answers")
@click.option("--doc", required=True)
@click.option("--profile", default=None)
@click.option("--feature", default=None)
def review_pull_answers(doc, profile, feature):
    """Pull Jira comments answering a blocked document's open
    [NEEDS CLARIFICATION-NNN] questions and patch them directly into the
    source docs (e.g. brd.md/use-cases.md/srd.md for --doc validate).
    Safe to call unconditionally before re-scanning -- exits 0 quietly
    whenever there's nothing to do (not configured, no ticket yet, no new
    answers)."""
    console.print()

    try:
        cfg = load_integrations()
    except (FileNotFoundError, IntegrationsConfigError):
        raise SystemExit(0)

    if doc not in cfg.document_reviews or not cfg.jira:
        raise SystemExit(0)

    manifest = read_manifest() or {}
    proj = manifest.get("project") or {}
    feature_name = feature or proj.get("feature", "")

    try:
        md_path = resolve_doc_path(doc, feature_name)
    except ValueError:
        raise SystemExit(0)
    if not md_path.exists():
        raise SystemExit(0)

    is_clarify = doc == "clarify"
    if is_clarify:
        items = _parse_clarify_open_items(md_path.read_text())
    else:
        items = _parse_open_questions(md_path.read_text())
    if not items:
        raise SystemExit(0)

    if not is_clarify:
        # Retrofit: a doc that predates NEEDS CLARIFICATION-NNN numbering
        # still has the old unnumbered [NEEDS CLARIFICATION: ...] form, even
        # though validate.md's table above already displays synthesized
        # brd:NC-001-style IDs for it (order-of-appearance, same rule) --
        # number the source file's markers to match before attempting any
        # patch, or the exact-ID search below would never find them.
        # clarify.md's own items have no such legacy/numbering concern --
        # they're tracked by a STATUS TABLE row, not a bracketed marker.
        referenced_docs = {
            _normalize_doc_key(loc_id.split(":NC-")[0])
            for item in items
            for loc_id in item["locations"]
        }
        for doc_key in referenced_docs:
            try:
                loc_path = resolve_doc_path(doc_key, feature_name)
            except ValueError:
                continue
            renumbered = _number_legacy_markers(loc_path)
            if renumbered:
                console.print(
                    f"  [dim]·  Numbered {renumbered} legacy marker(s) in "
                    f"{loc_path.name} to match validate.md's IDs[/dim]"
                )

    links = _load_review_links()
    issue_key = (links.get(doc) or {}).get("key")
    if not issue_key:
        console.print(
            f"  [dim]·  No Jira ticket recorded for {doc} yet — "
            f"run `sdd review push-questions --doc {doc}` first.[/dim]"
        )
        raise SystemExit(0)

    try:
        jira_prof, session = load_jira_session(cfg, profile)
    except Exception:
        raise SystemExit(0)

    jira_client = JiraClient(session, jira_prof.base_url)
    try:
        comments = jira_client.get_comments(issue_key)
    except Exception as e:
        console.print(
            f"  [yellow]!  Could not fetch comments from {issue_key}: {e}[/yellow]"
        )
        raise SystemExit(0)

    answers = (
        _parse_clarify_answers(comments) if is_clarify else _parse_answers(comments)
    )
    if not answers:
        raise SystemExit(0)

    patched_docs: dict[str, int] = {}
    patched_paths: dict[str, Path] = {}
    for item in items:
        # The reviewer only ever cites the row's primary ID (item["id"]) --
        # that single answer must propagate to every location listed for
        # this question, not just the one the reviewer happened to name
        # (a multi-location row exists specifically so one answer can
        # resolve a question duplicated across several docs at once).
        if item["id"] not in answers:
            continue
        answer_text = answers[item["id"]]
        if is_clarify:
            code = item["id"].split("clarify:", 1)[1]
            if _patch_clarify_item(md_path, code, answer_text):
                patched_docs["clarify"] = patched_docs.get("clarify", 0) + 1
                patched_paths["clarify"] = md_path
                console.print(
                    f"  [green]✓[/green]  {item['id']} resolved in {md_path.name}"
                )
            continue
        for loc_id in item["locations"]:
            doc_key, nnn = loc_id.split(":NC-")
            doc_key = _normalize_doc_key(doc_key)
            try:
                loc_path = resolve_doc_path(doc_key, feature_name)
            except ValueError:
                continue
            if _patch_marker(loc_path, nnn, answer_text):
                patched_docs[doc_key] = patched_docs.get(doc_key, 0) + 1
                patched_paths[doc_key] = loc_path
                console.print(
                    f"  [green]✓[/green]  {loc_id} resolved in {loc_path.name}"
                )

    if patched_docs:
        total = sum(patched_docs.values())
        console.print(
            f"  [bold]{total} item(s) resolved[/bold] across "
            f"{len(patched_docs)} document(s): {', '.join(patched_docs)}"
        )
        console.print()

        # Re-push each patched doc's own Confluence page so it doesn't go
        # stale relative to the .md file we just edited. Until now,
        # pull-answers only ever wrote the local file -- BRD/SRD/UC's
        # Confluence pages (created back at their own /specify-brd ->
        # `sdd review submit` time) kept showing the pre-answer
        # [NEEDS CLARIFICATION] markers even after every question was
        # resolved here. Best-effort per doc: one page's failure doesn't
        # block the others or the patching that already succeeded.
        if cfg.confluence:
            for doc_key, loc_path in patched_paths.items():
                try:
                    pushed = _push_doc_page(doc_key, loc_path, feature_name)
                    if pushed:
                        title, _page_url = pushed
                        console.print(
                            f"  [green]✓[/green]  Confluence page refreshed: [cyan]{title}[/cyan]"
                        )
                except Exception as e:
                    console.print(
                        f"  [yellow]!  Could not refresh Confluence page for {doc_key}: {e}[/yellow]"
                    )
            console.print()


# ── sdd review check ───────────────────────────────────────────────────────────


@review_command.command("check")
@click.option("--doc", required=True)
@click.option("--profile", default=None)
@click.option(
    "--feature", default=None, help="Feature name (default: from manifest.yml)"
)
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

    manifest = read_manifest() or {}
    proj = manifest.get("project") or {}
    feature_name = feature or proj.get("feature", "")

    # ── Jira check ────────────────────────────────────────────────────────────
    try:
        cfg = load_integrations()
        jira_prof, session = load_jira_session(cfg, profile)
    except Exception:
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

    client = JiraClient(session, jira_prof.base_url)
    status, comments, _ = _get_review_status(
        doc, client, cfg.jira.key_for("review"), cfg, feature_name
    )
    doc_cfg = cfg.document_reviews.get(doc)
    role = doc_cfg.reviewer_role if doc_cfg else "reviewer"

    # ── Refresh the Confluence status banner to match what we just polled ─────
    # Best-effort: a reviewer who only looks at Confluence (never Jira
    # directly) should see the same status this command just printed, without
    # having to wait for the next `sdd review submit`/`apply`/`approve`.
    if cfg.confluence:
        try:
            md_path = resolve_doc_path(doc, feature_name)
            if md_path.exists():
                _push_doc_page(doc, md_path, feature_name)
        except Exception:  # noqa: S110 -- best-effort banner refresh, see comment above
            pass

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
            text = _extract_text(c.get("body", ""))
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
@click.option("--doc", required=True)
@click.option(
    "--feature", default=None, help="Feature name (default: from manifest.yml)"
)
@click.option(
    "--ack",
    is_flag=True,
    default=False,
    help="Mark every comment currently on this doc as addressed",
)
def review_comments(doc, feature, ack):
    """Read (or acknowledge) dashboard-left review comments directly --
    the pure-local-mode path for feedback that has no Jira ticket to poll.
    `sdd review check` already calls into this when jira: isn't configured;
    this command exists for explicit/manual use and discoverability.

    Exit codes: 0=no unacknowledged comments (or --ack succeeded), 1=some found.
    """
    console.print()
    manifest = read_manifest() or {}
    proj = manifest.get("project") or {}
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

    console.print(
        f"  [yellow]{len(comments)} unacknowledged comment(s) on {doc.upper()}[/yellow]"
    )
    console.print()
    for c in comments:
        console.print(
            f"  [cyan]{c.get('by', 'Unknown')}[/cyan]  [dim]{c.get('at', '')[:10]}[/dim]"
        )
        for line in c.get("text", "").splitlines():
            console.print(f"  {line}")
        console.print()
    console.print(
        f"  [dim]After addressing them: sdd review comments --doc {doc} --ack[/dim]"
    )
    console.print()
    raise SystemExit(1)


# ── sdd review approve ─────────────────────────────────────────────────────────


@review_command.command("approve")
@click.option(
    "--doc",
    required=True,
    help="Document key: brd, use-cases, srd, design (unified) / arch, hld, adr (separate), validate, analyze, clarify, lld, ...",
)
@click.option(
    "--local",
    is_flag=True,
    required=True,
    help="Write a local approval record (fallback when Jira is not configured)",
)
@click.option("--by", default="chat", help="Who approved — defaults to 'chat'")
@click.option(
    "--role",
    default=None,
    help=(
        "Scope the Approvals-table flip to the row(s) matching this role "
        "text (case-insensitive substring, e.g. 'Architect') instead of "
        "flipping every Pending row. Use this when the evidence is a "
        "single reviewer's sign-off (e.g. one Jira ticket assignee) that "
        "shouldn't be read as every RACI role having approved. Omit for "
        "the default blanket flip (appropriate for chat/local mode, "
        "where there's no per-role signal to scope to)."
    ),
)
@click.option(
    "--note", default="", help="Optional note (e.g. 'approved in chat session')"
)
@click.option(
    "--feature", default=None, help="Feature name (default: from manifest.yml)"
)
@click.option(
    "--no-confluence",
    is_flag=True,
    default=False,
    help="Skip the Confluence page update even if confluence: is configured",
)
def review_approve(doc, local, by, role, note, feature, no_confluence):
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
        console.print(
            "  [red]✗  Only --local approvals are supported by this command.[/red]"
        )
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
        if _mark_md_approved(md_path, approver_name=by, role_filter=role):
            console.print(
                f"  [green]✓[/green]  {md_path} — header set to Status: Approved"
            )
            if role:
                console.print(
                    f"  [dim]·[/dim]  Approvals table: only the '{role}' row(s) "
                    f"marked Approved — other rows left Pending (no evidence "
                    f"of their sign-off)."
                )
        # ── Mirror the approved doc to its Confluence page ────────────────────
        if no_confluence:
            console.print("  [dim]·  Confluence update skipped (--no-confluence)[/dim]")
        else:
            try:
                manifest = read_manifest() or {}
                feature_name = feature or (manifest.get("project") or {}).get(
                    "feature", ""
                )
                pushed = _push_doc_page(doc, md_path, feature_name)
                if pushed:
                    title, _page_url = pushed
                    console.print(
                        f"  [green]✓[/green]  Confluence page updated: [cyan]{title}[/cyan]"
                    )
                else:
                    console.print(
                        "  [dim]·  Confluence not configured — page not updated[/dim]"
                    )
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
    console.print(
        "  [dim]sdd review check will now return exit 0 for this document.[/dim]"
    )
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()


# ── sdd review apply ───────────────────────────────────────────────────────────


@review_command.command("apply")
@click.option("--doc", required=True)
@click.option("--profile", default=None)
@click.option("--feature", default=None)
def review_apply(doc, profile, feature):
    """After updating a document, re-push to Confluence and notify the
    reviewer in Jira -- or, in pure local mode (neither configured),
    acknowledge dashboard comments as addressed."""
    console.print()
    manifest = read_manifest() or {}
    proj = manifest.get("project") or {}
    feature_name = feature or proj.get("feature", "")

    try:
        md_path = resolve_doc_path(doc, feature_name)
    except ValueError as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)

    # Revert an Approved document's header the instant it changes post-
    # approval -- before anything below pushes/notifies, so Confluence and
    # the reviewer both see the true current state, not a stale "Approved"
    # header. Runs unconditionally, ahead of the integrations checks below,
    # since it's a pure local-file operation with no Jira/Confluence
    # dependency. No-op (returns False) for a document that isn't
    # currently Approved -- e.g. this is a pre-approval NEEDS REVISION
    # round, nothing to revert.
    if md_path.exists() and _mark_md_needs_revision(md_path):
        console.print(
            f"  [green]✓[/green]  {doc.upper()} header reverted from Approved "
            f"— pending re-review."
        )

    try:
        cfg = load_integrations()
        jira_prof, session = load_jira_session(cfg, profile)
    except Exception:
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

    # Unlike review_submit (which must create a brand-new Jira ticket AND
    # therefore needs both sections up front), apply is a re-push of a doc
    # that may already be under review in either integration independently
    # -- confluence-only and jira-only configs both re-push/notify with
    # whatever's actually configured, rather than hard-requiring both.
    page_url = ""
    if cfg.confluence:
        if md_path.exists():
            pushed = _push_doc_page(doc, md_path, feature_name)
            if pushed:
                page_title, page_url = pushed
                console.print(
                    f"  [green]✓[/green]  Confluence updated: [cyan]{page_title}[/cyan]"
                )
        else:
            console.print(
                f"  [dim]·[/dim]  {md_path} not found — skipping Confluence update"
            )

    # Notify reviewer on Jira (only if a review ticket exists for this doc --
    # docs pushed via the page_map fallback alone have no ticket to notify)
    if cfg.jira:
        jira_client = JiraClient(session, jira_prof.base_url)
        issue = jira_client.find_by_label(
            cfg.jira.key_for("review"), f"sdd-doc:{feature_name}:{doc}"
        )
        if issue:
            msg = "Document updated per review comments. Please re-review:"
            if page_url:
                msg += f" {page_url}"
            jira_client.add_comment(issue["key"], msg)
            console.print(
                f"  [green]✓[/green]  Reviewer notified on [cyan]{issue['key']}[/cyan]"
            )
            _record_review_link(doc, issue["key"])

            # Best-effort: nudge a Done/Closed ticket back into an active
            # workflow status so the re-review comment above doesn't sit
            # unnoticed on a closed ticket. Opt-in via reopen_status
            # (unset by default -- see IntegrationsConfig.reopen_status);
            # silently a no-op if unset, if the ticket is already in that
            # status, or if the project's workflow has no transition to it
            # from the ticket's current state -- never blocks the rest of
            # this command.
            if cfg.reopen_status:
                try:
                    moved = jira_client.transition_issue(
                        issue["key"], cfg.reopen_status
                    )
                    if moved:
                        console.print(
                            f"  [green]✓[/green]  {issue['key']} transitioned to "
                            f"[cyan]{cfg.reopen_status}[/cyan]"
                        )
                    else:
                        console.print(
                            f"  [dim]·[/dim]  {issue['key']} already at (or has no "
                            f"transition to) '{cfg.reopen_status}' — status left as is"
                        )
                except Exception as e:
                    console.print(
                        f"  [yellow]!  Could not transition {issue['key']}: {e}[/yellow]"
                    )
        else:
            console.print(
                f"  [yellow]·[/yellow]  No Jira review story found for {doc.upper()}"
            )

    console.print()
    console.print(
        f"  [bold green]{doc.upper()} updated.[/bold green]  "
        f"Run [cyan]sdd review check --doc {doc}[/cyan] after the reviewer responds."
    )
    console.print()


# ── sdd review status ──────────────────────────────────────────────────────────


@review_command.command("status")
@click.option("--profile", default=None)
@click.option(
    "--feature", default=None, help="Feature name (default: from manifest.yml)"
)
def review_status(profile, feature):
    """Show review state of all documents for the current project."""
    console.print()
    try:
        cfg = load_integrations()
        jira_prof, session = load_jira_session(cfg, profile)
    except Exception as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)

    if not cfg.jira:
        console.print("  [red]✗  No jira: section in integrations.yml[/red]")
        raise SystemExit(1)

    manifest = read_manifest() or {}
    proj = manifest.get("project") or {}
    feature_name = feature or proj.get("feature", "")
    scope = proj.get("scope")

    client = JiraClient(session, jira_prof.base_url)

    # Group by phase, sort by sequence
    _PHASE_ORDER = ["specify", "validate", "planning", "tasks", "release"]
    phases: dict[str, list] = {}
    for key, dc in cfg.document_reviews.items():
        phases.setdefault(dc.phase, []).append((key, dc))
    for entries in phases.values():
        entries.sort(key=lambda x: x[1].sequence)

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
                k
                for k, v in cfg.document_reviews.items()
                if v.phase == phase and v.sequence == dc.sequence - 1
            ]
            pred_approved = all(all_statuses.get(p) == "APPROVED" for p in preds)

            if preds and not pred_approved:
                icon, label, style = "🔒", "Blocked", "dim"
                all_statuses[key] = "BLOCKED"
            else:
                st, _, _ = _get_review_status(
                    key, client, cfg.jira.key_for("review"), cfg, feature_name
                )
                all_statuses[key] = st
                if st == "APPROVED":
                    icon, label, style = "✓ ", "Approved", "green"
                elif st == "NEEDS_REVISION":
                    icon, label, style = "✗ ", "Needs Revision", "yellow"
                elif st == "PENDING":
                    icon, label, style = "⏳", "Pending", "dim"
                else:
                    icon, label, style = "· ", "Not Submitted", "dim"

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
