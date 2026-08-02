"""Parse SDD-generated stories.md and tasks.md into Python objects."""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Story:
    id: str  # STORY-001
    title: str
    moscow: str  # must-have | should-have | could-have | wont-have
    description: str  # As .../I want .../So that ... (or "As a ..." older style)
    acceptance_criteria: list[str]
    story_points: int | None
    satisfies: list[str]  # [FR-001, FR-002]
    derived_uc: str | None = None  # UC-001 -- set only when this story traces
    # 1:1 back to a single use case that already
    # got a draft Jira Story at /specify-uc time;
    # lets sdd jira push finalize that same
    # issue in place instead of creating a new one


@dataclass
class UseCase:
    id: str  # UC-001
    title: str


@dataclass
class Task:
    id: str  # TASK-001 (or PERF-001, Phase G perf tasks)
    title: str
    story_id: str | None  # STORY-001
    satisfies: list[str]
    estimate: str | None
    description: str
    acceptance_criteria: list[str]


def _normalize_moscow(header: str) -> str:
    """Bucket headers in the shipped template are e.g. "Must Have Stories"
    -- match on the keyword itself rather than requiring an exact
    "must have" string, so trailing words (or parentheticals) don't fall
    through to the could-have default."""
    h = header.lower()
    if "must" in h:
        return "must-have"
    if "should" in h:
        return "should-have"
    if "could" in h:
        return "could-have"
    if "won" in h:
        return "wont-have"
    return "could-have"


def _field(text: str, name: str) -> str | None:
    """Match a `**Field:** value` or plain `Field: value` line -- the
    shipped templates use bold fields in stories.md and plain (unbolded)
    fields in tasks.md; older generated docs mix styles too, so bold
    markers are always optional and the field name is matched
    case-insensitively."""
    m = re.search(rf"(?im)^\s*\*{{0,2}}{re.escape(name)}:\*{{0,2}}\s*(.+)$", text)
    return m.group(1).strip() if m else None


def _split_list_field(value: str | None) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()] if value else []


# ── stories.md ────────────────────────────────────────────────────────────────


def parse_stories(path: str | Path = ".specify/features") -> list[Story]:
    """Read stories.md from path (file) or search recursively (directory)."""
    p = Path(path)
    if p.is_file():
        return _parse_stories_text(p.read_text())
    matches = list(p.rglob("stories.md"))
    return _parse_stories_text(matches[0].read_text()) if matches else []


# STORY-{NNN} heading: current template uses a colon ("### STORY-001: Title"),
# older generated docs use an em-dash ("### STORY-001 — Title") -- accept any
# colon/dash separator so both are parsed correctly.
_STORY_HEADING_RE = re.compile(r"^###\s+(STORY-\d+)\s*[:—–-]+\s*(.+)")


def _parse_stories_text(text: str) -> list[Story]:
    stories: list[Story] = []
    current_moscow = "must-have"
    lines = text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]

        # MoSCoW bucket headers: ## Must Have / ## Should Have / etc.
        if re.match(r"^##\s+", line) and not line.startswith("###"):
            m = re.match(r"^##\s+(.+)", line)
            if m:
                header = m.group(1)
                if any(k in header.lower() for k in ["must", "should", "could", "won"]):
                    current_moscow = _normalize_moscow(header)
            i += 1
            continue

        m = _STORY_HEADING_RE.match(line)
        if m:
            story_id, title = m.group(1), m.group(2).strip()
            body_lines: list[str] = []
            i += 1
            while i < len(lines):
                if _STORY_HEADING_RE.match(lines[i]):
                    break
                if re.match(r"^##\s+", lines[i]) and not lines[i].startswith("###"):
                    break
                body_lines.append(lines[i])
                i += 1
            body = "\n".join(body_lines)
            stories.append(
                Story(
                    id=story_id,
                    title=title,
                    moscow=current_moscow,
                    description=_extract_user_story(body),
                    acceptance_criteria=_extract_ac_block(body, "Acceptance Criteria"),
                    story_points=_extract_story_points(body),
                    satisfies=_split_list_field(
                        _field(body, "Linked FRs") or _field(body, "Satisfies")
                    ),
                    derived_uc=_extract_derived_uc(body),
                )
            )
            continue

        i += 1
    return stories


# "As {actor}" / "As a {actor}" (older style) / "I want" / "I want to"
# (older style) / "So that" -- bold markers optional, "a"/"to" optional.
_USER_STORY_LINE_RE = re.compile(
    r"^\*{0,2}(As a|As|I want to|I want|So that)\*{0,2}\b", re.IGNORECASE
)


def _extract_user_story(text: str) -> str:
    parts = []
    for line in text.splitlines():
        if _USER_STORY_LINE_RE.match(line.strip()):
            parts.append(line.strip())
    return " ".join(parts)


def _extract_ac_block(text: str, header_name: str) -> list[str]:
    """Collect `- ...` bullet lines (checkbox or plain, e.g. `- [ ] ...`
    or `- AC-001-1: ...`) following a `**{header_name}:**` / plain
    `{header_name}:` header line, until the next field/heading line."""
    ac: list[str] = []
    in_ac = False
    header_re = re.compile(rf"(?i)^\s*\*{{0,2}}{re.escape(header_name)}:\*{{0,2}}\s*$")
    field_re = re.compile(r"^\s*\*{0,2}[A-Za-z][A-Za-z ]*:\*{0,2}\s")
    for line in text.splitlines():
        if header_re.match(line):
            in_ac = True
            continue
        if in_ac:
            m = re.match(r"^\s*[-*]\s+(.+)", line)
            if m:
                criterion = re.sub(r"^\[[xX ]\]\s*", "", m.group(1).strip())
                ac.append(criterion)
                continue
            if not line.strip():
                continue
            if field_re.match(line) and header_name.lower() not in line.lower():
                break
    return ac


def _extract_story_points(text: str) -> int | None:
    m = re.search(r"\*{0,2}Story Points:\*{0,2}\s*(\d+)", text, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _extract_derived_uc(text: str) -> str | None:
    """`**Derived from:** UC-001` -- the agent writes this only when a
    story traces 1:1 back to a single use case (see task.prompt.md);
    stories with no single-UC origin simply omit the field."""
    value = _field(text, "Derived from")
    m = re.match(r"(UC-\d+)", value) if value else None
    return m.group(1) if m else None


# ── use-cases.md ─────────────────────────────────────────────────────────────


def parse_use_cases(path: str | Path = ".specify/features") -> list[UseCase]:
    """Read use-cases.md from path (file) or search recursively (directory).
    Only extracts §3 UC-NNN headings and titles -- MP/AP/EP detail isn't
    needed for the draft-story bootstrap this feeds (see jira.py)."""
    p = Path(path)
    if p.is_file():
        return _parse_use_cases_text(p.read_text())
    matches = list(p.rglob("use-cases.md"))
    return _parse_use_cases_text(matches[0].read_text()) if matches else []


def _parse_use_cases_text(text: str) -> list[UseCase]:
    use_cases: list[UseCase] = []
    for m in re.finditer(r"^###\s+(UC-\d+)\s*[:—–-]+\s*(.+)$", text, re.MULTILINE):
        use_cases.append(UseCase(id=m.group(1), title=m.group(2).strip()))
    return use_cases


# ── tasks.md ──────────────────────────────────────────────────────────────────


def parse_tasks(path: str | Path = ".specify/features") -> list[Task]:
    """Read tasks.md from path (file) or search recursively (directory)."""
    p = Path(path)
    if p.is_file():
        return _parse_tasks_text(p.read_text())
    matches = list(p.rglob("tasks.md"))
    return _parse_tasks_text(matches[0].read_text()) if matches else []


# TASK-{NNN}/PERF-{NNN} heading: the shipped tasks-template.md uses "###"
# (H3) with an em-dash ("### TASK-001 — Title"); accept "##" too (older
# style) and any colon/dash separator.
_TASK_HEADING_RE = re.compile(r"^#{2,3}\s+(TASK-\d+|PERF-\d+|CHG-\d+)\s*[:—–-]+\s*(.+)")

# Field labels used as plain (unbolded) lines in tasks.md -- stops a
# multi-line block (e.g. Files:) from swallowing the next field.
_TASK_FIELD_NAMES = (
    "Story",
    "Satisfies",
    "Verifies",
    "Risk",
    "Dependencies",
    "Estimated lines",
    "PR",
    "Files",
    "Acceptance criteria",
)
_TASK_FIELD_STOP_RE = re.compile(
    r"^\s*(" + "|".join(re.escape(n) for n in _TASK_FIELD_NAMES) + r"):", re.IGNORECASE
)


def _parse_tasks_text(text: str) -> list[Task]:
    tasks: list[Task] = []
    lines = text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]
        m = _TASK_HEADING_RE.match(line)
        if m:
            task_id, title = m.group(1), m.group(2).strip()
            body_lines: list[str] = []
            i += 1
            while i < len(lines) and not _TASK_HEADING_RE.match(lines[i]):
                body_lines.append(lines[i])
                i += 1
            body = "\n".join(body_lines)
            tasks.append(
                Task(
                    id=task_id,
                    title=title,
                    story_id=_extract_task_story(body),
                    satisfies=_split_list_field(_field(body, "Satisfies")),
                    estimate=_field(body, "Estimated lines")
                    or _field(body, "Estimate"),
                    description=_extract_task_description(body),
                    acceptance_criteria=_extract_ac_block(body, "Acceptance criteria"),
                )
            )
            continue
        i += 1
    return tasks


def _extract_task_story(text: str) -> str | None:
    value = _field(text, "Story")
    m = re.match(r"(STORY-\d+)", value) if value else None
    return m.group(1) if m else None


def _extract_task_description(text: str) -> str:
    """Older generated tasks.md has a free-text `**Description:**`
    paragraph; the current shipped tasks-template.md has no such field --
    the closest equivalent there is the `Files:` block, which is what
    actually describes what the task touches."""
    paragraph = _extract_field_paragraph(text, "Description")
    return paragraph if paragraph else _extract_task_files(text)


def _extract_field_paragraph(text: str, header_name: str) -> str:
    """Value for a `**Field:**`/plain `Field:` header that may be inline
    (`Field: value`) or start on the next line and span a short
    paragraph, ending at a blank line or the next field/bullet line."""
    lines = text.splitlines()
    header_re = re.compile(
        rf"(?i)^\s*\*{{0,2}}{re.escape(header_name)}:\*{{0,2}}\s*(.*)$"
    )
    for idx, line in enumerate(lines):
        m = header_re.match(line)
        if not m:
            continue
        out = []
        inline = m.group(1).strip()
        if inline:
            out.append(inline)
        j = idx + 1
        while j < len(lines):
            nxt = lines[j]
            if not nxt.strip():
                if out:
                    break
                j += 1
                continue
            if _TASK_FIELD_STOP_RE.match(nxt) or re.match(r"^\s*[-*]\s", nxt):
                break
            out.append(nxt.strip())
            j += 1
        return " ".join(out).strip()
    return ""


def _extract_task_files(text: str) -> str:
    """tasks.md has no free-text `Description:` field -- the closest
    equivalent content is the `Files:` block, which is what actually
    describes what the task touches. `Files:` may give a single file
    inline on the same line (e.g. Phase G perf tasks) or a multi-line
    indented list (e.g. Phase A/B/C/D/E/F tasks)."""
    lines = text.splitlines()
    collecting = False
    out: list[str] = []
    for line in lines:
        m = re.match(r"(?i)^\s*Files:\s*(.*)$", line)
        if m:
            inline = m.group(1).strip()
            if inline:
                out.append(inline)
            collecting = True
            continue
        if collecting:
            if not line.strip() or _TASK_FIELD_STOP_RE.match(line):
                break
            out.append(line.strip())
    return "\n".join(out)
