"""Parse SDD-generated stories.md and tasks.md into Python objects."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Story:
    id: str                        # STORY-001
    title: str
    moscow: str                    # must-have | should-have | could-have | wont-have
    description: str               # As a ... / I want ... / So that ...
    acceptance_criteria: list[str]
    story_points: int | None
    satisfies: list[str]           # [FR-001, FR-002]


@dataclass
class Task:
    id: str                        # TASK-001
    title: str
    story_id: str | None           # STORY-001
    satisfies: list[str]
    estimate: str | None
    description: str
    acceptance_criteria: list[str]


_MOSCOW_MAP = {
    "must have":   "must-have",
    "should have": "should-have",
    "could have":  "could-have",
    "won't have":  "wont-have",
    "wont have":   "wont-have",
}


def _normalize_moscow(header: str) -> str:
    key = re.sub(r'\s*\(.*\)', '', header).lower().strip()
    return _MOSCOW_MAP.get(key, "could-have")


# ── stories.md ────────────────────────────────────────────────────────────────

def parse_stories(path: str | Path = ".specify/features") -> list[Story]:
    """Read stories.md from path (file) or search recursively (directory)."""
    p = Path(path)
    if p.is_file():
        return _parse_stories_text(p.read_text())
    matches = list(p.rglob("stories.md"))
    return _parse_stories_text(matches[0].read_text()) if matches else []


def _parse_stories_text(text: str) -> list[Story]:
    stories: list[Story] = []
    current_moscow = "must-have"
    lines = text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]

        # MoSCoW bucket headers: ## Must Have / ## Should Have / etc.
        if re.match(r'^##\s+', line) and not line.startswith('###'):
            header = re.match(r'^##\s+(.+)', line).group(1)
            if any(k in header.lower() for k in ["must", "should", "could", "won"]):
                current_moscow = _normalize_moscow(header)
            i += 1
            continue

        # Story block: ### STORY-NNN — Title
        m = re.match(r'^###\s+(STORY-\d+)\s+[—–-]+\s+(.+)', line)
        if m:
            story_id, title = m.group(1), m.group(2).strip()
            body_lines: list[str] = []
            i += 1
            while i < len(lines):
                if re.match(r'^###\s+STORY-', lines[i]):
                    break
                if re.match(r'^##\s+', lines[i]) and not lines[i].startswith('###'):
                    break
                body_lines.append(lines[i])
                i += 1
            body = "\n".join(body_lines)
            stories.append(Story(
                id=story_id,
                title=title,
                moscow=current_moscow,
                description=_extract_user_story(body),
                acceptance_criteria=_extract_ac(body),
                story_points=_extract_story_points(body),
                satisfies=_extract_satisfies(body),
            ))
            continue

        i += 1
    return stories


def _extract_user_story(text: str) -> str:
    parts = []
    for line in text.splitlines():
        if re.match(r'\*\*(As a|I want|So that)\*\*', line.strip()):
            parts.append(line.strip())
    return " ".join(parts)


def _extract_ac(text: str) -> list[str]:
    ac: list[str] = []
    in_ac = False
    for line in text.splitlines():
        if re.match(r'\*\*Acceptance Criteria:\*\*', line):
            in_ac = True
            continue
        if in_ac:
            if re.match(r'\*\*\w', line) and "Acceptance" not in line:
                break
            m = re.match(r'^\s*[-*]\s+(.+)', line)
            if m:
                ac.append(m.group(1).strip())
            elif re.match(r'^\s*AC-\d+', line):
                ac.append(line.strip())
    return ac


def _extract_story_points(text: str) -> int | None:
    m = re.search(r'\*\*Story Points:\*\*\s*(\d+)', text)
    return int(m.group(1)) if m else None


def _extract_satisfies(text: str) -> list[str]:
    m = re.search(r'\*\*Satisfies:\*\*\s*(.+)', text)
    if not m:
        return []
    return [x.strip() for x in m.group(1).split(",") if x.strip()]


# ── tasks.md ──────────────────────────────────────────────────────────────────

def parse_tasks(path: str | Path = ".specify/features") -> list[Task]:
    """Read tasks.md from path (file) or search recursively (directory)."""
    p = Path(path)
    if p.is_file():
        return _parse_tasks_text(p.read_text())
    matches = list(p.rglob("tasks.md"))
    return _parse_tasks_text(matches[0].read_text()) if matches else []


def _parse_tasks_text(text: str) -> list[Task]:
    tasks: list[Task] = []
    lines = text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]
        m = re.match(r'^##\s+(TASK-\d+)\s+[—–-]+\s+(.+)', line)
        if m:
            task_id, title = m.group(1), m.group(2).strip()
            body_lines: list[str] = []
            i += 1
            while i < len(lines) and not re.match(r'^##\s+TASK-', lines[i]):
                body_lines.append(lines[i])
                i += 1
            body = "\n".join(body_lines)
            tasks.append(Task(
                id=task_id,
                title=title,
                story_id=_extract_task_story(body),
                satisfies=_extract_satisfies(body),
                estimate=_extract_estimate(body),
                description=_extract_section(body, "Description"),
                acceptance_criteria=_extract_ac(body),
            ))
            continue
        i += 1
    return tasks


def _extract_task_story(text: str) -> str | None:
    m = re.search(r'\*\*Story:\*\*\s+(STORY-\d+)', text)
    return m.group(1) if m else None


def _extract_estimate(text: str) -> str | None:
    m = re.search(r'\*\*Estimate:\*\*\s*(.+)', text)
    return m.group(1).strip() if m else None


def _extract_section(text: str, heading: str) -> str:
    m = re.search(rf'\*\*{heading}:\*\*\s*(.*?)(?=\*\*|\Z)', text, re.DOTALL)
    return m.group(1).strip() if m else ""
