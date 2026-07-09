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


def _feature_docs(feature_dir: Path) -> list[dict]:
    docs: list[dict] = []
    seen_keys: set[str] = set()
    md_files = sorted(
        (p for p in feature_dir.glob("*.md")
         if not p.name.endswith(".summary.md") and p.stem not in _NON_PIPELINE_DOCS),
        key=lambda p: _PIPELINE_ORDER.get(p.stem, 999),
    )
    for path in md_files:
        key = path.stem
        seen_keys.add(key)
        docs.append({
            "key": key,
            "label": _PIPELINE_LABELS.get(key, key.replace("-", " ").title()),
            "exists": True,
            "status": _doc_status(path),
            "path": str(path),
        })
    return docs


def _current_stage(docs: list[dict]) -> dict:
    """Last pipeline-ordered doc that exists, plus a best-effort 'next' guess."""
    known = [d for d in docs if d["key"] in _PIPELINE_ORDER]
    if not known:
        return {"doc": None, "status": None, "next": PIPELINE_DOCS[0][1] if PIPELINE_DOCS else None}
    known.sort(key=lambda d: _PIPELINE_ORDER[d["key"]])
    last = known[-1]
    idx = _PIPELINE_ORDER[last["key"]]
    next_label = PIPELINE_DOCS[idx + 1][1] if idx + 1 < len(PIPELINE_DOCS) else None
    status = (last["status"] or "").lower()
    awaiting_approval = status not in ("approved",) and status != ""
    return {
        "doc": last["label"],
        "status": last["status"],
        "next": ("(awaiting approval)" if awaiting_approval else next_label),
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


def _constitution_status(root: Path) -> dict:
    path = root / ".specify" / "memory" / "constitution.md"
    if not path.exists():
        return {"exists": False, "gate1_inferred": "unknown"}
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


def _local_jira_links(root: Path, feature: str, base_url: str | None) -> dict:
    """Jira Epic/Story/Task links already persisted by the progressive
    export (docs/jira/{feature}/keys.yml, written by jira-push.py). No
    network call — review-gate ticket links (from `sdd review submit`)
    are never cached locally, see the live /api/review-links endpoint."""
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

    epic = keys.get("epic") or {}
    if epic.get("jira_key"):
        result["epic"] = _link(epic["jira_key"])
    result["stories"] = [_link(s["jira_key"]) for s in (keys.get("stories") or []) if s.get("jira_key")]
    result["tasks"] = [_link(t["jira_key"]) for t in (keys.get("tasks") or []) if t.get("jira_key")]
    return result


def _local_confluence_links(root: Path, base_url: str | None) -> dict:
    """Confluence page links already persisted by `sdd confluence push`/
    `draft` (.specify/.confluence-drafts.json). No network call — pages
    pushed via `sdd review submit` are never cached locally the same way,
    see the live /api/review-links endpoint. Project-wide, not per-feature
    (the drafts file isn't feature-scoped)."""
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


def build_feature_status(root: Path, feature: str) -> dict:
    feature_dir = root / ".specify" / "features" / feature
    docs = _feature_docs(feature_dir)
    base_url = _local_base_url()
    return {
        "name": feature,
        "docs": docs,
        "current_stage": _current_stage(docs),
        "tasks": _parse_tasks(feature_dir / "tasks.md"),
        "token_usage": _parse_token_usage(feature_dir / "token-usage.md"),
        "local_links": {
            "jira": _local_jira_links(root, feature, base_url),
            "confluence": _local_confluence_links(root, base_url),
        },
    }


def build_project_status(root: str | Path = ".") -> dict:
    """Pure, read-only snapshot of .specify/ — safe to call repeatedly (e.g.
    on every dashboard poll) since it does no caching and no writes."""
    root = Path(root)
    manifest = read_manifest(str(root / ".specify" / "manifest.yml")) or {}
    proj = manifest.get("project") or {}

    return {
        "project": {
            "name":            proj.get("name") or None,
            "current_feature": proj.get("feature") or None,
            "scope":           proj.get("scope"),  # absent for sdd-micro
            "project_type":    manifest.get("project_type"),
            "workflow_mode":   manifest.get("workflow_mode"),
            "sdd_version":     manifest.get("sdd_version"),
        },
        "constitution": _constitution_status(root),
        "features": [build_feature_status(root, f) for f in _list_feature_names(root)],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
