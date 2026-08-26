# Tracks what sddflow itself last wrote to each Confluence page, so a
# later push can tell "this page was edited by someone else since we
# last wrote it" apart from "this is exactly what we left it as".
#
# Confluence has no concept of "who owns this page" -- upsert_page()
# always just overwrites the body with whatever the local .md currently
# says, using Confluence's optimistic-locking version number purely to
# avoid a 409, never to detect or preserve a manual edit in between (see
# confluence_client.py's upsert_page docstring). Without this file,
# there is no way to tell a normal re-push (nothing changed on
# Confluence's side) apart from a re-push that's about to silently
# clobber a reviewer's or stakeholder's direct edit.
#
# Deliberately one file for the whole project, not per-feature like
# docs/jira/{feature}/keys.yml: PROJECT_SCOPED_DOCS (constitution,
# runbook, living-service-docs) don't have a feature at all, and a
# page's real identity in Confluence is its ID, not its title or which
# feature pushed it -- title can change, ID never does.
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sdd.utils.atomic_write import atomic_write_text

PUSH_LOG_PATH = Path("docs") / "confluence" / "push-log.yml"


def load_push_log(path: Path = PUSH_LOG_PATH) -> dict[str, dict[str, Any]]:
    """{page_id: {"doc": ..., "title": ..., "pushed_version": int}}.

    Never raises -- a missing or corrupt file just means nothing is
    tracked yet (same tolerance as jira.py's keys.yml handling): a
    brand-new project, or one that pushed to Confluence before this
    file existed, simply has no drift history to check against, not a
    hard failure."""
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def record_push(
    page_id: str,
    doc: str,
    title: str,
    pushed_version: int,
    path: Path = PUSH_LOG_PATH,
) -> None:
    """Update the log after a page is successfully written (push, draft,
    or pull -- anywhere sddflow's own view of "current version" changes),
    so the next drift check compares against what actually happened, not
    a stale record. Silently overwrites any prior entry for this page_id."""
    log = load_push_log(path)
    log[str(page_id)] = {"doc": doc, "title": title, "pushed_version": pushed_version}
    atomic_write_text(
        path,
        "# Tracks what sddflow itself last wrote to each Confluence page --\n"
        "# written by `sdd confluence push`/`draft`/`pull`, read by `push`'s\n"
        "# drift check and by `sdd confluence verify`. Safe to delete: it only\n"
        "# ever gets rebuilt from the next push, never re-derived from Confluence\n"
        "# itself (there is nothing there that says 'sddflow wrote this').\n"
        + yaml.dump(log, default_flow_style=False, sort_keys=True),
    )


def check_drift(existing_page: dict, log: dict[str, dict[str, Any]]) -> dict | None:
    """None if it's safe to overwrite `existing_page` (sddflow never
    pushed it before, or its version hasn't moved since we last did);
    otherwise a dict describing who changed it and when, for the warning
    message. Never raises -- a page missing the fields it expects (an
    unexpected Confluence response shape) is treated as "nothing to warn
    about" rather than crashing the push."""
    page_id = str(existing_page.get("id", ""))
    record = log.get(page_id)
    if not record:
        return None
    version_info = existing_page.get("version") or {}
    live_version = version_info.get("number")
    pushed_version = record.get("pushed_version")
    if live_version is None or pushed_version is None or live_version == pushed_version:
        return None
    return {
        "by": version_info.get("by", {}).get("displayName", "someone"),
        "when": (version_info.get("when") or "")[:10],
        "pushed_version": pushed_version,
        "live_version": live_version,
    }
