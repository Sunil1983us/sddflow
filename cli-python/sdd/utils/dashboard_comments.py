"""Read/acknowledge tracking for dashboard-left review comments
(.specify/.dashboard-comments.json).

`sdd dashboard` writes comments there (see dashboard.py's _do_comment).
When Jira is configured, those comments also mirror to the doc's Jira
review ticket, so `sdd review check` already surfaces them via the normal
Jira poll. But in pure local mode -- no jira: section at all -- there is
no external ticket to poll, so `sdd review check`/`sdd review apply` fall
back to the functions here instead of the file going unread until the
user manually relays the feedback in chat.

Acknowledgement is tracked separately (.dashboard-comments-ack.json)
because the comments file itself is an append-only log with no per-entry
"handled" flag -- the ack file just records, per feature/doc, the
timestamp of the last comment the agent has already acted on.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

_COMMENTS_FILE = Path(".specify") / ".dashboard-comments.json"
_ACK_FILE = Path(".specify") / ".dashboard-comments-ack.json"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def all_comments(feature: str, doc: str) -> list[dict]:
    """Every comment ever left for this feature/doc, oldest first."""
    return _load_json(_COMMENTS_FILE).get(f"{feature}/{doc}", [])


def unacknowledged(feature: str, doc: str) -> list[dict]:
    """Comments left since the last acknowledge() call for this
    feature/doc -- everything, if never acknowledged."""
    acked_at = _load_json(_ACK_FILE).get(f"{feature}/{doc}")
    comments = all_comments(feature, doc)
    if not acked_at:
        return comments
    return [c for c in comments if c.get("at", "") > acked_at]


def acknowledge(feature: str, doc: str) -> None:
    """Mark every comment currently on this feature/doc as addressed --
    the local-mode equivalent of `sdd review apply` re-pushing to
    Confluence/notifying Jira, for projects with neither configured."""
    key = f"{feature}/{doc}"
    acks = _load_json(_ACK_FILE)
    acks[key] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _ACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    _ACK_FILE.write_text(json.dumps(acks, indent=2))
