"""Build a read-only project status snapshot from .specify/ on disk.

No network calls, no Jira/Confluence dependency — works for chat, local,
and jira review modes alike, since "Status:" headers inside .md files are
the authoritative gate in every mode (see CLAUDE.md "Document Review
Gates"). This is what `sdd dashboard` and `sdd status` render.
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from sdd.utils.manifest import read_manifest

# Best-effort generic pipeline order. Not every pack/scope/plan_mode
# generates every doc — this is used only to order what *does* exist and
# to guess "next" from the last-known doc found on disk; unknown doc
# files are still shown, just appended after this list.
PIPELINE_DOCS: list[tuple[str, str]] = [
    ("brd", "BRD"),
    ("use-cases", "Use Cases"),
    ("srd", "SRD"),
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
_TASK_HEADING_RE = re.compile(r"^#{2,3}\s+(TASK-\d+)\s*[—–-]+\s*(.+)$")
_TASK_STATUS_FIELD_RE = re.compile(r"\*\*Status:\*\*\s*(.+)")
_CHECKBOX_DONE_RE = re.compile(r"^\s*[-*]\s+\[[xX]\]")
_CHECKBOX_OPEN_RE = re.compile(r"^\s*[-*]\s+\[\s\]")
_RUNNING_TOTAL_ROW_RE = re.compile(r"\|\s*(Total Est\. Input Tokens|Total Est\. Output Tokens|"
                                    r"Total Est\. Cost \(USD\)|Commands logged|Last updated)\s*\|\s*(.+?)\s*\|")


def _doc_status(path: Path) -> str | None:
    """First 'Status: X' value found in the file, or None if unreadable/absent."""
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return None
    m = _STATUS_RE.search(text)
    return m.group(1).strip() if m else None


def _list_feature_names(root: Path) -> list[str]:
    features_dir = root / ".specify" / "features"
    if not features_dir.is_dir():
        return []
    return sorted(p.name for p in features_dir.iterdir() if p.is_dir())


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
        return yaml.safe_load(path.read_text()) or {}
    except Exception:
        return {}


def _dashboard_comments(root: Path, feature: str, doc: str) -> list:
    path = root / _DASHBOARD_COMMENTS_PATH
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except Exception:
        return []
    return data.get(f"{feature}/{doc}", [])


def _feature_docs(root: Path, feature: str) -> list[dict]:
    feature_dir = root / ".specify" / "features" / feature
    docs: list[dict] = []
    md_files = sorted(
        (p for p in feature_dir.glob("*.md")
         if not p.name.endswith(".summary.md") and p.stem not in _NON_PIPELINE_DOCS),
        key=lambda p: _PIPELINE_ORDER.get(p.stem, 999),
    )
    approvals = _local_approvals(root)
    for path in md_files:
        key = path.stem
        docs.append({
            "key": key,
            "label": _PIPELINE_LABELS.get(key, key.replace("-", " ").title()),
            "exists": True,
            "status": _doc_status(path),
            "path": str(path),
            "local_approval": approvals.get(key),
            "comments": _dashboard_comments(root, feature, key),
        })
    return docs


def _current_stage(docs: list[dict], feature: str = "this feature",
                    scope: str | None = "pilot") -> dict:
    """Last pipeline-ordered doc that exists, plus a best-effort 'next' guess
    and (when the next doc has one) its Virtual Team persona hint. No hint
    for the "(awaiting approval)" case -- the ask templates are all
    creation-phrased and the doc already exists, waiting on a human
    reviewer, not on the persona who'd create it."""
    known = [d for d in docs if d["key"] in _PIPELINE_ORDER]
    if not known:
        first_key = PIPELINE_DOCS[0][0] if PIPELINE_DOCS else None
        return {
            "doc": None, "status": None,
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
        "persona": (None if awaiting_approval or not next_key
                    else _persona_hint(next_key, feature, scope)),
    }


def persona_for(step_id: str, feature: str, scope: str | None) -> dict | None:
    """Public wrapper around the pipeline's Virtual Team persona lookup, for
    callers outside build_pipeline/build_feature_status that want the same
    hint (e.g. `sdd review status`, which reads document_reviews keys
    directly rather than going through the pipeline)."""
    return _persona_hint(step_id, feature, scope)


def _service_docs_exist(root: Path) -> bool:
    """Whether any living/service-level spec doc (data-model, security-design,
    api-spec, ...) has been generated yet — these live at .specify/service/,
    not .specify/features/{feature}/, so _feature_docs() never sees them.
    Existence-only check (not per-doc status) since which exact docs apply
    is project-type-dependent; see build_pipeline()'s "extended-specs" step."""
    service_dir = root / ".specify" / "service"
    if not service_dir.is_dir():
        return False
    return any(p.suffix == ".md" and not p.name.endswith(".summary.md")
               for p in service_dir.glob("*.md"))


_SCOPE_ORDER = {"pilot": 0, "mvp": 1, "full": 2}


def _scope_at_least(scope: str | None, minimum: str) -> bool:
    return _SCOPE_ORDER.get(scope or "pilot", 0) >= _SCOPE_ORDER[minimum]


# Virtual Team roster (see each pack's CLAUDE.md "Virtual Team — Address by
# Name" table) -- name -> role, for the persona hint shown in the tooltip
# and next-action box. sdd-micro has no Virtual Team at all (its steps use
# id "task", not "tasks", and are never looked up here since callers pass
# scope=None for micro).
_PERSONA_ROLE = {
    "Maya":  "Business Analyst",
    "Rex":   "Requirements Engineer",
    "Ava":   "Software Architect",
    "Leo":   "Lead Developer",
    "Kai":   "Engineering Manager",
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
    "brd":            ("Maya",  "create the BRD for {feature}"),
    "use-cases":      ("Maya",  "write the use cases for {feature}"),
    "srd":            ("Rex",   "write the SRD for {feature}"),
    "extended-specs": ("Ava",   "write the data model and security design for {feature}"),
    "checklist":      ("Quinn", "run the spec quality checklist for {feature}"),
    "validate":       ("Maya",  "validate {feature}"),
    "analyze":        ("Ava",   "run the cross-doc analysis on {feature}"),
    "clarify":        ("Rex",   "clarify the open questions on {feature}"),
    "design":         ("Ava",   "design {feature}"),
    "arch":           ("Ava",   "design the architecture for {feature}"),
    "hld":            ("Ava",   "write the high-level design for {feature}"),
    "adr":            ("Ava",   "record the architecture decisions for {feature}"),
    "lld":            ("Leo",   "write the low-level design for {feature}"),
    "stories":        ("Kai",   "break {feature} into stories"),
    "tasks":          ("Kai",   "break {feature} into tasks"),
    "smoke-tests":    ("Kai",   "write smoke tests for {feature}"),
    "qa-testcases":   ("Kai",   "write QA test cases for {feature}"),
    "implement":      ("Leo",   "implement the next task for {feature}"),
    "release":        ("Riley", "plan the release for {feature}"),
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
    return {"name": name, "role": _PERSONA_ROLE[name], "ask": template.format(feature=feature)}


def _standard_pipeline_steps(scope: str | None, plan_mode: str) -> list[dict]:
    """The full command sequence for every pack except sdd-micro (backend,
    frontend-spa, mobile, fullstack, universal all share this exact
    top-level flow — see each pack's own CLAUDE.md header). Every step is
    always included, even ones this scope/plan_mode skips, so the dashboard
    can show *why* a step is absent rather than silently omitting it —
    the skip reasons mirror CLAUDE.md's "Scope Reference" table exactly.
    """
    mvp_plus = _scope_at_least(scope, "mvp")
    separate = plan_mode == "separate"
    pilot = (scope or "pilot") == "pilot"

    def doc(id_, command, label, doc_key, skip=None, optional=False):
        return {"id": id_, "command": command, "label": label, "kind": "doc",
                "doc_key": doc_key, "skip": skip, "optional": optional}

    return [
        {"id": "specify", "command": "/specify", "label": "Constitution (Part 2)", "kind": "constitution"},
        {"id": "gate1", "command": None, "label": "GATE-1 — Constitution Finalized", "kind": "manual_gate"},
        doc("brd", "/specify-brd", "Business Requirements Document", "brd"),
        doc("use-cases", "/specify-uc", "Use Case Specification", "use-cases"),
        doc("srd", "/specify-srd", "Software Requirements Document", "srd"),
        {"id": "extended-specs", "command": "/specify-doc {name}",
         "label": "Extended Specs (Data Model, Security, ...)", "kind": "service_docs",
         "skip": None if mvp_plus else "pilot scope"},
        doc("checklist", "/checklist", "Spec Quality Checklist", "checklist", optional=pilot),
        doc("validate", "/validate", "Validate", "validate"),
        doc("analyze", "/analyze", "Cross-Doc Analysis", "analyze"),
        doc("clarify", "/clarify", "Clarify Ambiguities", "clarify"),
        doc("design", "/plan-design", "Design (Architecture + HLD + API)", "design",
            skip=None if not separate else "separate plan mode"),
        doc("arch", "/plan-arch", "Architecture", "arch",
            skip=None if separate else "unified plan mode"),
        doc("hld", "/plan-hld", "High-Level Design", "hld",
            skip=None if separate else "unified plan mode"),
        doc("adr", "/plan-adr", "Architecture Decision Records", "adr",
            skip=("unified plan mode" if not separate else (None if mvp_plus else "pilot scope"))),
        doc("lld", "/plan-lld", "Low-Level Design", "lld", skip=None if mvp_plus else "pilot scope"),
        doc("stories", "/task", "User Stories", "stories"),
        doc("tasks", "/task", "Task Breakdown", "tasks"),
        doc("smoke-tests", "/task", "Smoke Tests (≤10 cases)", "smoke-tests", skip=None if pilot else "mvp+ scope"),
        doc("qa-testcases", "/task", "QA Test Cases", "qa-testcases", skip="pilot scope" if pilot else None),
        {"id": "implement", "command": "/implement", "label": "Implementation (per task)", "kind": "tasks_progress"},
        doc("runbook", "(generated by /implement)", "Runbook", "runbook", skip=None if mvp_plus else "pilot scope"),
        doc("release", "/release", "Release Plan & Go/No-Go", "release"),
    ]


def _micro_pipeline_steps() -> list[dict]:
    """sdd-micro's only 3 commands — see its CLAUDE.md header. No scope,
    no review-gated spec docs; identified by scope being absent on the
    manifest (sdd-micro's manifest.yml has no project.scope field)."""
    return [
        {"id": "specify", "command": "/specify", "label": "Constitution (Confirmed)", "kind": "constitution"},
        {"id": "gate1", "command": None, "label": "GATE-1 — Constitution Confirmed", "kind": "manual_gate"},
        {"id": "task", "command": "/task", "label": "Task Breakdown", "kind": "doc", "doc_key": "tasks", "skip": None},
        {"id": "implement", "command": "/implement", "label": "Implementation", "kind": "tasks_progress"},
    ]


def _step_state(step: dict, docs_by_key: dict, tasks: dict, constitution: dict, service_docs_exist: bool) -> str:
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
    if kind == "service_docs":
        return "done" if service_docs_exist else "upcoming"
    if kind == "tasks_progress":
        if tasks["total"] == 0:
            return "upcoming"
        return "done" if tasks["done"] == tasks["total"] else "current"
    doc = docs_by_key.get(step["doc_key"])
    if not doc:
        return "upcoming"
    status = (doc.get("status") or "").lower()
    return "done" if "approved" in status else "current"


def _next_action_sentence(step: dict, state: str, tasks: dict) -> str:
    kind = step["kind"]
    if kind == "constitution":
        return "Run `/specify` to generate the project constitution."
    if kind == "manual_gate":
        return ('Review and finalize constitution Part 2 (Tech Stack, Core '
                'Principles, Domain Rules, Never Do), then tell your agent: '
                '"Constitution Part 2 finalized."')
    if kind == "service_docs":
        return "Run `/specify-doc {name}` for each extended spec your scope requires (e.g. data-model, security)."
    if kind == "tasks_progress":
        if state == "upcoming":
            return "Run `/task` to break this feature into tasks, then `/implement` to start building."
        return f"Run `/implement` to continue — {tasks['done']}/{tasks['total']} tasks done."
    if state == "current":
        return (f'"{step["label"]}" is generated and waiting on review — check with '
                f'`sdd review check --doc {step["doc_key"]}`, or approve it above.')
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


def build_pipeline(docs: list[dict], tasks: dict, constitution: dict, service_docs_exist: bool,
                    plan_mode: str = "unified", scope: str | None = "pilot",
                    feature: str = "this feature") -> dict:
    """The full command sequence for this feature (every step this scope/
    plan_mode can ever produce, including skipped ones with a reason),
    each resolved to done/current/upcoming from what's actually on disk —
    plus a single plain-language sentence for what to do next. Pure
    function of already-loaded state; safe to call on every dashboard poll.
    """
    steps = _micro_pipeline_steps() if scope is None else _standard_pipeline_steps(scope, plan_mode)
    docs_by_key = {d["key"]: d for d in docs}

    resolved: list[dict] = []
    next_action: str | None = None
    next_step_id: str | None = None
    next_persona: dict | None = None
    for i, step in enumerate(steps):
        persona = _persona_hint(step["id"], feature, scope)
        if step.get("skip"):
            resolved.append({**step, "state": "skipped", "persona": persona})
            continue
        state = _step_state(step, docs_by_key, tasks, constitution, service_docs_exist)
        resolved.append({**step, "state": state, "persona": persona})
        if state != "done" and next_action is None:
            # An *optional* step (e.g. checklist at pilot scope) whose doc
            # was never generated is still "upcoming", not "done" -- but if
            # a later mandatory doc already exists, the user consciously
            # moved past it rather than forgot it. Picking it here would
            # tell the dashboard to say "run /checklist" while the pipeline
            # diagram itself already shows a later step as current --
            # exactly the contradiction a user reported seeing.
            if (step.get("optional") and state == "upcoming"
                    and _later_doc_step_exists(steps[i + 1:], docs_by_key)):
                continue
            next_action = _next_action_sentence(step, state, tasks)
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
        return {"format": "none", "total": 0, "done": 0, "in_progress": 0, "not_started": 0, "items": []}

    text = tasks_path.read_text(errors="replace")
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

        items.append({"id": task_id, "title": title, "status": status})

    def _norm(s: str) -> str:
        s = s.lower()
        if "done" in s or "complete" in s:
            return "done"
        if "progress" in s:
            return "in_progress"
        if "not started" in s or s == "":
            return "not_started"
        return "unknown"

    counts = {"done": 0, "in_progress": 0, "not_started": 0, "unknown": 0}
    for it in items:
        counts[_norm(it["status"])] += 1

    return {
        "format": fmt if items else "none",
        "total": len(items),
        "done": counts["done"],
        "in_progress": counts["in_progress"],
        "not_started": counts["not_started"] + counts["unknown"],
        "items": items,
    }


def _parse_token_usage(path: Path) -> dict | None:
    if not path.exists():
        return None
    text = path.read_text(errors="replace")
    values: dict[str, str] = {}
    for m in _RUNNING_TOTAL_ROW_RE.finditer(text):
        values[m.group(1)] = m.group(2).strip()
    if not values:
        return {"exists": True, "total_input": None, "total_output": None,
                "total_cost": None, "commands_logged": None, "last_updated": None}
    return {
        "exists": True,
        "total_input":     values.get("Total Est. Input Tokens"),
        "total_output":    values.get("Total Est. Output Tokens"),
        "total_cost":      values.get("Total Est. Cost (USD)"),
        "commands_logged": values.get("Commands logged"),
        "last_updated":    values.get("Last updated"),
    }


_TEMPLATE_PLACEHOLDER_RE = re.compile(r'\{[a-z][a-zA-Z0-9 _/]*\}')


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
    text = path.read_text(errors="replace")
    part2_marker = text.find("PART 2")
    part2_text = text[part2_marker:] if part2_marker != -1 else text
    if _TEMPLATE_PLACEHOLDER_RE.search(part2_text):
        return {"exists": True, "part2_generated": False, "gate1_inferred": "unknown"}
    # No machine-readable Draft/Finalized flag is written into constitution.md
    # by design (GATE-1 confirmation happens in chat) — infer from whether any
    # downstream feature doc exists, since the workflow can't produce those
    # before GATE-1 passes.
    features_dir = root / ".specify" / "features"
    any_downstream = False
    if features_dir.is_dir():
        for feature_dir in features_dir.iterdir():
            if not feature_dir.is_dir():
                continue
            if any(p.name != "tasks.md" and not p.name.endswith(".summary.md")
                   for p in feature_dir.glob("*.md")):
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
        from sdd.utils.integrations import load_integrations
        profile_name = None
        try:
            profile_name = load_integrations().profile
        except FileNotFoundError:
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
    `apply`) live in a separate file, see _local_review_links() below."""
    result: dict = {"epic": None, "stories": [], "tasks": []}
    keys_path = root / "docs" / "jira" / feature / "keys.yml"
    if not keys_path.exists():
        return result
    try:
        keys = yaml.safe_load(keys_path.read_text()) or {}
    except Exception:
        return result

    def _link(jira_key: str) -> dict:
        return {"key": jira_key, "url": f"{base_url}/browse/{jira_key}" if base_url else None}

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
        drafts = json.loads(drafts_path.read_text())
    except Exception:
        return {}
    links = {}
    for doc_key, entry in drafts.items():
        page_id = entry.get("page_id")
        if not page_id:
            continue
        links[doc_key] = {
            "title": entry.get("title"),
            "url": f"{base_url}/wiki/pages/viewpage.action?pageId={page_id}" if base_url else None,
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
        raw = json.loads(links_path.read_text())
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


def build_feature_status(root: Path, feature: str, constitution: dict | None = None,
                          plan_mode: str = "unified", scope: str | None = "pilot") -> dict:
    feature_dir = root / ".specify" / "features" / feature
    docs = _feature_docs(root, feature)
    base_url = _local_base_url()
    tasks = _parse_tasks(feature_dir / "tasks.md")
    return {
        "name": feature,
        "docs": docs,
        "current_stage": _current_stage(docs, feature, scope),
        "tasks": tasks,
        "token_usage": _parse_token_usage(feature_dir / "token-usage.md"),
        "local_links": {
            "jira": _local_jira_links(root, feature, base_url),
            "confluence": _local_confluence_links(root, base_url),
            "jira_review": _local_review_links(root, base_url),
        },
        "pipeline": build_pipeline(
            docs, tasks, constitution or _constitution_status(root),
            _service_docs_exist(root), plan_mode, scope, feature=feature,
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
    constitution = _constitution_status(root)

    return {
        "project": {
            "name":            proj.get("name") or None,
            "current_feature": proj.get("feature") or None,
            "scope":           scope,
            "plan_mode":       plan_mode,
            "project_type":    manifest.get("project_type"),
            "workflow_mode":   manifest.get("workflow_mode"),
            "sdd_version":     manifest.get("sdd_version"),
        },
        "constitution": constitution,
        "features": [
            build_feature_status(root, f, constitution=constitution, plan_mode=plan_mode, scope=scope)
            for f in _list_feature_names(root)
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
