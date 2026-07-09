"""sdd dashboard — local, read-only web UI over the status.py snapshot.

Stdlib-only HTTP server (no new dependency) serving a single static page
that polls /api/status. Nothing here writes to .specify/ — it's a viewer.
"""
from __future__ import annotations
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import click
from rich.console import Console

from sdd.utils.status import build_project_status

console = Console()

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
  .feature-title { font-size: 1.05rem; font-weight: 600; margin-bottom: .75rem; }
  .bar { display: flex; height: 8px; border-radius: 4px; overflow: hidden; background: var(--border); margin: .5rem 0 .75rem; }
  .bar span { display: block; }
  .empty { color: var(--muted); font-style: italic; padding: 1rem 0; }
  .refresh-note { color: var(--dim); font-size: .78rem; margin-top: 2rem; }
</style>
</head>
<body>
  <h1>SDD Dashboard</h1>
  <div class="sub" id="generated-at">loading…</div>
  <div id="root"></div>
  <div class="refresh-note">Read-only snapshot of <code>.specify/</code> — refreshes every 5s. Task/PR status reflects tasks.md, not live PR state.</div>

<script>
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

function renderDocs(docs, stage) {
  if (!docs || docs.length === 0) return '<div class="empty">No spec documents yet.</div>';
  const rows = docs.map(d => `
    <tr><td>${d.label}</td><td>${badge(d.status, 'doc')}</td></tr>
  `).join('');
  const next = stage.next ? `<div class="sub">Next: ${stage.next}</div>` : '';
  return `<table><thead><tr><th>Document</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table>${next}`;
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
  return `
  <div class="feature-block">
    <div class="feature-title">${f.name}</div>
    <div class="grid">
      <div class="card"><h2>Pipeline</h2>${renderDocs(f.docs, f.current_stage)}</div>
      <div class="card"><h2>Tasks</h2>${renderTasks(f.tasks)}</div>
      <div class="card"><h2>Token Usage</h2>${renderTokenUsage(f.token_usage)}</div>
    </div>
  </div>`;
}

async function refresh() {
  const res = await fetch('/api/status');
  const data = await res.json();
  document.getElementById('generated-at').textContent = 'Generated ' + data.generated_at;
  const features = data.features.length
    ? data.features.map(renderFeature).join('')
    : '<div class="empty">No features under .specify/features/ yet.</div>';
  document.getElementById('root').innerHTML = renderProject(data.project, data.constitution) + features;
}

refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # noqa: A003 - silence default access logging
        pass

    def do_GET(self):  # noqa: N802 - http.server API
        if self.path in ("/", "/index.html"):
            body = _PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/status":
            data = build_project_status(".")
            body = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


@click.command()
@click.option("--port", default=4747, show_default=True, help="Local port to serve on")
@click.option("--no-open", is_flag=True, help="Don't auto-open a browser tab")
def dashboard_command(port, no_open):
    """Local, read-only web UI over the current project's .specify/ status.

    Shows pipeline progress, task status, and token usage per feature.
    Nothing here writes to .specify/ — it's a viewer. Works without Jira/
    Confluence configured (unlike `sdd review status`).
    """
    url = f"http://127.0.0.1:{port}/"
    server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)

    console.print()
    console.print(f"  [bold cyan]SDD Dashboard[/bold cyan]  [dim]running at {url}[/dim]")
    console.print("  [dim]Ctrl+C to stop[/dim]")
    console.print()

    if not no_open:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        console.print("\n  Stopped.")
    finally:
        server.server_close()
