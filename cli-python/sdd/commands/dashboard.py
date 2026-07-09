"""sdd dashboard — local, read-only web UI over the status.py snapshot.

Stdlib-only HTTP server (no new dependency) serving a single static page
that polls /api/status. Nothing here writes to .specify/ — it's a viewer.

/api/review-links and /api/doc take feature/doc query params from HTTP
requests — once this server is bound to something other than 127.0.0.1
(see --host), that's network-reachable input, not a trusted local CLI
flag. Both values are validated against _SAFE_TOKEN before touching the
filesystem or building any path, closing off path traversal.
"""
from __future__ import annotations
import json
import re
import socket
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import click
from rich.console import Console

from sdd.utils.status import build_project_status
from sdd.utils.manifest import read_manifest

console = Console()

_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_-]+$")

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SDD Dashboard</title>
<style>
  :root {
    color-scheme: light dark;
    --bg: #ffffff; --fg: #1a1a1a; --muted: #6b7280; --card: #f5f5f7;
    --border: #e2e2e6; --accent: #2563eb;
    --ok: #16a34a; --warn: #ca8a04; --bad: #dc2626; --dim: #9ca3af;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0f1115; --fg: #e6e6e6; --muted: #9aa0a6; --card: #1a1d24;
      --border: #2a2d35; --accent: #60a5fa;
      --ok: #4ade80; --warn: #facc15; --bad: #f87171; --dim: #6b7280;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 2rem; background: var(--bg); color: var(--fg);
    font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }
  h1 { font-size: 1.3rem; margin: 0 0 .25rem; }
  h2 { font-size: 1rem; margin: 0 0 .75rem; color: var(--muted); font-weight: 600; }
  .sub { color: var(--muted); font-size: .85rem; margin-bottom: 1.5rem; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
  .card {
    background: var(--card); border: 1px solid var(--border); border-radius: 10px;
    padding: 1rem 1.2rem;
  }
  .kv { display: flex; justify-content: space-between; padding: .3rem 0; font-size: .9rem; }
  .kv span:first-child { color: var(--muted); }
  .badge {
    display: inline-block; padding: .1rem .55rem; border-radius: 999px;
    font-size: .75rem; font-weight: 600; text-transform: uppercase; letter-spacing: .02em;
  }
  .b-ok   { background: color-mix(in srgb, var(--ok) 18%, transparent); color: var(--ok); }
  .b-warn { background: color-mix(in srgb, var(--warn) 18%, transparent); color: var(--warn); }
  .b-bad  { background: color-mix(in srgb, var(--bad) 18%, transparent); color: var(--bad); }
  .b-dim  { background: color-mix(in srgb, var(--dim) 25%, transparent); color: var(--muted); }
  table { width: 100%; border-collapse: collapse; font-size: .88rem; }
  th, td { text-align: left; padding: .4rem .5rem; border-bottom: 1px solid var(--border); }
  th { color: var(--muted); font-weight: 600; font-size: .75rem; text-transform: uppercase; }
  tr:last-child td { border-bottom: none; }
  .feature-block { margin-bottom: 2rem; }
  .feature-title { font-size: 1.05rem; font-weight: 600; margin-bottom: .75rem; display: flex; align-items: center; gap: .75rem; flex-wrap: wrap; }
  .bar { display: flex; height: 8px; border-radius: 4px; overflow: hidden; background: var(--border); margin: .5rem 0 .75rem; }
  .bar span { display: block; }
  .empty { color: var(--muted); font-style: italic; padding: 1rem 0; }
  .refresh-note { color: var(--dim); font-size: .78rem; margin-top: 2rem; }
  .link-btn {
    background: var(--card); border: 1px solid var(--border); border-radius: 6px;
    padding: .15rem .55rem; font-size: .76rem; cursor: pointer; color: var(--fg); font: inherit;
  }
  .link-btn:hover { border-color: var(--accent); }
  .pill {
    display: inline-block; padding: .05rem .5rem; border-radius: 999px; font-size: .72rem;
    border: 1px solid var(--border); text-decoration: none; margin-left: .3rem; white-space: nowrap;
  }
  .pill-jira { color: var(--accent); border-color: var(--accent); }
  .pill-cf   { color: var(--ok); border-color: var(--ok); }
  .pill-bad  { color: var(--bad); border-color: var(--bad); }
  .links-cell { white-space: nowrap; }
  .doc-detail-row td { padding: 0; border-bottom: 1px solid var(--border); }
  .doc-detail {
    margin: 0; padding: .75rem 1rem; background: var(--bg); max-height: 360px; overflow: auto;
    font-size: .8rem; white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  .check-links-row { display: flex; align-items: center; gap: .6rem; margin: .5rem 0 1rem; }
</style>
</head>
<body>
  <h1>SDD Dashboard</h1>
  <div class="sub" id="generated-at">loading…</div>
  <div id="root"></div>
  <div class="refresh-note">Read-only snapshot of <code>.specify/</code> — refreshes every 5s. Task/PR status reflects tasks.md, not live PR state.
    "View" reads the raw .md file from disk. Jira/Confluence pills next to a document are from local cache (progressive export /
    <code>sdd confluence push</code>) — "Check Jira/Confluence review links" additionally queries live for <code>sdd review submit</code> tickets.</div>

<script>
// Client-side only — never re-fetched from /api/status, so it survives
// the 5s poll: which doc panels are expanded, their fetched content, and
// any live Jira/Confluence review-link results the user asked for.
const state = { expandedDocs: new Set(), docContents: {}, reviewLinks: {} };
let lastData = null;

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function badge(status, kind) {
  if (!status) return '<span class="badge b-dim">unknown</span>';
  const s = String(status).toLowerCase();
  let cls = 'b-dim';
  if (kind === 'doc') {
    if (s.includes('approved')) cls = 'b-ok';
    else if (s.includes('draft') || s.includes('proposed') || s.includes('open')) cls = 'b-warn';
  } else if (kind === 'task') {
    if (s.includes('done') || s.includes('complete')) cls = 'b-ok';
    else if (s.includes('progress')) cls = 'b-warn';
    else if (s.includes('not started')) cls = 'b-dim';
  } else if (kind === 'gate1') {
    if (s === 'passed') cls = 'b-ok';
    else cls = 'b-warn';
  }
  return `<span class="badge ${cls}">${status}</span>`;
}

function renderProject(p, constitution) {
  return `
  <div class="grid">
    <div class="card">
      <h2>Project</h2>
      <div class="kv"><span>Name</span><span>${p.name || '—'}</span></div>
      <div class="kv"><span>Type</span><span>${p.project_type || '—'}</span></div>
      <div class="kv"><span>Scope</span><span>${p.scope || '(none — sdd-micro)'}</span></div>
      <div class="kv"><span>Workflow</span><span>${p.workflow_mode || '—'}</span></div>
      <div class="kv"><span>sdd_version</span><span>${p.sdd_version || '—'}</span></div>
    </div>
    <div class="card">
      <h2>Constitution — GATE-1</h2>
      <div class="kv"><span>Exists</span><span>${constitution.exists ? 'yes' : 'no'}</span></div>
      <div class="kv"><span>Status (inferred)</span><span>${badge(constitution.gate1_inferred, 'gate1')}</span></div>
      <div class="sub" style="margin:.5rem 0 0">No machine-readable Draft/Confirmed flag is written to
        constitution.md — this is inferred from whether any downstream doc exists.</div>
    </div>
  </div>`;
}

function renderTasks(tasks) {
  if (!tasks || tasks.total === 0) {
    return '<div class="empty">No tasks.md yet.</div>';
  }
  const pct = n => tasks.total ? (100 * n / tasks.total).toFixed(0) : 0;
  const rows = tasks.items.map(t => `
    <tr><td>${t.id}</td><td>${t.title}</td><td>${badge(t.status, 'task')}</td></tr>
  `).join('');
  return `
    <div class="bar">
      <span style="width:${pct(tasks.done)}%;background:var(--ok)"></span>
      <span style="width:${pct(tasks.in_progress)}%;background:var(--warn)"></span>
      <span style="width:${pct(tasks.not_started)}%;background:var(--border)"></span>
    </div>
    <div class="sub">${tasks.done} done · ${tasks.in_progress} in progress · ${tasks.not_started} not started · format: ${tasks.format}</div>
    <table><thead><tr><th>ID</th><th>Title</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table>
  `;
}

function linkPill(kind, link) {
  if (!link) return '';
  if (link.error) return `<span class="pill pill-bad" title="${escapeHtml(link.error)}">${kind} ⚠</span>`;
  const label = kind === 'Jira' ? `Jira ${link.key}` : 'Confluence';
  return link.url
    ? `<a class="pill pill-${kind === 'Jira' ? 'jira' : 'cf'}" href="${link.url}" target="_blank" rel="noopener">${label}</a>`
    : `<span class="pill pill-${kind === 'Jira' ? 'jira' : 'cf'}" title="No Atlassian base_url configured — run sdd config init">${label}</span>`;
}

function renderDocRow(d, feature, localConfluence, reviewEntry) {
  const key = feature + '|' + d.key;
  const expanded = state.expandedDocs.has(key);
  const localCf = (localConfluence || {})[d.key];
  const reviewJira = reviewEntry && reviewEntry.docs ? reviewEntry.docs[d.key]?.jira : null;
  const reviewCf   = reviewEntry && reviewEntry.docs ? reviewEntry.docs[d.key]?.confluence : null;
  const links = [
    linkPill('Jira', reviewJira),
    linkPill('Confluence', localCf || reviewCf),
  ].join('');
  const row = `
    <tr>
      <td>${d.label}</td>
      <td>${badge(d.status, 'doc')}</td>
      <td class="links-cell">
        <button class="link-btn" data-action="view-doc" data-feature="${feature}" data-doc="${d.key}">${expanded ? 'Hide' : 'View'}</button>${links}
      </td>
    </tr>`;
  const detail = expanded
    ? `<tr class="doc-detail-row"><td colspan="3"><pre class="doc-detail">${escapeHtml(state.docContents[key] ?? 'Loading…')}</pre></td></tr>`
    : '';
  return row + detail;
}

function renderDocs(docs, stage, feature, localConfluence) {
  if (!docs || docs.length === 0) return '<div class="empty">No spec documents yet.</div>';
  const reviewEntry = state.reviewLinks[feature];
  const rows = docs.map(d => renderDocRow(d, feature, localConfluence, typeof reviewEntry === 'object' ? reviewEntry : null)).join('');
  const next = stage.next ? `<div class="sub">Next: ${stage.next}</div>` : '';
  return `<table><thead><tr><th>Document</th><th>Status</th><th>Links</th></tr></thead><tbody>${rows}</tbody></table>${next}`;
}

function renderJiraExport(jira) {
  if (!jira || (!jira.epic && jira.stories.length === 0 && jira.tasks.length === 0)) {
    return '<div class="empty">No progressive Jira export yet (run /jira-push or sdd jira push).</div>';
  }
  const list = arr => arr.length
    ? arr.map(x => x.url ? `<a href="${x.url}" target="_blank" rel="noopener">${x.key}</a>` : x.key).join(', ')
    : '—';
  return `
    <div class="kv"><span>Epic</span><span>${jira.epic ? list([jira.epic]) : '—'}</span></div>
    <div class="kv"><span>Stories (${jira.stories.length})</span><span>${list(jira.stories)}</span></div>
    <div class="kv"><span>Tasks (${jira.tasks.length})</span><span>${list(jira.tasks)}</span></div>
  `;
}

function renderReviewLinksControl(feature) {
  const entry = state.reviewLinks[feature];
  let status = '';
  if (entry === 'loading') status = '<span class="sub">Checking…</span>';
  else if (entry && entry.error) status = `<span class="sub" style="color:var(--bad)">${escapeHtml(entry.error)}</span>`;
  else if (entry && entry.checked_at) status = `<span class="sub">Checked ${entry.checked_at}</span>`;
  return `
    <div class="check-links-row">
      <button class="link-btn" data-action="check-review-links" data-feature="${feature}">🔄 Check Jira/Confluence review links</button>
      ${status}
    </div>`;
}

function renderTokenUsage(tu) {
  if (!tu) return '<div class="empty">Token usage logging not enabled for this feature.</div>';
  return `
    <div class="kv"><span>Total Est. Input Tokens</span><span>${tu.total_input ?? '—'}</span></div>
    <div class="kv"><span>Total Est. Output Tokens</span><span>${tu.total_output ?? '—'}</span></div>
    <div class="kv"><span>Total Est. Cost (USD)</span><span>${tu.total_cost ?? '—'}</span></div>
    <div class="kv"><span>Commands logged</span><span>${tu.commands_logged ?? '—'}</span></div>
    <div class="kv"><span>Last updated</span><span>${tu.last_updated ?? '—'}</span></div>
  `;
}

function renderFeature(f) {
  const local = f.local_links || { jira: null, confluence: {} };
  return `
  <div class="feature-block">
    <div class="feature-title">${f.name}</div>
    ${renderReviewLinksControl(f.name)}
    <div class="grid">
      <div class="card"><h2>Pipeline</h2>${renderDocs(f.docs, f.current_stage, f.name, local.confluence)}</div>
      <div class="card"><h2>Tasks</h2>${renderTasks(f.tasks)}</div>
      <div class="card"><h2>Token Usage</h2>${renderTokenUsage(f.token_usage)}</div>
      <div class="card"><h2>Jira Export</h2>${renderJiraExport(local.jira)}</div>
    </div>
  </div>`;
}

function render() {
  if (!lastData) return;
  const data = lastData;
  document.getElementById('generated-at').textContent = 'Generated ' + data.generated_at;
  const features = data.features.length
    ? data.features.map(renderFeature).join('')
    : '<div class="empty">No features under .specify/features/ yet.</div>';
  document.getElementById('root').innerHTML = renderProject(data.project, data.constitution) + features;
}

async function refresh() {
  const res = await fetch('/api/status');
  lastData = await res.json();
  render();
}

// Event delegation on #root: click handlers survive innerHTML replacement
// on every refresh(), since the listener lives on the stable parent node.
document.getElementById('root').addEventListener('click', async (e) => {
  const btn = e.target.closest('[data-action]');
  if (!btn) return;
  const feature = btn.dataset.feature;

  if (btn.dataset.action === 'view-doc') {
    const doc = btn.dataset.doc;
    const key = feature + '|' + doc;
    if (state.expandedDocs.has(key)) {
      state.expandedDocs.delete(key);
      render();
      return;
    }
    state.expandedDocs.add(key);
    if (!(key in state.docContents)) {
      state.docContents[key] = 'Loading…';
      render();
      try {
        const res = await fetch(`/api/doc?feature=${encodeURIComponent(feature)}&doc=${encodeURIComponent(doc)}`);
        const data = await res.json();
        state.docContents[key] = data.content ?? ('Error: ' + (data.error || 'unknown'));
      } catch (err) {
        state.docContents[key] = 'Error: ' + err;
      }
    }
    render();

  } else if (btn.dataset.action === 'check-review-links') {
    state.reviewLinks[feature] = 'loading';
    render();
    try {
      const res = await fetch(`/api/review-links?feature=${encodeURIComponent(feature)}`);
      state.reviewLinks[feature] = await res.json();
    } catch (err) {
      state.reviewLinks[feature] = { error: String(err) };
    }
    render();
  }
});

refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""


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


def _fetch_review_links(feature: str) -> dict:
    """Live Jira/Confluence lookup for review-gate tickets (the ones
    created by `sdd review submit`) — these are never cached locally
    (see status.py's local_links, which covers only the progressive Jira
    export and sdd confluence push/draft). Network call, on-demand only —
    never invoked by /api/status. feature is accepted for API symmetry;
    document_reviews page titles only support {project} today, matching
    `sdd review status`'s own behavior, so results are the same across
    features until that's extended.
    """
    from sdd.utils.integrations import load_integrations
    from sdd.utils.atlassian_auth import load_profile, build_session
    from sdd.utils.jira_client import JiraClient
    from sdd.utils.confluence_client import ConfluenceClient

    try:
        cfg = load_integrations()
    except FileNotFoundError as e:
        return {"error": str(e)}
    if not cfg.document_reviews:
        return {"error": "No document_reviews configured in .specify/integrations.yml"}

    try:
        prof = load_profile(cfg.profile)
        session = build_session(prof)
    except Exception as e:
        return {"error": f"Could not authenticate: {e}"}

    jira_client = JiraClient(session, prof.base_url) if cfg.jira else None
    cf_client = ConfluenceClient(session, prof.base_url) if cfg.confluence else None

    manifest = read_manifest() or {}
    project_name = (manifest.get("project") or {}).get("name", "Project")

    docs: dict = {}
    for doc_key, dr in cfg.document_reviews.items():
        entry: dict = {"jira": None, "confluence": None}

        if jira_client:
            try:
                issue = jira_client.find_by_label(cfg.jira.project_key, f"sdd-doc:{doc_key}")
                if issue:
                    entry["jira"] = {
                        "key": issue["key"],
                        "url": f"{prof.base_url}/browse/{issue['key']}",
                        "status": issue.get("fields", {}).get("status", {}).get("name"),
                    }
            except Exception as e:
                entry["jira"] = {"error": str(e)}

        if cf_client:
            try:
                title = dr.confluence_page.replace("{project}", project_name)
                page = cf_client.get_page_by_title(cfg.confluence.space_key, title)
                if page:
                    entry["confluence"] = {
                        "title": title,
                        "url": f"{prof.base_url}/wiki/pages/viewpage.action?pageId={page['id']}",
                    }
            except Exception as e:
                entry["confluence"] = {"error": str(e)}

        docs[doc_key] = entry

    return {"docs": docs, "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # noqa: A003 - silence default access logging
        pass

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 - http.server API
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
            self._send_json(build_project_status("."))

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
            feature = (qs.get("feature") or [""])[0]
            if not _SAFE_TOKEN.match(feature):
                self._send_json({"error": "invalid feature"}, status=400)
                return
            self._send_json(_fetch_review_links(feature))

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
@click.option("--host", default="127.0.0.1", show_default=True,
              help="Bind address. Use 0.0.0.0 to let teammates on the same "
                   "network reach this instance (see the printed warning).")
@click.option("--no-open", is_flag=True, help="Don't auto-open a browser tab")
def dashboard_command(port, host, no_open):
    """Local, read-only web UI over the current project's .specify/ status.

    Shows pipeline progress, task status, and token usage per feature.
    Nothing here writes to .specify/ — it's a viewer. Works without Jira/
    Confluence configured (unlike `sdd review status`).

    By default this only listens on 127.0.0.1 (your machine only). Run
    with --host 0.0.0.0 on a shared devbox to let teammates on the same
    network open it from their own browser at that machine's IP — there's
    still just one server process; it isn't a hosted/always-on service.
    """
    local_url = f"http://127.0.0.1:{port}/"
    server = ThreadingHTTPServer((host, port), _Handler)

    console.print()
    console.print(f"  [bold cyan]SDD Dashboard[/bold cyan]  [dim]running at {local_url}[/dim]")

    if host not in ("127.0.0.1", "localhost"):
        lan_ip = _lan_ip()
        if lan_ip:
            console.print(f"  [dim]Reachable on your network at:[/dim]  http://{lan_ip}:{port}/")
        console.print(
            "  [yellow]⚠  Bound to a non-local address — anyone who can reach this "
            "machine on the network can view this project's .specify/ status "
            "(read-only; no credentials pass through it).[/yellow]"
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
