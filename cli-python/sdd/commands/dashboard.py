"""sdd dashboard — local web UI over the status.py snapshot.

Stdlib-only HTTP server (no new dependency) serving a single static page
that polls /api/status. Mostly a read-only viewer, with two write actions
(POST /api/approve, POST /api/comment) that mirror what a human would
otherwise run via `sdd review approve --local` from the CLI.

Every endpoint takes feature/doc/etc. from HTTP requests — once this
server is bound to something other than 127.0.0.1 (see --host), that's
network-reachable input, not a trusted local CLI flag. feature/doc are
validated against _SAFE_TOKEN before touching the filesystem or building
any path, closing off path traversal; free-text fields (by/note/comment
text) are length-clipped before being written anywhere.
"""

from __future__ import annotations

import json
import re
import secrets
import socket
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TypedDict
from urllib.parse import parse_qs, urlparse

import click
from rich.console import Console

from sdd.utils.manifest import read_manifest
from sdd.utils.status import build_project_status

console = Console()

_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_-]+$")


# --- Access control for non-loopback binds --------------------------------
# Set once by dashboard_command() before serve_forever(); read by every
# _Handler instance (http.server makes a fresh handler per request, so this
# can't live on self -- module-level state set once at startup is the
# simplest correct home for it). Defaults here are the safe/local case:
# no token, writes allowed -- matching today's loopback-only behavior
# exactly, so a plain `sdd dashboard` with no flags is unaffected by any of
# this.
class _AccessState(TypedDict):
    is_local: bool
    writes_enabled: bool
    token: str | None
    allowed_origins: set[str]


_ACCESS: _AccessState = {
    "is_local": True,
    "writes_enabled": True,
    "token": None,
    "allowed_origins": set(),
}

# Serializes every write triggered by a dashboard request (approve, comment)
# behind one lock. ThreadingHTTPServer runs each request on its own thread,
# and _do_approve/_do_comment each do a read-modify-write on a shared file
# (.local-approvals.yml / .dashboard-comments.json) with no atomicity of
# their own -- two near-simultaneous requests can race and silently drop
# one's write. Dashboard write volume is a human clicking buttons, so
# serializing it has no meaningful cost.
_WRITE_LOCK = threading.Lock()

_DASHBOARD_STATIC_DIR = Path(__file__).parent / "dashboard_static"


def _load_page() -> str:
    """Assembles the dashboard's single-response HTML page from the static
    files in dashboard_static/ -- CSS/JS live in real .css/.js files (for
    editor syntax highlighting/linting) rather than a giant Python string
    literal, but the page is still served as one self-contained HTML
    response with everything inlined (no extra HTTP round-trips, no new
    routes) -- token substitution happens once at import time, not per
    request."""
    template = (_DASHBOARD_STATIC_DIR / "page.html").read_text(encoding="utf-8")
    css = (_DASHBOARD_STATIC_DIR / "style.css").read_text(encoding="utf-8")
    theme_js = (_DASHBOARD_STATIC_DIR / "theme.js").read_text(encoding="utf-8")
    app_js = (_DASHBOARD_STATIC_DIR / "app.js").read_text(encoding="utf-8")
    return (
        template.replace("__SDD_DASHBOARD_CSS__", css)
        .replace("__SDD_DASHBOARD_THEME_JS__", theme_js)
        .replace("__SDD_DASHBOARD_APP_JS__", app_js)
    )


_PAGE = _load_page()


def _fetch_doc_content(feature: str, doc: str) -> dict | None:
    """Raw markdown for in-dashboard viewing — local file read only.

    feature/doc are validated by the caller (_SAFE_TOKEN) before this is
    ever invoked; resolve_doc_path handles living-doc/context routing the
    same way every other CLI command does.
    """
    from sdd.utils.validate import resolve_doc_path

    try:
        path = resolve_doc_path(doc, feature)
    except ValueError:
        return None
    if not path.exists() or not path.is_file():
        return None
    return {"path": str(path), "content": path.read_text(errors="replace")}


_JIRA_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*-\d+$")


def _fetch_export_ticket_statuses(feature: str, jira_client) -> dict:
    """Live Jira status for the Epic/Story/Task tickets from the
    progressive export (docs/jira/{feature}/keys.yml, written by `sdd
    jira push`) -- unlike the review-gate tickets above, status.py's
    local_links.jira only ever has cached key+url, never a live status,
    since nothing previously fetched one. One batched 'key in (...)' JQL
    query covers the whole Epic+Stories+Tasks set in a single API call.
    Folded into _fetch_review_links' response so there's still only one
    "Check Jira/Confluence status" action per feature, not two buttons.

    Keys are re-validated against Jira's own KEY-123 format before being
    inlined into the JQL string -- they normally come straight from
    Jira's own issue-creation response (via `sdd jira push`), but
    keys.yml is a plain file on disk a user could hand-edit, and JQL has
    no query-parameter binding to lean on the way SQL does.
    """
    if jira_client is None:
        return {}
    from sdd.utils.status import _local_jira_links

    local = _local_jira_links(Path("."), feature, base_url=None)
    all_keys = []
    if local["epic"]:
        all_keys.append(local["epic"]["key"])
    all_keys += [s["key"] for s in local["stories"]]
    all_keys += [t["key"] for t in local["tasks"]]
    all_keys = [k for k in all_keys if _JIRA_KEY_RE.match(k)]
    if not all_keys:
        return {}

    try:
        issues = jira_client.search(
            f"key in ({', '.join(all_keys)})",
            fields=["status"],
            max_results=len(all_keys),
        )
    except Exception as e:
        return {"error": str(e)}
    return {
        "statuses": {
            issue["key"]: issue.get("fields", {}).get("status", {}).get("name")
            for issue in issues
        }
    }


def _fetch_review_links(feature: str) -> dict:
    """Live Jira/Confluence lookup for review-gate tickets (the ones
    created by `sdd review submit`) plus live status for the progressive
    Jira export's Epic/Story/Task tickets (see
    _fetch_export_ticket_statuses). status.py's local_links.jira_review
    gives the passive 5s poll an instant-but-possibly-stale fallback pill
    (populated the moment `sdd review submit`/`apply` touches the
    ticket) — this function is what actually re-verifies against Jira/
    Confluence and adds status/comments the local cache never has.
    Network call, on-demand only — never invoked by /api/status. Jira
    lookup is feature-qualified to match
    the label `sdd review submit` writes; Confluence page titles only
    support {project} today, matching `sdd review status`'s own behavior,
    so the Confluence half is still shared across features on one project.

    Also surfaces the same APPROVED/NEEDS_REVISION/PENDING classification
    and reviewer comments that `sdd review check --doc` prints, by reusing
    review.py's own classification helper rather than re-deriving it here
    (keeps the two in lockstep instead of drifting).
    """
    from sdd.commands.review import _extract_text, _get_review_status
    from sdd.utils.atlassian_auth import load_confluence_session, load_jira_session
    from sdd.utils.confluence_client import ConfluenceClient
    from sdd.utils.integrations import load_integrations
    from sdd.utils.jira_client import JiraClient

    try:
        cfg = load_integrations()
    except FileNotFoundError as e:
        return {"error": str(e)}
    if not cfg.jira and not cfg.confluence:
        return {
            "error": "Neither jira: nor confluence: configured in .specify/integrations.yml"
        }

    try:
        if cfg.jira:
            prof, session = load_jira_session(cfg)
            jira_client = JiraClient(session, prof.base_url)
        else:
            jira_client = None
        if cfg.confluence:
            cf_prof, cf_session = load_confluence_session(cfg)
            cf_client = ConfluenceClient(cf_session, cf_prof.base_url)
        else:
            cf_prof, cf_client = None, None
    except Exception as e:
        return {"error": f"Could not authenticate: {e}"}

    manifest = read_manifest() or {}
    project_name = (manifest.get("project") or {}).get("name", "Project")

    docs: dict = {}
    for doc_key, dr in (cfg.document_reviews or {}).items():
        entry: dict = {"jira": None, "confluence": None}

        if jira_client:
            # jira_client is only ever set (above) when cfg.jira was truthy,
            # so this is always non-None here -- mypy can't see the
            # correlation across the two variables.
            assert cfg.jira is not None
            try:
                issue = jira_client.find_by_label(
                    cfg.jira.key_for("review"), f"sdd-doc:{feature}:{doc_key}"
                )
                if issue:
                    review_status, comments, _ = _get_review_status(
                        doc_key,
                        jira_client,
                        cfg.jira.key_for("review"),
                        cfg,
                        feature,
                    )
                    entry["jira"] = {
                        "key": issue["key"],
                        "url": f"{prof.base_url}/browse/{issue['key']}",
                        "status": issue.get("fields", {}).get("status", {}).get("name"),
                        "review_status": review_status,
                        "comments": [
                            {
                                "author": (c.get("author") or {}).get(
                                    "displayName", "Unknown"
                                ),
                                "created": c.get("created", "")[:10],
                                "text": _extract_text(c.get("body", "")),
                            }
                            for c in comments
                        ],
                    }
            except Exception as e:
                entry["jira"] = {"error": str(e)}

        if cf_client:
            # cf_client/cf_prof are only ever set (above) when cfg.confluence
            # was truthy -- same false-correlation gap as the jira_client
            # case above.
            assert cfg.confluence is not None
            assert cf_prof is not None
            try:
                title = dr.confluence_page.replace("{project}", project_name)
                page = cf_client.get_page_by_title(cfg.confluence.space_key, title)
                if page:
                    entry["confluence"] = {
                        "title": title,
                        "url": f"{cf_prof.base_url}/wiki/pages/viewpage.action?pageId={page['id']}",
                    }
            except Exception as e:
                entry["confluence"] = {"error": str(e)}

        docs[doc_key] = entry

    return {
        "docs": docs,
        "export": _fetch_export_ticket_statuses(feature, jira_client),
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


_COMMENTS_FILE = Path(".specify") / ".dashboard-comments.json"
_MAX_TEXT_LEN = 2000  # by/note/comment fields — generous but bounded


def _clip_text(value, max_len=_MAX_TEXT_LEN) -> str:
    text = str(value or "").strip()
    return text[:max_len]


def _jira_client_for_comments():
    """Build (client, cfg) for posting a Jira comment, or None if Jira isn't
    configured. Never raises — callers treat None as 'skip, not an error'."""
    from sdd.utils.atlassian_auth import load_jira_session
    from sdd.utils.integrations import load_integrations
    from sdd.utils.jira_client import JiraClient

    try:
        cfg = load_integrations()
    except FileNotFoundError:
        return None
    if not cfg.jira:
        return None
    try:
        prof, session = load_jira_session(cfg)
        return JiraClient(session, prof.base_url), cfg
    except Exception:
        return None


def _post_jira_comment(feature: str, doc: str, text: str) -> dict:
    """Best-effort comment on the doc's review-gate Jira ticket (found via
    the same feature-qualified sdd-doc:{feature}:{doc} label sdd review
    submit/status/check already use). Never raises — a Jira hiccup must
    never block a local approval or comment, matching the existing
    Confluence-on-approve behavior in `sdd review approve --local`."""
    built = _jira_client_for_comments()
    if built is None:
        return {"posted": False, "reason": "Jira not configured"}
    client, cfg = built
    try:
        issue = client.find_by_label(
            cfg.jira.key_for("review"), f"sdd-doc:{feature}:{doc}"
        )
        if not issue:
            return {
                "posted": False,
                "reason": "no review ticket found for this document",
            }
        client.add_comment(issue["key"], text)
        return {"posted": True, "issue_key": issue["key"]}
    except Exception as e:
        return {"posted": False, "reason": str(e)}


def _do_approve(feature: str, doc: str, by: str, note: str) -> dict:
    """Approve a document from the dashboard — mirrors `sdd review approve
    --local` exactly (same .specify/.local-approvals.yml, same Status:
    header flip, same automatic Confluence mirror) so the CLI and the
    dashboard share one audit trail, plus a best-effort Jira comment.

    .local-approvals.yml is keyed by bare doc name, not feature — this
    matches the existing `sdd review approve`/`review check` format
    exactly (interoperability with the CLI wins over fixing that gap
    unilaterally here); on a multi-feature project this doc key doesn't
    distinguish which feature was approved, a pre-existing limitation of
    those CLI commands, not something introduced by the dashboard.
    """
    from sdd.commands.review import (
        _doc_md_path,
        _mark_md_approved,
        _push_doc_page,
        _save_local_approval,
    )

    by = _clip_text(by) or "dashboard user"
    note = _clip_text(note) or "approved via dashboard"

    _save_local_approval(doc, by, note)
    result: dict = {
        "local_approval": True,
        "md_updated": False,
        "confluence": None,
        "jira_comment": None,
    }

    md_path = _doc_md_path(doc, feature)
    if md_path and md_path.exists():
        result["md_updated"] = _mark_md_approved(md_path)
        try:
            manifest = read_manifest() or {}
            feature_name = feature or (manifest.get("project") or {}).get("feature", "")
            title = _push_doc_page(doc, md_path, feature_name)
            result["confluence"] = {"updated": bool(title), "title": title}
        except Exception as e:
            result["confluence"] = {"error": str(e)}
    else:
        result["error"] = f"{doc}.md not found for feature {feature}"

    result["jira_comment"] = _post_jira_comment(
        feature, doc, f"Approved via SDD Dashboard by {by}."
    )
    return result


def _load_comments() -> dict:
    if not _COMMENTS_FILE.exists():
        return {}
    try:
        return json.loads(_COMMENTS_FILE.read_text())
    except Exception:
        return {}


def _do_comment(feature: str, doc: str, by: str, text: str) -> dict:
    """Save a review comment locally (feature-scoped — this is a new store,
    so unlike .local-approvals.yml there's no legacy format to match) and
    best-effort mirror it to the doc's Jira review ticket, if configured.
    Confluence comment posting isn't implemented — ConfluenceClient has no
    comment-write method today; only Jira and the local record apply."""
    by = _clip_text(by) or "dashboard user"
    text = _clip_text(text)
    if not text:
        return {"error": "comment text is empty"}

    comments = _load_comments()
    key = f"{feature}/{doc}"
    entry = {
        "by": by,
        "text": text,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    comments.setdefault(key, []).append(entry)
    _COMMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _COMMENTS_FILE.write_text(json.dumps(comments, indent=2))

    jira_comment = _post_jira_comment(feature, doc, f"{by} (via SDD Dashboard): {text}")
    return {"saved": True, "comment": entry, "jira_comment": jira_comment}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        if parsed.path in ("/", "/index.html"):
            body = _PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/api/status":
            try:
                self._send_json(build_project_status("."))
            except Exception as e:
                # A malformed file anywhere under .specify/ or docs/jira/
                # (hand-edited, from an older CLI version, etc.) must not
                # take down every future poll with a bare connection
                # reset -- surface it as JSON so the frontend can show a
                # visible error instead of silently going stale.
                self._send_json({"error": f"{type(e).__name__}: {e}"}, status=500)

        elif parsed.path == "/api/doc":
            feature = (qs.get("feature") or [""])[0]
            doc = (qs.get("doc") or [""])[0]
            if not (_SAFE_TOKEN.match(feature) and _SAFE_TOKEN.match(doc)):
                self._send_json({"error": "invalid feature/doc"}, status=400)
                return
            result = _fetch_doc_content(feature, doc)
            if result is None:
                self._send_json({"error": "not found"}, status=404)
            else:
                self._send_json(result)

        elif parsed.path == "/api/review-links":
            access_error = self._check_review_links_access()
            if access_error is not None:
                self._send_json({"error": access_error}, status=403)
                return
            feature = (qs.get("feature") or [""])[0]
            if not _SAFE_TOKEN.match(feature):
                self._send_json({"error": "invalid feature"}, status=400)
                return
            self._send_json(_fetch_review_links(feature))

        elif parsed.path == "/api/dashboard-info":
            # Never includes the token itself -- that's only ever handed out
            # via the auto-opened URL's ?token= param and the console
            # printout, both of which only the person who ran `sdd
            # dashboard` sees. This endpoint just tells the page's own JS
            # whether to show write controls and the network-sharing banner.
            self._send_json(
                {
                    "is_local": _ACCESS["is_local"],
                    "writes_enabled": _ACCESS["writes_enabled"],
                }
            )

        else:
            self.send_response(404)
            self.end_headers()

    def _read_json_body(self, max_bytes: int = 65536) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if length <= 0 or length > max_bytes:
            return None
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _check_origin_and_token(self) -> str | None:
        """Origin/Host check plus token check, non-loopback only -- the two
        gates shared by every non-local request regardless of whether it's
        a write or a read that triggers a live third-party call.

        1. Origin/Host check (defense in depth): if the browser sent an
           Origin header, it must match this server's own host:port. A
           cross-origin page (malicious or just a stray open tab) can't
           forge this the way it could once ambient cookies -- this runs
           before the token check so a mismatched Origin is rejected even
           if a token somehow leaked.
        2. Token check: the Origin check alone doesn't stop another device
           on the same network from calling the API directly (curl, not a
           browser) -- the token is what actually authenticates the
           request. Sent as a custom header (X-SDD-Token), never a cookie,
           precisely so it's never included automatically by the browser
           on a request this page didn't initiate itself -- that property
           is what makes it double as CSRF protection, not just as auth.

        Callers are responsible for the is_local short-circuit -- this
        function assumes it's already been established that the request
        needs checking at all.
        """
        origin = self.headers.get("Origin")
        if origin and origin not in _ACCESS["allowed_origins"]:
            return f"Origin not allowed: {origin}"
        token = self.headers.get("X-SDD-Token")
        if not token or not secrets.compare_digest(token, _ACCESS["token"] or ""):
            return "Missing or invalid X-SDD-Token header."
        return None

    def _check_write_access(self) -> str | None:
        """Returns an error message if this write request should be
        rejected, or None if it's allowed.

        1. Loopback binds (the default `sdd dashboard`, no flags) skip
           straight to None -- today's zero-friction local UX is
           completely unaffected.
        2. Read-only mode: non-loopback binds without --write reject every
           POST outright, regardless of token -- writes are simply off.
        3. Otherwise, the shared Origin+token check from
           _check_origin_and_token() above.
        """
        if _ACCESS["is_local"]:
            return None
        if not _ACCESS["writes_enabled"]:
            return (
                "Dashboard is read-only over the network. Restart with "
                "--share --write to enable writes (requires the printed token)."
            )
        return self._check_origin_and_token()

    def _check_review_links_access(self) -> str | None:
        """Returns an error message if this /api/review-links request
        should be rejected, or None if it's allowed.

        Unlike _check_write_access(), this applies even in read-only share
        mode: this endpoint makes a *live* call to Jira/Confluence using
        the credentials stored on the machine running `sdd dashboard`, for
        whatever --feature the caller names -- "read-only" describes local
        writes, not third-party API calls made under the host's own
        credentials, so this needs the same Origin+token gate as a write
        the moment the dashboard is reachable off loopback at all.
        """
        if _ACCESS["is_local"]:
            return None
        return self._check_origin_and_token()

    def do_POST(self):
        parsed = urlparse(self.path)

        write_error = self._check_write_access()
        if write_error is not None:
            self._send_json({"error": write_error}, status=403)
            return

        payload = self._read_json_body()
        if payload is None:
            self._send_json({"error": "invalid or oversized JSON body"}, status=400)
            return

        feature = str(payload.get("feature", ""))
        doc = str(payload.get("doc", ""))
        if not (_SAFE_TOKEN.match(feature) and _SAFE_TOKEN.match(doc)):
            self._send_json({"error": "invalid feature/doc"}, status=400)
            return

        if parsed.path == "/api/approve":
            try:
                with _WRITE_LOCK:
                    result = _do_approve(
                        feature, doc, payload.get("by", ""), payload.get("note", "")
                    )
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)

        elif parsed.path == "/api/comment":
            try:
                with _WRITE_LOCK:
                    result = _do_comment(
                        feature, doc, payload.get("by", ""), payload.get("text", "")
                    )
                status = 400 if "error" in result else 200
                self._send_json(result, status=status)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)

        else:
            self.send_response(404)
            self.end_headers()


def _lan_ip() -> str | None:
    """Best-effort LAN-reachable IP for this machine. Opens no connection —
    UDP connect() just makes the OS pick a local route/interface."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return None


@click.command()
@click.option("--port", default=4747, show_default=True, help="Local port to serve on")
@click.option(
    "--host",
    default="127.0.0.1",
    show_default=True,
    help="Bind address for advanced/custom use. Prefer --share for "
    "the common case of letting teammates on the same network in.",
)
@click.option(
    "--share",
    is_flag=True,
    help="Shortcut for --host 0.0.0.0 — reachable by teammates on "
    "your network. Read-only by default; add --write to also "
    "allow approvals/comments (requires the printed token).",
)
@click.option(
    "--write",
    is_flag=True,
    help="Allow write actions (approve/comment) over a non-local "
    "bind (--share or a manual --host). Ignored/always-on for "
    "the local-only default. Generates a session token that "
    "must be sent on every write request.",
)
@click.option("--no-open", is_flag=True, help="Don't auto-open a browser tab")
def dashboard_command(port, host, share, write, no_open):
    """Local web UI over the current project's .specify/ status.

    Shows pipeline progress, task status, and token usage per feature.
    Mostly a viewer — it also lets you Approve a document or leave a
    review comment, which updates the local .md Status header (same as
    `sdd review approve --local`), mirrors to Confluence if configured,
    and posts a best-effort Jira comment. Works without Jira/Confluence
    configured at all (unlike `sdd review status`).

    Three modes:

    \b
      sdd dashboard                 # 127.0.0.1 only — writes enabled, no token needed
      sdd dashboard --share         # reachable on your network — read-only
      sdd dashboard --share --write # reachable on your network — writes enabled,
                                     # requires the session token printed below
                                     # (and baked into the auto-opened URL for you)

    A plain --host 0.0.0.0 (without --share) follows the same --write/token
    rule as --share — --share is just a shortcut for the common case.
    """
    # Deliberate, opt-in network-sharing feature (--share), not an accidental
    # bind: gated behind the session-token + Origin-check + read-only-by-
    # default access control implemented in _check_write_access() above.
    effective_host = "0.0.0.0" if share else host  # nosec B104
    is_local = effective_host in ("127.0.0.1", "localhost")
    writes_enabled = is_local or write
    # Generated for *any* non-local bind, not just --write ones: the token
    # also gates /api/review-links (a live Jira/Confluence call made under
    # this machine's own credentials), which needs authenticating even
    # when writes are off -- "read-only" describes local writes, not
    # third-party API calls made on the caller's behalf.
    token = secrets.token_urlsafe(24) if not is_local else None

    lan_ip = None if is_local else _lan_ip()
    allowed_origins = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
    if lan_ip:
        allowed_origins.add(f"http://{lan_ip}:{port}")

    _ACCESS["is_local"] = is_local
    _ACCESS["writes_enabled"] = writes_enabled
    _ACCESS["token"] = token
    _ACCESS["allowed_origins"] = allowed_origins

    token_qs = f"?token={token}" if token else ""
    local_url = f"http://127.0.0.1:{port}/{token_qs}"
    server = ThreadingHTTPServer((effective_host, port), _Handler)

    console.print()
    console.print(
        f"  [bold cyan]SDD Dashboard[/bold cyan]  [dim]running at http://127.0.0.1:{port}/[/dim]"
    )

    if not is_local:
        if lan_ip:
            console.print(
                f"  [dim]Reachable on your network at:[/dim]  http://{lan_ip}:{port}/{token_qs}"
            )
        if writes_enabled:
            console.print(
                "  [yellow]⚠  Write access enabled over the network — anyone with the link "
                "above (which includes the token) can approve documents and post review "
                "comments on your behalf. Treat that link like a credential: only share it "
                "with people you trust, over a channel you trust.[/yellow]"
            )
        else:
            console.print(
                "  [dim]Read-only — viewers on your network can see this project's "
                ".specify/ status but cannot approve documents or post comments. "
                "Add --write to enable that.[/dim]"
            )
        console.print(
            '  [dim]"Check Jira/Confluence status" makes a live call under this '
            "machine's own credentials for any --feature the caller names — the "
            "link above (which includes the token) is required for that too, "
            "even read-only. Treat it like a credential.[/dim]"
        )

    console.print("  [dim]Ctrl+C to stop[/dim]")
    console.print()

    if not no_open:
        webbrowser.open(local_url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        console.print("\n  Stopped.")
    finally:
        server.server_close()
