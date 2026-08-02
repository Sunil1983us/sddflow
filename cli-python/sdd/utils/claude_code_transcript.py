"""Best-effort reader for Claude Code's local session transcript files.

Claude Code writes one JSONL file per session to
~/.claude/projects/{sanitized-cwd}/{session-id}.jsonl, and one more per
spawned subagent under {session-id}/subagents/*.jsonl. Each assistant
turn in these files carries the real `usage` object from the Anthropic
API response (input_tokens, output_tokens, cache_creation_input_tokens,
cache_read_input_tokens) -- actual measured token counts, not an
estimate.

This is Claude Code-specific and undocumented (reverse-engineered from
observed file layout, not a published API) -- it is not available under
any other AI tool this framework supports (Copilot, Cursor, Windsurf,
copy-paste "any AI"), and the directory-naming convention or file format
could change in a future Claude Code release with no notice. Callers
must treat "nothing found" as a normal, expected outcome and fall back
to the char-count estimate, not an error.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json


def _parse_timestamp(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


@dataclass
class ModelUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    turns: int = 0

    @property
    def billed_input_tokens(self) -> int:
        """Cache-creation and cache-read tokens are still input tokens,
        billed at their own (usually cheaper or pricier) cache rates --
        token-pricing.yml only has one input_per_million rate per model,
        with no cache-tier split, so summing all three into one bucket
        is the best approximation this schema supports. Good enough for
        relative comparison, which is this file's own stated purpose;
        not exact billing, same caveat the estimate path already carries."""
        return (
            self.input_tokens
            + self.cache_creation_input_tokens
            + self.cache_read_input_tokens
        )


def claude_projects_dir() -> Path:
    return Path.home() / ".claude" / "projects"


def _sanitize_cwd(cwd: Path) -> str:
    """Claude Code's own directory-naming convention: the absolute
    project path with every path separator replaced by '-'. Undocumented
    and reverse-engineered -- inherently best-effort."""
    return str(cwd.resolve()).replace("/", "-")


def find_session_transcripts(cwd: Path | None = None) -> tuple[Path | None, list[Path]]:
    """Locate the current Claude Code session's transcript and any
    subagent transcripts spawned from it.

    Returns (main_transcript_or_None, [subagent_transcript, ...]). Picks
    the most-recently-modified top-level .jsonl file in the project's
    transcript directory as "the current session" -- if more than one
    Claude Code session is open against the same project directory at
    once, this can pick the wrong one; there is no documented way for
    this process to know which session it belongs to. Returns (None, [])
    if the directory doesn't exist at all (not running under Claude
    Code, or no session has touched this project yet) -- this is the
    normal, expected outcome for every other AI tool."""
    cwd = cwd or Path.cwd()
    project_dir = claude_projects_dir() / _sanitize_cwd(cwd)
    if not project_dir.is_dir():
        return None, []
    candidates = sorted(
        (p for p in project_dir.glob("*.jsonl") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None, []
    main = candidates[0]
    subagents_dir = project_dir / main.stem / "subagents"
    subagent_files = (
        sorted(subagents_dir.glob("*.jsonl")) if subagents_dir.is_dir() else []
    )
    return main, subagent_files


def sum_usage_since(
    transcript_files: list[Path], since: datetime | None
) -> dict[str, ModelUsage]:
    """Sum real API usage across the given transcript file(s), bucketed
    by model, for assistant turns at or after `since` (all turns if
    `since` is None -- used for the very first command logged in a
    session, when there's no prior timestamp to bound from).

    Malformed or unreadable lines/files are skipped, not fatal -- the
    main transcript can be actively appended to by the running session
    while this reads it, and a torn last line is expected, not an error."""
    usage_by_model: dict[str, ModelUsage] = {}
    for path in transcript_files:
        try:
            lines = path.read_text().splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("type") != "assistant":
                continue
            message = entry.get("message") or {}
            usage = message.get("usage")
            if not usage:
                continue
            ts_raw = entry.get("timestamp")
            if since is not None and ts_raw:
                try:
                    if _parse_timestamp(ts_raw) < since:
                        continue
                except ValueError:
                    pass
            model = message.get("model") or "unknown"
            bucket = usage_by_model.setdefault(model, ModelUsage())
            bucket.input_tokens += usage.get("input_tokens", 0) or 0
            bucket.output_tokens += usage.get("output_tokens", 0) or 0
            bucket.cache_creation_input_tokens += (
                usage.get("cache_creation_input_tokens", 0) or 0
            )
            bucket.cache_read_input_tokens += (
                usage.get("cache_read_input_tokens", 0) or 0
            )
            bucket.turns += 1
    return usage_by_model
