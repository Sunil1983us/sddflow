"""Build a read-only project status snapshot from .specify/ on disk.

No network calls, no Jira/Confluence dependency — works for chat, local,
and jira review modes alike, since "Status:" headers inside .md files are
the authoritative gate in every mode (see CLAUDE.md "Document Review
Gates"). This is what `sdd dashboard` and `sdd status` render.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from sdd.utils.manifest import read_manifest
from sdd.utils.project_type import applicable_extended_docs
from sdd.utils.validate import safe_feature_path

# Best-effort generic pipeline order. Not every pack/scope/plan_mode
# generates every doc — this is used only to order what *does* exist and
# to guess "next" from the last-known doc found on disk; unknown doc
# files are still shown, just appended after this list.
PIPELINE_DOCS: list[tuple[str, str]] = [
    ("brd", "BRD"),
    ("use-cases", "Use Cases"),
    ("srd", "SRD"),
    ("component-spec", "Component Spec"),
    ("ux-flow", "UX Flow"),
    ("screen-spec", "Screen Spec"),
    ("resilience", "Resilience"),
    ("investigation", "Investigation"),
    ("checklist", "Checklist"),
    ("validate", "Validate"),
    ("analyze", "Analyze"),
    ("clarify", "Clarify"),
    ("design", "Design"),
    ("arch", "Architecture"),
    ("hld", "HLD"),
    ("adr", "ADR"),
    ("lld", "LLD"),
    ("stories", "Stories"),
    ("tasks", "Tasks"),
    ("qa-testcases", "QA Test Cases"),
    ("runbook", "Runbook"),
    ("release", "Release"),
]
_PIPELINE_ORDER = {key: i for i, (key, _label) in enumerate(PIPELINE_DOCS)}
_PIPELINE_LABELS = dict(PIPELINE_DOCS)

_STATUS_RE = re.compile(r"Status:\s*([A-Za-z][\w -]*)")
_TASK_HEADING_RE = re.compile(r"^#{2,3}\s+(TASK-\d+|PERF-\d+|CHG-\d+)\s*[—–-]+\s*(.+)$")
_TASK_STATUS_FIELD_RE = re.compile(r"\*\*Status:\*\*\s*(.+)")
_CHECKBOX_DONE_RE = re.compile(r"^\s*[-*]\s+\[[xX]\]")
_CHECKBOX_OPEN_RE = re.compile(r"^\s*[-*]\s+\[\s\]")
_SATISFIES_RE = re.compile(r"Satisfies:\s*(.+)")


def _norm_task_status(s: str) -> str:
    """Collapses a task's free-text/checkbox-derived status label into one
    of done/in_progress/not_started/unknown. Shared by _parse_tasks and
    build_bo_rollup so a task counts the same way in both places."""
    s = s.lower()
    if "done" in s or "complete" in s:
        return "done"
    if "progress" in s:
        return "in_progress"
    if "not started" in s or s == "":
        return "not_started"
    return "unknown"


def _extract_ids(text: str, prefix: str) -> list[str]:
    """All '{prefix}-NNN' tokens in free text, in order, deduped. Used to
    read BO-NNN/BR-NNN/UC-NNN/FR-NNN references out of table cells that
    are themselves free text (e.g. 'BR-002, BR-003' or 'FR-{NNN}' still
    unfilled)."""
    seen: list[str] = []
    for m in re.finditer(rf"\b{prefix}-(\d+)\b", text):
        tok = f"{prefix}-{m.group(1)}"
        if tok not in seen:
            seen.append(tok)
    return seen


def _table_rows_after_heading(lines: list[str], contains: str) -> list[list[str]]:
    """Finds the first '## ...' heading whose text contains `contains`,
    then parses the pipe-table immediately following it (header + separator
    row skipped). Returns [] if the heading or a table under it isn't
    found -- never raises; every caller treats this as best-effort, the
    doc may not exist yet or may predate a template change."""
    try:
        heading_idx = next(
            i
            for i, line in enumerate(lines)
            if line.strip().startswith("##") and contains in line
        )
    except StopIteration:
        return []
    sep_idx = None
    for i in range(heading_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("## "):
            return []
        if _TABLE_SEP_RE.match(stripped):
            sep_idx = i
            break
    if sep_idx is None:
        return []
    rows = []
    for line in lines[sep_idx + 1 :]:
        stripped = line.strip()
        if not stripped or stripped.startswith("## "):
            break
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        rows.append([c.strip() for c in stripped.strip("|").split("|")])
    return rows


# "Est. " is optional in the label -- token-usage-template.md dropped the
# prefix when the Source column (Real | Estimated) was added, since a row
# can now be either; older files created before that change still say
# "Total Est. Input Tokens" etc. and must keep parsing correctly.
_RUNNING_TOTAL_ROW_RE = re.compile(
    r"\|\s*(Total (?:Est\. )?Input Tokens|Total (?:Est\. )?Output Tokens|"
    r"Total (?:Est\. )?Cost \(USD\)|Commands logged|Last updated)\s*\|\s*(.+?)\s*\|"
)


def _doc_status(path: Path) -> str | None:
    """First 'Status: X' value found in the file, or None if unreadable/absent."""
    try:
        text = path.read_text(errors="replace", encoding="utf-8")
    except OSError:
        return None
    m = _STATUS_RE.search(text)
    return m.group(1).strip() if m else None


_TABLE_SEP_RE = re.compile(r"^\|(?:-+\|)+$")


def _parse_approvals_table(path: Path) -> list[dict]:
    """Parses a document's own '## Approvals' table -- present in every
    template, filled in identically regardless of review mode (chat/
    local/jira) per the review-decision-step shared block. This is the
    one source of truth for "who approved this / who's still pending"
    that works the same way in every mode, unlike .local-approvals.yml
    (local mode only) or a Jira ticket's comments (jira mode only).
    Tolerates the older 3-column format (Role | Status | Date) from
    before the Approver column existed, alongside the current 4-column
    one -- an existing project's docs predate that addition and must
    still parse. Returns [] if the section/table isn't found or the file
    is unreadable -- never raises, this is best-effort dashboard sugar.
    """
    try:
        text = path.read_text(errors="replace", encoding="utf-8")
    except OSError:
        return []
    lines = text.splitlines()
    try:
        heading_idx = next(
            i for i, line in enumerate(lines) if line.strip() == "## Approvals"
        )
    except StopIteration:
        return []
    sep_idx = None
    for i in range(heading_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("## "):
            return []
        if _TABLE_SEP_RE.match(stripped):
            sep_idx = i
            break
    if sep_idx is None:
        return []
    rows = []
    for line in lines[sep_idx + 1 :]:
        stripped = line.strip()
        if not stripped or stripped.startswith("## "):
            break
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) == 4:
            role, approver, appr_status, date = cells
        elif len(cells) == 3:
            role, appr_status, date = cells
            approver = ""
        else:
            continue
        if not role or role.startswith("{"):
            continue  # unfilled template placeholder -- doc was never regenerated
        rows.append(
            {
                "role": role,
                "approver": approver or None,
                "status": appr_status or None,
                "date": date or None,
            }
        )
    return rows


_ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def _parse_iso_date(s: str | None) -> date | None:
    """Strict YYYY-MM-DD parse -- returns None for anything else (free text,
    a different format, empty/missing). Templates now instruct the agent to
    always write dates as {date: YYYY-MM-DD} (see CHANGELOG), but existing
    documents written before that, or hand-edited afterward, won't parse --
    that's fine, this never raises and callers treat None as 'not
    computable', not an error."""
    if not s:
        return None
    m = _ISO_DATE_RE.match(s.strip())
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _parse_version_history_table(path: Path) -> list[dict]:
    """Parses a document's own '## Version History' table. Per the shared
    review-decision-step block, exactly two things append a row here: a
    reviewer-requested content edit (bumps the version -- 'Revision
    Logging'), and the final approval (same version as the row before it,
    summary 'Approved'). So the first row is always the creation/draft
    entry and, once the doc is Approved, the last row is always the
    approval event -- see _doc_timing() for how that's used.

    Not every document type has this table (release.md doesn't, for
    instance) -- an empty list means 'no version history', not an error.
    Tolerates the optional trailing CHG-NNN column (5 cells) alongside the
    4-cell base shape."""
    try:
        text = path.read_text(errors="replace", encoding="utf-8")
    except OSError:
        return []
    rows = []
    for cells in _table_rows_after_heading(text.splitlines(), "Version History"):
        if len(cells) == 5:
            version, when, changed_by, summary, _chg = cells
        elif len(cells) == 4:
            version, when, changed_by, summary = cells
        else:
            continue
        if not version or version.startswith("{"):
            continue  # unfilled template placeholder -- doc never regenerated
        rows.append(
            {
                "version": version,
                "date": when or None,
                "changed_by": changed_by or None,
                "summary": summary or None,
            }
        )
    return rows


def _doc_timing(path: Path, status: str | None, approvals: list[dict]) -> dict:
    """Created/approved dates, duration, and revision-round count for one
    document. Every field is None when it can't be computed (unparseable
    or missing dates, no Version History table, not yet approved) -- the
    dashboard shows '--' rather than guessing; see the "Missing/bad dates"
    decision in the version-history dashboard-enhancement round.

    created_date: the Version History table's first row -- never rewritten
        after being appended, so it's a stable creation timestamp even
        after later revisions change the doc's current Version: header.
    approved_date: the Version History table's LAST row, but only when the
        doc's Status: header says Approved (the shared review-decision-step
        block always appends exactly one same-version 'Approved' row as
        its last write, regardless of which mode -- chat/local/jira --
        surfaced the approval). Falls back to the Approvals table's own
        Date column (latest Approved row) for doc types with no Version
        History table at all, e.g. release.md.
    revision_rounds: count of version bumps in the table -- each one is a
        reviewer-requested content edit (Revision Logging), so this
        excludes both the creation row and the final same-version Approved
        row and only counts rounds that actually changed something.
    duration_days: approved_date - created_date, only when both parse.
    """
    history = _parse_version_history_table(path)
    created = _parse_iso_date(history[0]["date"]) if history else None
    is_approved = status is not None and "approved" in status.lower()

    approved = None
    if is_approved:
        if history:
            approved = _parse_iso_date(history[-1]["date"])
        else:
            approved_dates = [
                d
                for d in (
                    _parse_iso_date(row.get("date"))
                    for row in approvals
                    if (row.get("status") or "").lower() == "approved"
                )
                if d is not None
            ]
            approved = max(approved_dates) if approved_dates else None

    revision_rounds = None
    if history:
        revision_rounds = sum(
            1
            for i in range(1, len(history))
            if history[i]["version"] != history[i - 1]["version"]
        )

    return {
        "created_date": created.isoformat() if created else None,
        "approved_date": approved.isoformat() if approved else None,
        "duration_days": (approved - created).days if (created and approved) else None,
        "revision_rounds": revision_rounds,
    }


def _load_roles_map(root: Path) -> dict:
    """roles.yml's top-level `roles:` map (snake_case key -> name filled in
    once per project), or {} if the file/section is missing/unreadable."""
    path = root / ".specify" / "memory" / "roles.yml"
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    roles = data.get("roles")
    return roles if isinstance(roles, dict) else {}


def _normalize_role_key(role_label: str) -> str:
    """'DevOps/SRE' / 'QA Lead' / 'Tech Lead' -> 'devops_sre' / 'qa_lead' /
    'tech_lead' -- matches roles.yml's snake_case key convention so a
    document's human-readable Approvals-table Role column can be looked
    up directly, without a second hardcoded mapping to keep in sync.

    Every real template's Approvals table Role cell carries a RACI
    annotation in parentheses -- e.g. "Product Owner (accountable --
    business objectives sign-off)" (brd-template.md) or "DevOps/SRE
    (consulted -- deployment readiness)" (release-template.md), never
    just the bare role name. That suffix must be stripped before
    normalizing, or the result ("product_owner_accountable_business_..."
    ) never matches any roles.yml key -- which used to mean every
    project's Approvals detail panel showed "not set in roles.yml" for
    every role, even with roles.yml fully filled in."""
    label = re.split(r"\s*\(", role_label.strip(), maxsplit=1)[0]
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def _resolve_expected_approver(role_label: str, roles_map: dict) -> str | None:
    name = roles_map.get(_normalize_role_key(role_label))
    return name if isinstance(name, str) and name.strip() else None


def list_feature_names(root: Path) -> list[str]:
    """Every feature folder under .specify/features/, sorted. Public --
    used both internally (build_project_status) and by `sdd feature list`/
    `sdd feature status`, which need the exact same filesystem scan the
    dashboard already uses as its source of truth, rather than a second,
    separately-maintained list (see the "why not a manifest.yml features
    list" design discussion this exists to avoid re-litigating)."""
    features_dir = root / ".specify" / "features"
    if not features_dir.is_dir():
        return []
    return sorted(p.name for p in features_dir.iterdir() if p.is_dir())


_list_feature_names = list_feature_names  # internal call sites, unchanged


_NON_PIPELINE_DOCS = {"token-usage"}
_LOCAL_APPROVALS_PATH = Path(".specify") / ".local-approvals.yml"
_DASHBOARD_COMMENTS_PATH = Path(".specify") / ".dashboard-comments.json"


def _local_approvals(root: Path) -> dict:
    """Same file/format `sdd review approve --local` writes — bare doc key,
    not feature-scoped (matches that command's existing format; see
    dashboard.py's _do_approve docstring for why this isn't changed here)."""
    path = root / _LOCAL_APPROVALS_PATH
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _dashboard_comments(root: Path, feature: str, doc: str) -> list:
    path = root / _DASHBOARD_COMMENTS_PATH
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data.get(f"{feature}/{doc}", [])


def _annotate_approvals(rows: list[dict], roles_map: dict) -> list[dict]:
    """For each Approvals-table row still Pending with no Approver filled
    in, resolve who's expected to act from roles.yml — so a document
    waiting on review names the actual person, not just the role."""
    annotated = []
    for row in rows:
        entry = dict(row)
        entry["expected_approver"] = (
            None
            if entry.get("approver")
            else _resolve_expected_approver(entry["role"], roles_map)
        )
        annotated.append(entry)
    return annotated


def _feature_docs(root: Path, feature: str) -> list[dict]:
    feature_dir = root / ".specify" / "features" / feature
    docs: list[dict] = []
    md_files = sorted(
        (
            p
            for p in feature_dir.glob("*.md")
            if not p.name.endswith(".summary.md") and p.stem not in _NON_PIPELINE_DOCS
        ),
        key=lambda p: _PIPELINE_ORDER.get(p.stem, 999),
    )
    approvals = _local_approvals(root)
    roles_map = _load_roles_map(root)
    for path in md_files:
        key = path.stem
        status = _doc_status(path)
        approvals_table = _annotate_approvals(_parse_approvals_table(path), roles_map)
        docs.append(
            {
                "key": key,
                "label": _PIPELINE_LABELS.get(key, key.replace("-", " ").title()),
                "exists": True,
                "status": status,
                "path": str(path),
                "local_approval": approvals.get(key),
                "comments": _dashboard_comments(root, feature, key),
                "approvals": approvals_table,
                "timing": _doc_timing(path, status, approvals_table),
            }
        )
    return docs


def _feature_timeline(docs: list[dict]) -> dict:
    """Feature-level start/end rolled up from each document's own timing
    (_doc_timing). start_date is the earliest created_date across every doc
    that has one -- normally brd.md's v1.0 row, since it's first in the
    pipeline. end_date is release.md's approved_date, once release.md
    exists and is Approved -- the feature's actual last gate. Both stay
    None until there's enough data to compute them; duration_days only once
    both resolve. ISO date strings sort correctly with plain min(), no need
    to re-parse for that part."""
    created = [
        d["timing"]["created_date"]
        for d in docs
        if d.get("timing", {}).get("created_date")
    ]
    start = min(created) if created else None

    release_doc = next((d for d in docs if d["key"] == "release"), None)
    end = release_doc["timing"]["approved_date"] if release_doc else None

    duration_days = None
    if start and end:
        start_d, end_d = _parse_iso_date(start), _parse_iso_date(end)
        if start_d and end_d:
            duration_days = (end_d - start_d).days

    return {"start_date": start, "end_date": end, "duration_days": duration_days}


def _current_stage(
    docs: list[dict], feature: str = "this feature", scope: str | None = "pilot"
) -> dict:
    """Last pipeline-ordered doc that exists, plus a best-effort 'next' guess
    and (when the next doc has one) its Virtual Team persona hint. No hint
    for the "(awaiting approval)" case -- the ask templates are all
    creation-phrased and the doc already exists, waiting on a human
    reviewer, not on the persona who'd create it."""
    known = [d for d in docs if d["key"] in _PIPELINE_ORDER]
    if not known:
        first_key = PIPELINE_DOCS[0][0] if PIPELINE_DOCS else None
        return {
            "doc": None,
            "status": None,
            "next": PIPELINE_DOCS[0][1] if PIPELINE_DOCS else None,
            "persona": _persona_hint(first_key, feature, scope) if first_key else None,
        }
    known.sort(key=lambda d: _PIPELINE_ORDER[d["key"]])
    last = known[-1]
    idx = _PIPELINE_ORDER[last["key"]]
    next_key = PIPELINE_DOCS[idx + 1][0] if idx + 1 < len(PIPELINE_DOCS) else None
    next_label = PIPELINE_DOCS[idx + 1][1] if idx + 1 < len(PIPELINE_DOCS) else None
    status = (last["status"] or "").lower()
    awaiting_approval = status not in ("approved",) and status != ""
    return {
        "doc": last["label"],
        "status": last["status"],
        "next": ("(awaiting approval)" if awaiting_approval else next_label),
        "persona": (
            None
            if awaiting_approval or not next_key
            else _persona_hint(next_key, feature, scope)
        ),
    }


def persona_for(step_id: str, feature: str, scope: str | None) -> dict | None:
    """Public wrapper around the pipeline's Virtual Team persona lookup, for
    callers outside build_pipeline/build_feature_status that want the same
    hint (e.g. `sdd review status`, which reads document_reviews keys
    directly rather than going through the pipeline)."""
    return _persona_hint(step_id, feature, scope)


def _checklist_info(root: Path, feature: str) -> dict:
    """Existence + open-CRITICAL-count for /checklist's output at
    .specify/features/{feature}/checklists/{feature}-spec-quality.md.

    Deliberately NOT discoverable via _feature_docs()'s
    feature_dir.glob("*.md") -- checklist.prompt.md saves it inside a
    checklists/ subdirectory, named "{feature}-spec-quality.md" rather
    than "checklist.md", so the flat top-level glob never finds it. It
    also has no `> Status: Draft | ...` header like every other spec doc
    -- it's a self-contained audit report an agent generates for itself,
    not a document someone reviews and approves. Both of those meant the
    pipeline's Checklist step could never show "done" no matter how many
    times /checklist actually ran -- a real bug, not the scope/mvp
    enforcement question this looks similar to (see validate.prompt.md's
    CHECKLIST GATE). "done" here means exists + zero open CRITICAL rows
    in the CHK-NNN table, not a Status: header -- see build_pipeline()'s
    "checklist" step kind."""
    path = (
        root
        / ".specify"
        / "features"
        / feature
        / "checklists"
        / f"{feature}-spec-quality.md"
    )
    if not path.is_file():
        return {"exists": False, "critical_open": None}
    try:
        text = path.read_text(errors="replace", encoding="utf-8")
    except OSError:
        return {"exists": False, "critical_open": None}
    rows = _table_rows_after_heading(text.splitlines(), "CHK-NNN Items")
    critical_open = sum(
        1 for r in rows if len(r) > 2 and r[2].strip().upper() == "CRITICAL"
    )
    return {"exists": True, "critical_open": critical_open}


def _service_doc_info(root: Path, key: str) -> dict:
    """Existence + Status: header for one specific living/service-level doc
    (data-model or security-design — see LIVING_SERVICE_DOCS in
    sdd/utils/validate.py) at .specify/service/{key}.md. Per-doc, not a
    folder-wide existence check — see build_pipeline()'s per-key
    "service_doc" steps for why: a single collapsed check meant generating
    just one of these two docs made the dashboard show *both* as done."""
    path = root / ".specify" / "service" / f"{key}.md"
    if not path.is_file():
        return {"exists": False, "status": None}
    return {"exists": True, "status": _doc_status(path)}


# Living/service-level docs shown in the dashboard's project-level
# "Living Documents" section (see _service_level_docs() below) --
# (key, label, command, always_shown). Data Model and Security Design are
# the two currently wired up; api-spec and component-library are also in
# LIVING_SERVICE_DOCS (sdd/utils/validate.py) but aren't generated via a
# standalone /specify-doc command (api-spec comes from /plan-design §3;
# component-library has no dashboard tracking yet either) -- deliberately
# left out here rather than showing a command hint that doesn't exist.
_SERVICE_LEVEL_DOC_SPECS = [
    ("data-model", "Data Model", "/specify-doc data-model", False),
    ("security-design", "Security Design", "/specify-doc security", True),
]


def _service_level_docs(
    root: Path, current_feature: str, scope: str | None
) -> list[dict]:
    """Full doc entries (same shape _feature_docs() returns -- status,
    approvals, comments, timing) for the project-wide living/service-level
    docs, so the dashboard's project-level "Living Documents" section gets
    the exact same Approve button / Confluence+Jira links / Details panel
    every per-feature document already has, instead of being reduced to a
    bare progress dot inside one feature's own pipeline (which is what
    build_pipeline()'s old "service_doc" steps did -- see their docstring
    note in build_pipeline() -- and, worse, meant the SAME shared doc
    displayed as a separate dot inside every feature's own pipeline card
    on a multi-feature project, each computed from the identical
    underlying file. Reported by a user who couldn't find Data Model on
    the dashboard at all and found its "waiting for review" status
    confusing buried in a per-feature progress list).

    current_feature is used only for the local comments-store key
    (.dashboard-comments.json, keyed "{feature}/{doc}") and Jira-ticket
    lookup, matching the exact same feature-tagging `sdd review submit`
    itself already uses for these docs (it has no living-doc special
    case either -- the review ticket for a living doc ends up labeled
    with whatever feature was active/passed at submit time). This keeps
    the dashboard consistent with the CLI's own pre-existing behavior
    rather than inventing a different scheme; .local-approvals.yml
    (unlike comments) is already bare-doc-keyed with no feature
    involved at all, so approval state is unaffected by this either way.
    """
    mvp_plus = _scope_at_least(scope, "mvp")
    approvals = _local_approvals(root)
    roles_map = _load_roles_map(root)
    docs: list[dict] = []
    for key, label, command, always_shown in _SERVICE_LEVEL_DOC_SPECS:
        skip = None if (always_shown or mvp_plus) else "pilot scope"
        path = root / ".specify" / "service" / f"{key}.md"
        exists = path.is_file()
        status = _doc_status(path) if exists else None
        approvals_table = (
            _annotate_approvals(_parse_approvals_table(path), roles_map)
            if exists
            else []
        )
        docs.append(
            {
                "key": key,
                "label": label,
                "command": command,
                "skip": skip,
                "exists": exists,
                "status": status,
                "path": str(path) if exists else None,
                "local_approval": approvals.get(key),
                "comments": _dashboard_comments(root, current_feature, key)
                if current_feature
                else [],
                "approvals": approvals_table,
                "timing": _doc_timing(path, status, approvals_table),
            }
        )
    return docs


# Per-feature extended docs whose applicability depends on project type --
# detected from which template file the pack actually ships, rather than
# hardcoding pack names. This works for the 4 single-type packs (each ships
# only the templates its own type needs) but NOT for sdd-universal, which
# ships every template up front and branches at runtime by `project_type`
# instead -- see sdd.utils.project_type.EXTENDED_DOCS_BY_TYPE for that case.
_EXTENDED_TEMPLATE_MAP = {
    "component-spec": "component-spec-template.md",
    "ux-flow": "ux-flow-template.md",
    "screen-spec": "screen-spec-template.md",
}

# sdd-universal only: which of the type-specific extended docs apply per
# project_type, mirroring the Action 2 doc-set matrix in sdd-universal's
# own specify.prompt.md. Sourced from sdd.utils.project_type -- the single
# canonical copy of this mapping, also used by `sdd project-type migrate`
# to report what changes when a project's type is switched -- so the two
# can never drift apart. cli/library/iac are deliberately absent from that
# map (not mapped to {}) -- the framework doesn't cleanly define UI-doc
# applicability for those types either; template-presence detection would
# wrongly say "yes" for universal (it ships every template), so they fall
# through to no type-specific docs shown rather than a guessed answer.


def _applicable_extended_docs(root: Path, project_type: str | None) -> set[str]:
    """Which of component-spec/ux-flow/screen-spec this project should show
    on the dashboard. resilience/investigation and the two living docs
    (data-model, security-design) aren't here -- they're scope-gated only,
    applicable regardless of project type."""
    if project_type:
        return set(applicable_extended_docs(project_type))
    templates_dir = root / ".specify" / "templates"
    return {
        key
        for key, fname in _EXTENDED_TEMPLATE_MAP.items()
        if (templates_dir / fname).is_file()
    }


_SCOPE_ORDER = {"pilot": 0, "mvp": 1, "full": 2}


def _scope_at_least(scope: str | None, minimum: str) -> bool:
    return _SCOPE_ORDER.get(scope or "pilot", 0) >= _SCOPE_ORDER[minimum]


# Virtual Team roster (see each pack's CLAUDE.md "Virtual Team — Address by
# Name" table) -- name -> role, for the persona hint shown in the tooltip
# and next-action box. sdd-micro has no Virtual Team at all (its steps use
# id "task", not "tasks", and are never looked up here since callers pass
# scope=None for micro).
_PERSONA_ROLE = {
    "Maya": "Business Analyst",
    "Rex": "Requirements Engineer",
    "Ava": "Software Architect",
    "Leo": "Lead Developer",
    "Kai": "Engineering Manager",
    "Quinn": "QA Lead",
    "Riley": "Release Manager",
}

# Pipeline step id -> (persona name, natural-language ask with a {feature}
# placeholder). Addressing a persona by name (e.g. "Ava, design checkout")
# works identically to running that step's slash command -- see each
# pack's CLAUDE.md "Virtual Team" routing rule. Steps with no clear owner
# (specify/gate1 -- run before any persona takes over; runbook -- a
# byproduct of /implement, not something you ask for directly) are
# intentionally absent from this map.
_STEP_PERSONA = {
    "brd": ("Maya", "create the BRD for {feature}"),
    "use-cases": ("Maya", "write the use cases for {feature}"),
    "srd": ("Rex", "write the SRD for {feature}"),
    "security-design": ("Ava", "write the security design for {feature}"),
    "data-model": ("Ava", "write the data model for {feature}"),
    "component-spec": ("Ava", "write the component spec for {feature}"),
    "ux-flow": ("Ava", "write the UX flow for {feature}"),
    "screen-spec": ("Ava", "write the screen spec for {feature}"),
    "resilience": ("Ava", "write the resilience design for {feature}"),
    "investigation": ("Ava", "write the investigation doc for {feature}"),
    "checklist": ("Quinn", "run the spec quality checklist for {feature}"),
    "validate": ("Maya", "validate {feature}"),
    "analyze": ("Ava", "run the cross-doc analysis on {feature}"),
    "clarify": ("Rex", "clarify the open questions on {feature}"),
    "design": ("Ava", "design {feature}"),
    "arch": ("Ava", "design the architecture for {feature}"),
    "hld": ("Ava", "write the high-level design for {feature}"),
    "adr": ("Ava", "record the architecture decisions for {feature}"),
    "lld": ("Leo", "write the low-level design for {feature}"),
    "stories": ("Kai", "break {feature} into stories"),
    "tasks": ("Kai", "break {feature} into tasks"),
    "smoke-tests": ("Kai", "write smoke tests for {feature}"),
    "qa-testcases": ("Kai", "write QA test cases for {feature}"),
    "implement": ("Leo", "implement the next task for {feature}"),
    "release": ("Riley", "plan the release for {feature}"),
}


def _persona_hint(step_id: str, feature: str, scope: str | None) -> dict | None:
    """Which Virtual Team member owns this step, plus an example
    natural-language ask the user can type instead of memorizing the slash
    command. None for sdd-micro (scope is None) and for steps with no
    persona owner (see _STEP_PERSONA's docstring)."""
    if scope is None:
        return None
    entry = _STEP_PERSONA.get(step_id)
    if not entry:
        return None
    name, template = entry
    return {
        "name": name,
        "role": _PERSONA_ROLE[name],
        "ask": template.format(feature=feature),
    }


def _standard_pipeline_steps(
    scope: str | None, plan_mode: str, applicable_extended: frozenset[str] = frozenset()
) -> list[dict]:
    """The full command sequence for every pack except sdd-micro (backend,
    frontend-spa, mobile, fullstack, universal all share this exact
    top-level flow — see each pack's own CLAUDE.md header). Every step is
    always included, even ones this scope/plan_mode skips, so the dashboard
    can show *why* a step is absent rather than silently omitting it —
    the skip reasons mirror CLAUDE.md's "Scope Reference" table exactly.

    data-model and security-design (living/service-level, one shared file
    for the whole project, not per-feature) are NOT steps in this
    sequence — see _service_level_docs() and the dashboard's project-level
    "Living Documents" section instead. The type-specific extended docs
    (component-spec/ux-flow/screen-spec) genuinely are per-feature, so
    they stay here:
    - component-spec / ux-flow / screen-spec: mvp+, and only included at
      all when `applicable_extended` says this project's type uses them
      (component-spec/ux-flow: frontend-spa/desktop/fullstack; screen-spec/
      ux-flow: mobile) — omitted entirely for types that don't, rather than
      shown as a permanent "not applicable" row
    - resilience / investigation: full scope only
    """
    mvp_plus = _scope_at_least(scope, "mvp")
    full = _scope_at_least(scope, "full")
    separate = plan_mode == "separate"
    pilot = (scope or "pilot") == "pilot"

    def doc(id_, command, label, doc_key, skip=None, optional=False):
        return {
            "id": id_,
            "command": command,
            "label": label,
            "kind": "doc",
            "doc_key": doc_key,
            "skip": skip,
            "optional": optional,
        }

    # Data Model / Security Design used to each get a "service_doc" step
    # here too, but that meant the SAME project-wide file (.specify/
    # service/{key}.md, generated once, not per-feature) showed as a
    # separate progress dot inside every single feature's own pipeline
    # card on a multi-feature project -- confusing, and easy to miss
    # entirely since it was buried mid-list rather than surfaced
    # anywhere project-level. They're now in their own project-level
    # "Living Documents" section instead (see _service_level_docs()),
    # shown once, not duplicated per feature. build_pipeline()'s
    # `service_docs` param and _step_state()'s "service_doc" kind branch
    # are dead code as of this change (no step ever produces that kind
    # anymore) -- left in place rather than removed, since trimming them
    # would touch build_pipeline()'s public signature and every call
    # site/test that constructs it, for no behavioral gain.
    extended_steps: list[dict] = []
    if "component-spec" in applicable_extended:
        extended_steps.append(
            doc(
                "component-spec",
                "/specify-doc component-spec",
                "Component Spec",
                "component-spec",
                skip=None if mvp_plus else "pilot scope",
            )
        )
    if "ux-flow" in applicable_extended:
        extended_steps.append(
            doc(
                "ux-flow",
                "/specify-doc ux-flow",
                "UX Flow",
                "ux-flow",
                skip=None if mvp_plus else "pilot scope",
            )
        )
    if "screen-spec" in applicable_extended:
        extended_steps.append(
            doc(
                "screen-spec",
                "/specify-doc screen-spec",
                "Screen Spec",
                "screen-spec",
                skip=None if mvp_plus else "pilot scope",
            )
        )
    extended_steps.append(
        doc(
            "resilience",
            "/specify-doc resilience",
            "Resilience",
            "resilience",
            skip=None if full else "full scope",
        )
    )
    extended_steps.append(
        doc(
            "investigation",
            "/specify-doc investigation",
            "Investigation",
            "investigation",
            skip=None if full else "full scope",
        )
    )

    return [
        {
            "id": "specify",
            "command": "/specify",
            "label": "Constitution (Part 2)",
            "kind": "constitution",
        },
        {
            "id": "gate1",
            "command": None,
            "label": "GATE-1 — Constitution Finalized",
            "kind": "manual_gate",
        },
        doc("brd", "/specify-brd", "Business Requirements Document", "brd"),
        doc("use-cases", "/specify-uc", "Use Case Specification", "use-cases"),
        doc("srd", "/specify-srd", "Software Requirements Document", "srd"),
        *extended_steps,
        {
            "id": "checklist",
            "command": "/checklist",
            "label": "Spec Quality Checklist",
            "kind": "checklist",
            "skip": None,
            "optional": pilot,
        },
        doc("validate", "/validate", "Validate", "validate"),
        doc("analyze", "/analyze", "Cross-Doc Analysis", "analyze"),
        doc("clarify", "/clarify", "Clarify Ambiguities", "clarify"),
        doc(
            "design",
            "/plan-design",
            "Design (Architecture + HLD + API)",
            "design",
            skip=None if not separate else "separate plan mode",
        ),
        doc(
            "arch",
            "/plan-arch",
            "Architecture",
            "arch",
            skip=None if separate else "unified plan mode",
        ),
        doc(
            "hld",
            "/plan-hld",
            "High-Level Design",
            "hld",
            skip=None if separate else "unified plan mode",
        ),
        doc(
            "adr",
            "/plan-adr",
            "Architecture Decision Records",
            "adr",
            skip=(
                "unified plan mode"
                if not separate
                else (None if mvp_plus else "pilot scope")
            ),
        ),
        doc(
            "lld",
            "/plan-lld",
            "Low-Level Design",
            "lld",
            skip=None if mvp_plus else "pilot scope",
        ),
        doc("stories", "/task", "User Stories", "stories"),
        doc("tasks", "/task", "Task Breakdown", "tasks"),
        doc(
            "smoke-tests",
            "/task",
            "Smoke Tests (≤10 cases)",
            "smoke-tests",
            skip=None if pilot else "mvp+ scope",
        ),
        doc(
            "qa-testcases",
            "/task",
            "QA Test Cases",
            "qa-testcases",
            skip="pilot scope" if pilot else None,
        ),
        {
            "id": "implement",
            "command": "/implement",
            "label": "Implementation (per task)",
            "kind": "tasks_progress",
        },
        doc(
            "runbook",
            "(generated by /implement)",
            "Runbook",
            "runbook",
            skip=None if mvp_plus else "pilot scope",
        ),
        doc("release", "/release", "Release Plan & Go/No-Go", "release"),
    ]


def _micro_pipeline_steps() -> list[dict]:
    """sdd-micro's only 3 commands — see its CLAUDE.md header. No scope,
    no review-gated spec docs; identified by scope being absent on the
    manifest (sdd-micro's manifest.yml has no project.scope field)."""
    return [
        {
            "id": "specify",
            "command": "/specify",
            "label": "Constitution (Confirmed)",
            "kind": "constitution",
        },
        {
            "id": "gate1",
            "command": None,
            "label": "GATE-1 — Constitution Confirmed",
            "kind": "manual_gate",
        },
        {
            "id": "task",
            "command": "/task",
            "label": "Task Breakdown",
            "kind": "doc",
            "doc_key": "tasks",
            "skip": None,
        },
        {
            "id": "implement",
            "command": "/implement",
            "label": "Implementation",
            "kind": "tasks_progress",
        },
    ]


def _step_state(
    step: dict,
    docs_by_key: dict,
    tasks: dict,
    constitution: dict,
    service_docs: dict,
    checklist_info: dict | None = None,
) -> str:
    """done | current | upcoming — 'current' means either awaiting review
    (a doc exists but its Status: header isn't Approved yet) or actively
    in progress (tasks partially done); 'upcoming' means not started."""
    kind = step["kind"]
    if kind == "constitution":
        return "done" if constitution.get("part2_generated") else "upcoming"
    if kind == "manual_gate":
        if constitution.get("gate1_inferred") == "passed":
            return "done"
        return "current" if constitution.get("part2_generated") else "upcoming"
    if kind == "service_doc":
        info = service_docs.get(step["doc_key"]) or {"exists": False, "status": None}
        if not info["exists"]:
            return "upcoming"
        status = (info.get("status") or "").lower()
        return "done" if "approved" in status else "current"
    if kind == "tasks_progress":
        if tasks["total"] == 0:
            return "upcoming"
        return "done" if tasks["done"] == tasks["total"] else "current"
    if kind == "checklist":
        # No Status: Draft/Approved header (see _checklist_info()) -- "done"
        # is exists + zero open CRITICAL findings, not an approval.
        info = checklist_info or {"exists": False, "critical_open": None}
        if not info["exists"]:
            return "upcoming"
        return "done" if not info["critical_open"] else "current"
    doc = docs_by_key.get(step["doc_key"])
    if not doc:
        return "upcoming"
    status = (doc.get("status") or "").lower()
    return "done" if "approved" in status else "current"


def _next_action_sentence(
    step: dict, state: str, tasks: dict, checklist_info: dict | None = None
) -> str:
    kind = step["kind"]
    if kind == "constitution":
        return "Run `/specify` to generate the project constitution."
    if kind == "manual_gate":
        return (
            "Review and finalize constitution Part 2 (Tech Stack, Core "
            "Principles, Domain Rules, Never Do), then tell your agent: "
            '"Constitution Part 2 finalized."'
        )
    if kind == "tasks_progress":
        if state == "upcoming":
            return "Run `/task` to break this feature into tasks, then `/implement` to start building."
        return f"Run `/implement` to continue — {tasks['done']}/{tasks['total']} tasks done."
    if kind == "checklist":
        if state == "current":
            n = (checklist_info or {}).get("critical_open") or 0
            plural = "s" if n != 1 else ""
            return (
                f"{n} CRITICAL item{plural} from `/checklist` still open — resolve "
                "them in the spec documents, then re-run `/checklist` to confirm."
            )
        return "Run `/checklist` to generate the Spec Quality Checklist."
    if state == "current":
        return (
            f'"{step["label"]}" is generated and waiting on review — check with '
            f"`sdd review check --doc {step['doc_key']}`, or approve it above."
        )
    return f"Run `{step['command']}` to generate the {step['label']}."


def _later_doc_step_exists(remaining_steps: list[dict], docs_by_key: dict) -> bool:
    """True if any later non-skipped doc-kind step already exists on disk --
    signals that an earlier *optional* step was consciously bypassed rather
    than simply not reached yet, so it shouldn't be picked as the
    pipeline's 'next' action."""
    for s in remaining_steps:
        if s.get("skip"):
            continue
        if s["kind"] == "doc" and s["doc_key"] in docs_by_key:
            return True
    return False


def build_pipeline(
    docs: list[dict],
    tasks: dict,
    constitution: dict,
    service_docs: dict,
    plan_mode: str = "unified",
    scope: str | None = "pilot",
    feature: str = "this feature",
    applicable_extended: frozenset[str] = frozenset(),
    checklist_info: dict | None = None,
) -> dict:
    """The full command sequence for this feature (every step this scope/
    plan_mode can ever produce, including skipped ones with a reason),
    each resolved to done/current/upcoming from what's actually on disk —
    plus a single plain-language sentence for what to do next. Pure
    function of already-loaded state; safe to call on every dashboard poll.

    `service_docs` is keyed by doc key ("data-model", "security-design"),
    each value {"exists": bool, "status": str | None} — see
    _service_doc_info(). `applicable_extended` is the set of type-specific
    extended docs (component-spec/ux-flow/screen-spec) this project's type
    actually uses — see _applicable_extended_docs(). `checklist_info` is
    {"exists": bool, "critical_open": int | None} — see _checklist_info();
    defaults to "never run" so every existing call site (including tests)
    that predates this parameter still behaves exactly as before.
    """
    steps = (
        _micro_pipeline_steps()
        if scope is None
        else _standard_pipeline_steps(scope, plan_mode, applicable_extended)
    )
    docs_by_key = {d["key"]: d for d in docs}
    checklist_info = checklist_info or {"exists": False, "critical_open": None}

    resolved: list[dict] = []
    next_action: str | None = None
    next_step_id: str | None = None
    next_persona: dict | None = None
    for i, step in enumerate(steps):
        persona = _persona_hint(step["id"], feature, scope)
        if step.get("skip"):
            resolved.append({**step, "state": "skipped", "persona": persona})
            continue
        state = _step_state(
            step, docs_by_key, tasks, constitution, service_docs, checklist_info
        )
        resolved.append({**step, "state": state, "persona": persona})
        if state != "done" and next_action is None:
            # An *optional* step (e.g. checklist at pilot scope) whose doc
            # was never generated is still "upcoming", not "done" -- but if
            # a later mandatory doc already exists, the user consciously
            # moved past it rather than forgot it. Picking it here would
            # tell the dashboard to say "run /checklist" while the pipeline
            # diagram itself already shows a later step as current --
            # exactly the contradiction a user reported seeing.
            if (
                step.get("optional")
                and state == "upcoming"
                and _later_doc_step_exists(steps[i + 1 :], docs_by_key)
            ):
                continue
            next_action = _next_action_sentence(step, state, tasks, checklist_info)
            next_step_id = step["id"]
            # A doc "current"/awaiting-review isn't waiting to be *created* --
            # the ask templates are all creation-phrased ("create the BRD"),
            # which would misleadingly imply the doc doesn't exist yet. Only
            # attach the persona ask when it's actually about to be done.
            awaiting_review = step["kind"] == "doc" and state == "current"
            next_persona = None if awaiting_review else persona

    return {
        "steps": resolved,
        "next_step_id": next_step_id,
        "next_action": next_action or "All pipeline steps complete for this feature.",
        "next_persona": next_persona,
    }


def _parse_tasks(tasks_path: Path) -> dict:
    if not tasks_path.exists():
        return {
            "format": "none",
            "total": 0,
            "done": 0,
            "in_progress": 0,
            "not_started": 0,
            "items": [],
        }

    text = tasks_path.read_text(errors="replace", encoding="utf-8")
    lines = text.splitlines()
    items: list[dict] = []
    fmt = "full"

    i = 0
    while i < len(lines):
        m = _TASK_HEADING_RE.match(lines[i])
        if not m:
            i += 1
            continue
        task_id, title = m.group(1), m.group(2).strip()
        body: list[str] = []
        i += 1
        while i < len(lines) and not _TASK_HEADING_RE.match(lines[i]):
            body.append(lines[i])
            i += 1
        block = "\n".join(body)

        status_field = _TASK_STATUS_FIELD_RE.search(block)
        if status_field:
            fmt = "micro"
            status = status_field.group(1).strip()
        else:
            done_boxes = len([ln for ln in body if _CHECKBOX_DONE_RE.match(ln)])
            open_boxes = len([ln for ln in body if _CHECKBOX_OPEN_RE.match(ln)])
            total_boxes = done_boxes + open_boxes
            if total_boxes == 0:
                status = "Unknown"
            elif done_boxes == total_boxes:
                status = "Done"
            elif done_boxes == 0:
                status = "Not Started"
            else:
                status = "In Progress"

        satisfies_match = _SATISFIES_RE.search(block)
        fr_ids = _extract_ids(satisfies_match.group(1), "FR") if satisfies_match else []

        items.append(
            {"id": task_id, "title": title, "status": status, "fr_ids": fr_ids}
        )

    counts = {"done": 0, "in_progress": 0, "not_started": 0, "unknown": 0}
    for it in items:
        counts[_norm_task_status(it["status"])] += 1

    return {
        "format": fmt if items else "none",
        "total": len(items),
        "done": counts["done"],
        "in_progress": counts["in_progress"],
        "not_started": counts["not_started"] + counts["unknown"],
        "items": items,
    }


def _parse_brd_bo(brd_path: Path) -> dict:
    """Reads brd.md's §2 Business Objectives and §5 Business Requirements
    (Serves BO column) tables. Returns {'objectives': {BO-NNN: {objective,
    metric}}, 'br_to_bo': {BR-NNN: [BO-NNN, ...]}}. Both empty if brd.md
    doesn't exist yet, or still has unfilled template placeholders (a row
    starting with '{' is treated as never-generated, not a real BO/BR)."""
    try:
        text = brd_path.read_text(errors="replace", encoding="utf-8")
    except OSError:
        return {"objectives": {}, "br_to_bo": {}}
    lines = text.splitlines()

    objectives: dict[str, dict] = {}
    for cells in _table_rows_after_heading(lines, "Business Objectives"):
        # Template's canonical shape is 3 columns (ID | Objective | Success
        # Metric); some real docs split that into Metric + Target (4
        # columns). Accept either rather than assume one exact shape.
        if len(cells) not in (3, 4):
            continue
        bo_id, objective = cells[0], cells[1]
        metric = " / ".join(c for c in cells[2:] if c)
        if not bo_id.startswith("BO-") or "{" in bo_id:
            continue
        objectives[bo_id] = {"objective": objective, "metric": metric}

    br_to_bo: dict[str, list[str]] = {}
    for cells in _table_rows_after_heading(lines, "Business Requirements"):
        # Last column carries the BO reference regardless of its header
        # text ('Serves BO' in the current template, 'Satisfies' in some
        # existing docs) -- extracting BO-NNN tokens from it either way.
        if len(cells) != 4:
            continue
        br_id, serves_bo = cells[0], cells[3]
        if not br_id.startswith("BR-") or "{" in br_id:
            continue
        br_to_bo[br_id] = _extract_ids(serves_bo, "BO")

    return {"objectives": objectives, "br_to_bo": br_to_bo}


_UC_SECTION_RE = re.compile(r"^###\s+(UC-\d+)\b")
_UC_BR_LINE_RE = re.compile(
    r"\*\*(?:BR Traces|Trace|Business Rules Applied)\s*:?\*\*\s*(.+)", re.IGNORECASE
)
_UC_FR_LINE_RE = re.compile(
    r"\*\*(?:FR Traces[^*]*|Linked FR-NNN)\s*:?\*\*\s*(.+)", re.IGNORECASE
)


def _parse_uc_traces(uc_path: Path) -> dict:
    """Reads use-cases.md. Prefers the §2 Use Case Index table (BR Traces /
    FR Traces (SRD) columns). Real, hand-evolved docs sometimes lack that
    table entirely (older generations, or a narrative-only §3) -- in that
    case falls back to scanning each '### UC-NNN' section for a trace line
    ('**BR Traces:**', '**Trace:**', or '**Business Rules Applied:**' for
    BRs; '**FR Traces...**' or '**Linked FR-NNN:**' for FRs). Returns
    {UC-NNN: {'br_ids': [...], 'fr_ids': [...]}} -- fr_ids is [] until
    /specify-srd has backfilled the FR trace."""
    try:
        text = uc_path.read_text(errors="replace", encoding="utf-8")
    except OSError:
        return {}
    lines = text.splitlines()
    result: dict[str, dict] = {}
    for cells in _table_rows_after_heading(lines, "Use Case Index"):
        if len(cells) != 6:
            continue
        uc_id, _title, _actors, _priority, br_traces, fr_traces = cells
        if not uc_id.startswith("UC-") or "{" in uc_id:
            continue
        result[uc_id] = {
            "br_ids": _extract_ids(br_traces, "BR"),
            "fr_ids": _extract_ids(fr_traces, "FR"),
        }
    if result:
        return result

    current: str | None = None
    section_lines: list[str] = []

    def _flush() -> None:
        if current is None:
            return
        br_ids: list[str] = []
        fr_ids: list[str] = []
        for line in section_lines:
            m = _UC_BR_LINE_RE.search(line)
            if m:
                br_ids.extend(
                    i for i in _extract_ids(m.group(1), "BR") if i not in br_ids
                )
            m = _UC_FR_LINE_RE.search(line)
            if m:
                fr_ids.extend(
                    i for i in _extract_ids(m.group(1), "FR") if i not in fr_ids
                )
        if current not in result:
            result[current] = {"br_ids": br_ids, "fr_ids": fr_ids}
        else:
            result[current]["br_ids"].extend(
                i for i in br_ids if i not in result[current]["br_ids"]
            )
            result[current]["fr_ids"].extend(
                i for i in fr_ids if i not in result[current]["fr_ids"]
            )

    for line in lines:
        m = _UC_SECTION_RE.match(line.strip())
        if m:
            _flush()
            current = m.group(1)
            section_lines = []
        elif current is not None:
            section_lines.append(line)
    _flush()
    return result


def _parse_srd_fr(srd_path: Path) -> dict:
    """Reads srd.md's Functional Requirements table plus (if present) its
    §4 Use Case Coverage table. Handles both the canonical 5-column §2
    shape (ID | Requirement | UC Trace | Source | Priority -- 'Source'
    carries BR-NNN, 'UC Trace' carries UC-NNN) and a 4-column variant seen
    in some existing docs (ID | Requirement | Priority | Satisfies --
    'Satisfies' carries BR-NNN, no UC Trace column). Use Case Coverage
    rows (FR-NNN | UC Trace | Coverage Confirmed?) supplement FR->UC links
    when §2 lacks one. Returns {FR-NNN: {'br_ids': [...], 'uc_ids': [...]}}."""
    try:
        text = srd_path.read_text(errors="replace", encoding="utf-8")
    except OSError:
        return {}
    lines = text.splitlines()
    result: dict[str, dict] = {}
    for cells in _table_rows_after_heading(lines, "Functional Requirements"):
        if len(cells) == 5:
            fr_id, _req, uc_trace, source, _priority = cells
        elif len(cells) == 4:
            fr_id, _req, _priority, source = cells
            uc_trace = ""
        else:
            continue
        if not fr_id.startswith("FR-") or "{" in fr_id:
            continue
        result[fr_id] = {
            "br_ids": _extract_ids(source, "BR"),
            "uc_ids": _extract_ids(uc_trace, "UC"),
        }
    for cells in _table_rows_after_heading(lines, "Use Case Coverage"):
        if len(cells) != 3:
            continue
        fr_id, uc_trace, _confirmed = cells
        if not fr_id.startswith("FR-") or "{" in fr_id:
            continue
        entry = result.setdefault(fr_id, {"br_ids": [], "uc_ids": []})
        for uc_id in _extract_ids(uc_trace, "UC"):
            if uc_id not in entry["uc_ids"]:
                entry["uc_ids"].append(uc_id)
    return result


_BO_CLOSURE_CHECKBOX_RE = re.compile(r"\[([ xX])\]\s*(Yes|No|Pending)")


def _parse_release_bo_closure(release_path: Path) -> dict:
    """Parses release.md 'Business Objective Closure' table -- the actual
    measured business outcome, as opposed to build_bo_rollup's own
    task-completion-derived status. Returns {BO-NNN: {"outcome": "met" /
    "not_met" / "pending" / None, "measured_result": str}}. Best-effort:
    {} if release.md doesn't exist yet or the table isn't found -- most
    features haven't reached /release yet, that's normal, not an error."""
    try:
        text = release_path.read_text(errors="replace", encoding="utf-8")
    except OSError:
        return {}
    lines = text.splitlines()
    result: dict[str, dict] = {}
    for cells in _table_rows_after_heading(lines, "Business Objective Closure"):
        if len(cells) != 4:
            continue
        bo_id, _metric, measured_result, met = cells
        if not bo_id.startswith("BO-") or "{" in bo_id:
            continue
        outcome = None
        checked = [
            label
            for box, label in _BO_CLOSURE_CHECKBOX_RE.findall(met)
            if box.lower() == "x"
        ]
        if "Yes" in checked:
            outcome = "met"
        elif "No" in checked:
            outcome = "not_met"
        elif "Pending" in checked:
            outcome = "pending"
        result[bo_id] = {"outcome": outcome, "measured_result": measured_result}
    return result


def build_bo_rollup(root: Path, feature: str) -> list[dict]:
    """Chains BO (brd.md §2) -> BR (brd.md §5 'Serves BO' column) -> FR
    (srd.md Functional Requirements 'Source'/'Satisfies' column, which
    cites the BR it implements) -> TASK (tasks.md 'Satisfies:' field +
    completion status) to compute how much of a business objective's work
    is actually done. UC-NNN for display is gathered from both directions
    -- use-cases.md's own 'BR Traces' column, and srd.md's 'UC Trace'
    column/§4 Use Case Coverage table -- since real documents don't
    reliably backfill use-cases.md's FR Traces column (that's a manual
    /specify-uc re-run after /specify-srd, and it's often skipped), so the
    BR->FR link from srd.md is the more reliable bridge to task
    completion; the UC->FR link is used only when present, as a bonus.

    Each rollup dict also carries "outcome"/"measured_result", read
    separately from release.md's own Business Objective Closure table
    (see _parse_release_bo_closure) -- the actual measured business
    result, once /release has run, alongside (never replacing) "status"
    which stays purely task-completion-derived so existing Done/In
    Progress/Not Started badge logic keeps working unchanged.

    Read-only, best-effort: any link not yet generated (use-cases.md or
    srd.md not written yet, tasks.md doesn't exist yet) just means fewer
    tasks are counted, never an error. Returns [] if brd.md has no BO-NNN
    rows yet (nothing to roll up)."""
    feature_dir = root / ".specify" / "features" / feature
    brd = _parse_brd_bo(feature_dir / "brd.md")
    if not brd["objectives"]:
        return []

    uc_traces = _parse_uc_traces(feature_dir / "use-cases.md")
    fr_meta = _parse_srd_fr(feature_dir / "srd.md")
    tasks = _parse_tasks(feature_dir / "tasks.md")
    bo_closure = _parse_release_bo_closure(feature_dir / "release.md")

    bo_to_br = _bo_to_br_index(brd["objectives"], brd["br_to_bo"])
    br_to_uc = _br_to_uc_index(uc_traces)
    br_to_fr, fr_to_uc = _fr_indexes(fr_meta)
    fr_to_tasks = _fr_to_tasks_index(tasks["items"])

    rollup = []
    for bo_id, meta in brd["objectives"].items():
        br_ids = bo_to_br.get(bo_id, [])
        uc_ids, fr_ids = _bo_uc_and_fr_ids(
            br_ids, br_to_uc, br_to_fr, uc_traces, fr_to_uc
        )
        related_tasks = _bo_related_tasks(fr_ids, fr_to_tasks)
        status_label, total, done = _bo_task_status(related_tasks)

        closure = bo_closure.get(bo_id, {})
        rollup.append(
            {
                "bo_id": bo_id,
                "objective": meta["objective"],
                "metric": meta["metric"],
                "uc_ids": uc_ids,
                "task_count": total,
                "tasks_done": done,
                "percent_done": round(100 * done / total) if total else 0,
                "status": status_label,
                "outcome": closure.get("outcome"),
                "measured_result": closure.get("measured_result"),
            }
        )
    return rollup


def _bo_to_br_index(
    objectives: dict, br_to_bo: dict[str, list[str]]
) -> dict[str, list[str]]:
    """Reverses brd.md §5's BR->BO ("Serves BO") column into BO->[BR]."""
    bo_to_br: dict[str, list[str]] = {bo_id: [] for bo_id in objectives}
    for br_id, bo_ids in br_to_bo.items():
        for bo_id in bo_ids:
            if bo_id in bo_to_br:
                bo_to_br[bo_id].append(br_id)
    return bo_to_br


def _br_to_uc_index(uc_traces: dict) -> dict[str, list[str]]:
    """Reverses use-cases.md's own "BR Traces" column into BR->[UC]."""
    br_to_uc: dict[str, list[str]] = {}
    for uc_id, trace in uc_traces.items():
        for br_id in trace["br_ids"]:
            br_to_uc.setdefault(br_id, []).append(uc_id)
    return br_to_uc


def _fr_indexes(
    fr_meta: dict,
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """From srd.md's FR metadata (Source/Satisfies BR column, UC Trace
    column), builds BR->[FR] and FR->[UC] in one pass over the same data."""
    br_to_fr: dict[str, list[str]] = {}
    fr_to_uc: dict[str, list[str]] = {}
    for fr_id, meta in fr_meta.items():
        for br_id in meta["br_ids"]:
            br_to_fr.setdefault(br_id, []).append(fr_id)
        for uc_id in meta["uc_ids"]:
            fr_to_uc.setdefault(fr_id, []).append(uc_id)
    return br_to_fr, fr_to_uc


def _fr_to_tasks_index(task_items: list[dict]) -> dict[str, list[dict]]:
    """Reverses tasks.md's "Satisfies:" field into FR->[task]."""
    fr_to_tasks: dict[str, list[dict]] = {}
    for item in task_items:
        for fr_id in item.get("fr_ids", []):
            fr_to_tasks.setdefault(fr_id, []).append(item)
    return fr_to_tasks


def _bo_uc_and_fr_ids(
    br_ids: list[str],
    br_to_uc: dict[str, list[str]],
    br_to_fr: dict[str, list[str]],
    uc_traces: dict,
    fr_to_uc: dict[str, list[str]],
) -> tuple[list[str], list[str]]:
    """UC_ids and FR_ids for one BO, given its BR_ids -- order-preserving,
    de-duplicated (each is built as an insertion-ordered set via a plain
    list + "not in" check, not a real set, since the order feeds display).
    The two lists are interdependent, computed in three passes in this
    specific order: UC_ids from BR_to_UC first, then FR_ids from BR_to_FR
    plus a bonus backfill from any of those UC_ids' own FR Traces (catches
    an FR srd.md's table missed), then UC_ids gets a final backfill from
    those FR_ids' own UC Trace column."""
    uc_ids: list[str] = []
    for br_id in br_ids:
        for uc_id in br_to_uc.get(br_id, []):
            if uc_id not in uc_ids:
                uc_ids.append(uc_id)

    fr_ids: list[str] = []
    for br_id in br_ids:
        for fr_id in br_to_fr.get(br_id, []):
            if fr_id not in fr_ids:
                fr_ids.append(fr_id)
    # Bonus: FR Traces already backfilled in use-cases.md for one of
    # this BO's UCs -- catches an FR that srd.md's own table missed.
    for uc_id in uc_ids:
        for fr_id in uc_traces.get(uc_id, {}).get("fr_ids", []):
            if fr_id not in fr_ids:
                fr_ids.append(fr_id)
    for fr_id in fr_ids:
        for uc_id in fr_to_uc.get(fr_id, []):
            if uc_id not in uc_ids:
                uc_ids.append(uc_id)

    return uc_ids, fr_ids


def _bo_related_tasks(
    fr_ids: list[str], fr_to_tasks: dict[str, list[dict]]
) -> dict[str, dict]:
    """All tasks satisfying any of this BO's FR_ids, deduplicated by task id."""
    related_tasks: dict[str, dict] = {}
    for fr_id in fr_ids:
        for t in fr_to_tasks.get(fr_id, []):
            related_tasks[t["id"]] = t
    return related_tasks


def _bo_task_status(related_tasks: dict[str, dict]) -> tuple[str, int, int]:
    """(status_label, total, done) for one BO's related tasks."""
    total = len(related_tasks)
    norm_counts = {"done": 0, "in_progress": 0}
    for t in related_tasks.values():
        n = _norm_task_status(t["status"])
        if n in norm_counts:
            norm_counts[n] += 1
    done = norm_counts["done"]

    if total == 0:
        status_label = "Not Started"
    elif done == total:
        status_label = "Done"
    elif done > 0 or norm_counts["in_progress"] > 0:
        status_label = "In Progress"
    else:
        status_label = "Not Started"

    return status_label, total, done


def _parse_command_log_sources(text: str) -> dict:
    """Tally Per-Command Log rows by Source (Real vs Estimated), for the
    dashboard's Token Usage card. Mirrors token_log.py's _parse_table_row
    column handling (8-column current format with Source, or legacy
    7-column rows that pre-date the column and are always Estimated) so
    the two never drift apart.
    """
    real = estimated = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) not in (7, 8) or not cells[0].isdigit():
            continue
        source = cells[6] if len(cells) == 8 else "Estimated"
        if source.startswith("Real"):
            real += 1
        else:
            estimated += 1
    return {"real_commands": real, "estimated_commands": estimated}


def _parse_token_usage(path: Path) -> dict | None:
    if not path.exists():
        return None
    text = path.read_text(errors="replace", encoding="utf-8")
    values: dict[str, str] = {}
    for m in _RUNNING_TOTAL_ROW_RE.finditer(text):
        values[m.group(1)] = m.group(2).strip()
    sources = _parse_command_log_sources(text)
    if not values:
        return {
            "exists": True,
            "total_input": None,
            "total_output": None,
            "total_cost": None,
            "commands_logged": None,
            "last_updated": None,
            **sources,
        }
    return {
        "exists": True,
        "total_input": values.get("Total Input Tokens")
        or values.get("Total Est. Input Tokens"),
        "total_output": values.get("Total Output Tokens")
        or values.get("Total Est. Output Tokens"),
        "total_cost": values.get("Total Cost (USD)")
        or values.get("Total Est. Cost (USD)"),
        "commands_logged": values.get("Commands logged"),
        "last_updated": values.get("Last updated"),
        **sources,
    }


_TEMPLATE_PLACEHOLDER_RE = re.compile(r"\{[a-z][a-zA-Z0-9 _/]*\}")


def _constitution_status(root: Path) -> dict:
    path = root / ".specify" / "memory" / "constitution.md"
    if not path.exists():
        return {"exists": False, "gate1_inferred": "unknown"}
    # constitution.md is scaffolded by `sdd init` for every project (Part 1
    # boilerplate + a Part 2 template full of {extracted from context} /
    # {derived} / {date} placeholders) — the file existing on disk does NOT
    # mean /specify has run yet. Only treat Part 2 as generated once those
    # literal placeholders are gone (the agent replaces every one of them
    # when it fills Part 2, even in DRAFT form pre-GATE-1).
    text = path.read_text(errors="replace", encoding="utf-8")
    part2_marker = text.find("PART 2")
    part2_text = text[part2_marker:] if part2_marker != -1 else text
    if _TEMPLATE_PLACEHOLDER_RE.search(part2_text):
        return {"exists": True, "part2_generated": False, "gate1_inferred": "unknown"}
    # No machine-readable Draft/Finalized flag is written into constitution.md
    # by design (GATE-1 confirmation happens in chat) — infer from whether any
    # downstream feature doc exists, since the workflow can't produce those
    # before GATE-1 passes.
    #
    # token-usage.md is NOT such a doc, despite living in the same directory
    # — it's opt-in telemetry (token-pricing.yml.example) appended to by
    # every command including /specify itself and even /create-context,
    # which both run before GATE-1 can possibly pass. Same for tasks.md
    # (already excluded below) and *.summary.md. Without this exclusion,
    # any project with token logging enabled shows GATE-1 as "passed" the
    # instant /specify finishes, before the user has reviewed a single row.
    _NON_DOWNSTREAM_NAMES = {"tasks.md", "token-usage.md"}
    features_dir = root / ".specify" / "features"
    any_downstream = False
    if features_dir.is_dir():
        for feature_dir in features_dir.iterdir():
            if not feature_dir.is_dir():
                continue
            if any(
                p.name not in _NON_DOWNSTREAM_NAMES
                and not p.name.endswith(".summary.md")
                for p in feature_dir.glob("*.md")
            ):
                any_downstream = True
                break
            if (feature_dir / "tasks.md").exists():
                any_downstream = True
                break
    return {
        "exists": True,
        "part2_generated": True,
        "gate1_inferred": "passed" if any_downstream else "pending_or_unknown",
    }


def _local_base_url() -> str | None:
    """Best-effort Atlassian base_url from ~/.sdd/config.yml — a local file
    read only (no network, no credential check), so this is safe to call
    on every dashboard poll. Returns None if unconfigured/ambiguous."""
    try:
        from sdd.utils.atlassian_auth import load_profile
        from sdd.utils.integrations import IntegrationsConfigError, load_integrations

        profile_name = None
        try:
            profile_name = load_integrations().profile
        except (FileNotFoundError, IntegrationsConfigError):
            pass
        return load_profile(profile_name).base_url
    except Exception:
        return None


def _jira_key_from(value) -> str | None:
    """keys.yml's actual shape (written by jira.py's _save_keys_summary):
    epic is a plain string, stories/tasks are {id: jira_key} dicts. Also
    tolerate a {"jira_key": "..."} dict per entry, in case an older or
    hand-edited keys.yml uses that shape — never assume either shape and
    never crash on whichever one is actually on disk."""
    if isinstance(value, str) and value:
        return value
    if isinstance(value, dict):
        k = value.get("jira_key")
        return k if isinstance(k, str) and k else None
    return None


def _local_jira_links(root: Path, feature: str, base_url: str | None) -> dict:
    """Jira Epic/Story/Task links already persisted by the progressive
    export (docs/jira/{feature}/keys.yml, written by `sdd jira push`). No
    network call — review-gate ticket links (from `sdd review submit`/
    `apply`) live in a separate file, see _local_review_links() below.

    `feature` is traversal-checked via safe_feature_path() here too, even
    though every current caller already validates it upstream (dashboard.py's
    _SAFE_TOKEN regex on the HTTP path, plain CLI-arg trust on the `sdd
    status` path) -- this way the guard doesn't depend on every future
    caller remembering to check first (CodeQL py/path-injection)."""
    result: dict = {"epic": None, "stories": [], "tasks": []}
    try:
        keys_path = safe_feature_path(root / "docs" / "jira", feature) / "keys.yml"
    except ValueError:
        return result
    if not keys_path.exists():
        return result
    try:
        keys = yaml.safe_load(keys_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return result

    def _link(jira_key: str) -> dict:
        return {
            "key": jira_key,
            "url": f"{base_url}/browse/{jira_key}" if base_url else None,
        }

    def _collect(raw) -> list[dict]:
        items = raw.values() if isinstance(raw, dict) else (raw or [])
        return [_link(k) for k in (_jira_key_from(item) for item in items) if k]

    epic_key = _jira_key_from(keys.get("epic"))
    if epic_key:
        result["epic"] = _link(epic_key)
    result["stories"] = _collect(keys.get("stories"))
    result["tasks"] = _collect(keys.get("tasks"))
    return result


def _local_confluence_links(root: Path, base_url: str | None) -> dict:
    """Confluence page links already persisted by `sdd confluence push`/
    `draft`/`sdd review submit`/`apply` (all write to the same
    .specify/.confluence-drafts.json). No network call. Project-wide, not
    per-feature (the drafts file isn't feature-scoped)."""
    drafts_path = root / ".specify" / ".confluence-drafts.json"
    if not drafts_path.exists():
        return {}
    try:
        drafts = json.loads(drafts_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    links = {}
    for doc_key, entry in drafts.items():
        page_id = entry.get("page_id")
        if not page_id:
            continue
        links[doc_key] = {
            "title": entry.get("title"),
            "url": f"{base_url}/wiki/pages/viewpage.action?pageId={page_id}"
            if base_url
            else None,
        }
    return links


def _local_review_links(root: Path, base_url: str | None) -> dict:
    """Review-gate Jira ticket links persisted by `sdd review submit`/
    `apply` (.specify/.jira-review-links.json). No network call -- mirrors
    _local_confluence_links' pattern (and its same not-feature-scoped
    limitation: the file has no feature keying) so the dashboard's Jira
    pill can show instantly the same way the Confluence one already does,
    instead of staying blank until the live /api/review-links check runs."""
    links_path = root / ".specify" / ".jira-review-links.json"
    if not links_path.exists():
        return {}
    try:
        raw = json.loads(links_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    links = {}
    for doc_key, entry in raw.items():
        key = entry.get("key") if isinstance(entry, dict) else None
        if not key:
            continue
        links[doc_key] = {
            "key": key,
            "url": f"{base_url}/browse/{key}" if base_url else None,
        }
    return links


def build_feature_status(
    root: Path,
    feature: str,
    constitution: dict | None = None,
    plan_mode: str = "unified",
    scope: str | None = "pilot",
    project_type: str | None = None,
) -> dict:
    feature_dir = root / ".specify" / "features" / feature
    docs = _feature_docs(root, feature)
    base_url = _local_base_url()
    tasks = _parse_tasks(feature_dir / "tasks.md")
    service_docs = {
        "data-model": _service_doc_info(root, "data-model"),
        "security-design": _service_doc_info(root, "security-design"),
    }
    return {
        "name": feature,
        "docs": docs,
        "current_stage": _current_stage(docs, feature, scope),
        "tasks": tasks,
        "timeline": _feature_timeline(docs),
        "business_objectives": build_bo_rollup(root, feature),
        "token_usage": _parse_token_usage(feature_dir / "token-usage.md"),
        "local_links": {
            "jira": _local_jira_links(root, feature, base_url),
            "confluence": _local_confluence_links(root, base_url),
            "jira_review": _local_review_links(root, base_url),
        },
        "pipeline": build_pipeline(
            docs,
            tasks,
            constitution or _constitution_status(root),
            service_docs,
            plan_mode,
            scope,
            feature=feature,
            applicable_extended=frozenset(
                _applicable_extended_docs(root, project_type)
            ),
            checklist_info=_checklist_info(root, feature),
        ),
    }


def build_project_status(root: str | Path = ".") -> dict:
    """Pure, read-only snapshot of .specify/ — safe to call repeatedly (e.g.
    on every dashboard poll) since it does no caching and no writes."""
    root = Path(root)
    manifest = read_manifest(str(root / ".specify" / "manifest.yml")) or {}
    proj = manifest.get("project") or {}
    scope = proj.get("scope")  # absent for sdd-micro
    plan_mode = manifest.get("plan_mode") or "unified"
    project_type = manifest.get("project_type")  # sdd-universal only
    constitution = _constitution_status(root)

    features = [
        build_feature_status(
            root,
            f,
            constitution=constitution,
            plan_mode=plan_mode,
            scope=scope,
            project_type=project_type,
        )
        for f in _list_feature_names(root)
    ]

    # Cross-feature Business Objectives rollup: each feature's brd.md has
    # its own independent BO-NNN numbering (no service-level BRD -- every
    # feature is deliberately self-contained), so BO-002 in one feature and
    # BO-002 in another are unrelated. Tag each with its feature so the
    # dashboard can show one consolidated list without id collisions --
    # same trick a Jira key (PROJ-123) uses for the same reason.
    business_objectives = [
        {**bo, "feature": f["name"]}
        for f in features
        for bo in f["business_objectives"]
    ]

    # Living/service-level docs (Data Model, Security Design) shown once,
    # project-level -- not sdd-micro, which has no such concept (scope is
    # None there, same guard _micro_pipeline_steps() uses). See
    # _service_level_docs()'s docstring for why current_feature is used
    # for the comments-store key.
    base_url = _local_base_url()
    living_documents = (
        _service_level_docs(root, proj.get("feature") or "", scope)
        if scope is not None
        else []
    )

    return {
        "project": {
            "name": proj.get("name") or None,
            "current_feature": proj.get("feature") or None,
            "scope": scope,
            "plan_mode": plan_mode,
            "project_type": manifest.get("project_type"),
            "workflow_mode": manifest.get("workflow_mode"),
            "sdd_version": manifest.get("sdd_version"),
        },
        "constitution": constitution,
        "features": features,
        "business_objectives": business_objectives,
        "living_documents": living_documents,
        "living_local_links": {
            "confluence": _local_confluence_links(root, base_url),
            "jira_review": _local_review_links(root, base_url),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
