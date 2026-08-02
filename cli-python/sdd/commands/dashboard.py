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
_ACCESS = {
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
  /* Auto (default): follows the OS/browser signal. */
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme]) {
      --bg: #0f1115; --fg: #e6e6e6; --muted: #9aa0a6; --card: #1a1d24;
      --border: #2a2d35; --accent: #60a5fa;
      --ok: #4ade80; --warn: #facc15; --bad: #f87171; --dim: #6b7280;
    }
  }
  /* Explicit Light/Dark picks from the toggle below always win over the
     OS signal above, since some browsers/embedded webviews never report
     prefers-color-scheme reliably -- this is the actual fix, not just a
     nicety. Persisted to localStorage by the script at the bottom. */
  :root[data-theme="light"] {
    color-scheme: light;
    --bg: #ffffff; --fg: #1a1a1a; --muted: #6b7280; --card: #f5f5f7;
    --border: #e2e2e6; --accent: #2563eb;
    --ok: #16a34a; --warn: #ca8a04; --bad: #dc2626; --dim: #9ca3af;
  }
  :root[data-theme="dark"] {
    color-scheme: dark;
    --bg: #0f1115; --fg: #e6e6e6; --muted: #9aa0a6; --card: #1a1d24;
    --border: #2a2d35; --accent: #60a5fa;
    --ok: #4ade80; --warn: #facc15; --bad: #f87171; --dim: #6b7280;
  }
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    margin: 0; padding: 2rem; background: var(--bg); color: var(--fg);
    font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }
  h1 { font-size: 1.3rem; margin: 0 0 .25rem; }
  h2 { font-size: 1rem; margin: 0 0 .75rem; color: var(--muted); font-weight: 600; }
  .sub { color: var(--muted); font-size: .85rem; margin-bottom: 1.5rem; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
  .feature-grid { grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
  .feature-grid .card-wide { grid-column: 1 / -1; }
  .card {
    background: var(--card); border: 1px solid var(--border); border-radius: 10px;
    padding: 1rem 1.2rem;
  }
  .kv { display: flex; justify-content: space-between; padding: .3rem 0; font-size: .9rem; }
  /* Child combinator, not descendant -- ".kv span:first-child" (space)
     also matched a badge/pill nested inside the value span whenever it
     was that span's only child (a badge IS ":first-child" of ITS own
     parent), silently overriding the badge's semantic color (green/red/
     amber) to plain gray. Hit the Constitution card's gate-1 badge and
     the Token Usage "Source mix" badges. */
  .kv > span:first-child { color: var(--muted); }
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
  .pill-ok   { color: var(--ok); border-color: var(--ok); }
  .links-cell { display: flex; flex-wrap: wrap; align-items: center; gap: .35rem; }
  .doc-detail-row td { padding: 0; border-bottom: 1px solid var(--border); }
  .doc-detail {
    margin: 0; font-size: .8rem; white-space: pre-wrap;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  .details-panel { background: var(--bg); }
  .tab-strip { display: flex; gap: .1rem; padding: .4rem 1rem 0; border-bottom: 1px solid var(--border); }
  .tab-btn {
    background: transparent; border: none; border-bottom: 2px solid transparent; color: var(--muted);
    font: inherit; font-size: .78rem; padding: .4rem .7rem; cursor: pointer; white-space: nowrap;
  }
  .tab-btn:hover { color: var(--fg); }
  .tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }
  .tab-body { padding: .75rem 1rem; max-height: 420px; overflow: auto; }
  .check-links-row { display: flex; align-items: center; gap: .6rem; margin: .5rem 0 1rem; }
  .comment { padding: .4rem 0; border-bottom: 1px dashed var(--border); font-size: .85rem; }
  .comment:last-of-type { border-bottom: none; }
  .comment-form { display: flex; flex-direction: column; gap: .4rem; margin-top: .6rem; max-width: 420px; }
  .comment-form input, .comment-form textarea {
    background: var(--card); border: 1px solid var(--border); border-radius: 6px;
    padding: .4rem .6rem; color: var(--fg); font: inherit; font-size: .85rem; resize: vertical;
  }
  .link-btn:disabled { opacity: .5; cursor: default; }
  .pipeline-caption { color: var(--muted); font-size: .8rem; margin: -.4rem 0 .75rem; }
  .pipeline-flow { display: flex; flex-wrap: wrap; align-items: center; gap: .25rem .1rem; margin-bottom: .9rem; }
  .pstep {
    display: inline-flex; align-items: center; gap: .3rem; padding: .25rem .6rem;
    border-radius: 999px; font-size: .78rem; border: 1px solid var(--border); white-space: nowrap;
  }
  .pstep-done    { color: var(--ok);   border-color: var(--ok); background: color-mix(in srgb, var(--ok) 10%, transparent); }
  .pstep-current { color: var(--accent); border-color: var(--accent); background: color-mix(in srgb, var(--accent) 14%, transparent); font-weight: 600; }
  .pstep-upcoming { color: var(--muted); }
  .pstep-skipped { color: var(--dim); text-decoration: line-through; border-style: dashed; }
  .pstep-optional { font-size: .68rem; color: var(--dim); font-weight: 400; }
  .pstep-persona {
    font-size: .68rem; font-weight: 700; opacity: .75; border-right: 1px solid currentColor;
    padding-right: .3rem; margin-right: -.05rem;
  }
  .pipeline-arrow { color: var(--dim); font-size: .8rem; }
  .pipeline-legend { color: var(--dim); font-size: .74rem; margin-bottom: .75rem; }
  .next-action-box {
    display: flex; flex-direction: column; gap: .35rem; padding: .6rem .8rem;
    border-radius: 8px; background: color-mix(in srgb, var(--accent) 10%, transparent);
    border: 1px solid var(--accent); font-size: .88rem;
  }
  .next-action-main { display: flex; gap: .5rem; align-items: baseline; }
  .next-action-main strong { color: var(--accent); white-space: nowrap; }
  .next-action-box code, .pstep code {
    background: var(--card); border-radius: 4px; padding: .05rem .35rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .85em;
  }
  .next-persona-ask { color: var(--fg); font-size: .85rem; }
  .next-persona-ask em { color: var(--accent); font-style: normal; font-weight: 600; }
  .next-persona-role { color: var(--dim); font-size: .8rem; }
  .doc-next-ask { color: var(--dim); }
  .doc-next-ask em { color: var(--fg); font-style: normal; font-weight: 600; }
  .doc-approval-line { font-size: .74rem; color: var(--muted); margin-top: .25rem; }
  .doc-approval-pending strong { color: var(--fg); }
  .doc-timing-line { font-size: .74rem; color: var(--muted); margin-top: .1rem; }
  .topbar { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; flex-wrap: wrap; }
  .theme-toggle {
    display: inline-flex; gap: .15rem; background: var(--card); border: 1px solid var(--border);
    border-radius: 999px; padding: .2rem; flex-shrink: 0;
  }
  .theme-toggle button {
    background: transparent; border: none; color: var(--muted); font: inherit; font-size: .78rem;
    padding: .3rem .65rem; border-radius: 999px; cursor: pointer; white-space: nowrap;
  }
  .theme-toggle button:hover { color: var(--fg); }
  .theme-toggle button.active { background: var(--accent); color: #fff; }
  .info-box {
    margin: .5rem 0 1.5rem; border: 1px solid var(--border); border-radius: 8px;
    background: var(--card); font-size: .82rem; color: var(--muted);
  }
  .info-box summary {
    cursor: pointer; padding: .5rem .8rem; font-weight: 600; color: var(--fg);
    list-style: none; display: flex; align-items: center; gap: .4rem;
  }
  .info-box summary::-webkit-details-marker { display: none; }
  .info-box summary::before { content: "▸"; color: var(--dim); transition: transform .15s; }
  .info-box[open] summary::before { transform: rotate(90deg); }
  .info-box .info-content { padding: 0 .8rem .8rem; line-height: 1.6; }
  .info-box code { background: var(--bg); border-radius: 4px; padding: .05rem .35rem; font-size: .9em; }
  .network-banner {
    margin: 0 0 1rem; padding: .6rem .9rem; border-radius: 8px; font-size: .85rem; font-weight: 600;
  }
  .network-banner-write {
    background: color-mix(in srgb, var(--bad) 12%, transparent); border: 1px solid var(--bad); color: var(--bad);
  }
  .network-banner-readonly {
    background: color-mix(in srgb, var(--muted) 14%, transparent); border: 1px solid var(--border); color: var(--muted);
  }
</style>
</head>
<body>
  <div class="topbar">
    <div>
      <h1>SDD Dashboard</h1>
      <div class="sub" id="generated-at">loading…</div>
    </div>
    <div class="theme-toggle" role="group" aria-label="Theme">
      <button type="button" data-theme-choice="light" title="Always use light theme">☀️ Light</button>
      <button type="button" data-theme-choice="dark" title="Always use dark theme">🌙 Dark</button>
      <button type="button" data-theme-choice="auto" title="Match your OS/browser setting">🖥️ Auto</button>
    </div>
  </div>
  <details class="info-box">
    <summary>ℹ️ Where this data comes from</summary>
    <div class="info-content">
      Everything below is a snapshot of local files under <code>.specify/</code> and <code>docs/jira/</code> — refreshed
      every 5s, no network calls. Task status reflects <code>tasks.md</code>, not live PR state.
      🕐 next to a document's status is its own <code>## Version History</code> table: created date (first row),
      days since/until approval, and revision-round count (version bumps after the first row). Needs
      <code>{date}</code> fields written as <code>YYYY-MM-DD</code> — older documents, or hand-edited dates in another
      format, just don't show it. The feature-level <strong>Timeline</strong> card rolls this up: start = earliest
      document's created date, end = <code>release.md</code>'s approval date.
      "Details" → Content reads the raw .md file from disk. Jira/Confluence pills next to a document come from a local cache written
      the last time you ran <code>sdd jira push</code> / <code>sdd confluence push</code> / <code>sdd review submit</code>/<code>apply</code> —
      they can go stale if the ticket changed since then. Click <strong>"Check Jira/Confluence status"</strong> to make a
      live call that refreshes both pills and adds the same APPROVED/NEEDS REVISION/PENDING classification as
      <code>sdd review check --doc</code>, plus reviewer comments (shown under 💬) — and, in the same call, the live Jira
      workflow status (e.g. "In Review", "Done") for both the review-gate tickets and the Jira Export card's Epic/Story/Task
      tickets. That's the only thing on this page that talks to Jira/Confluence — everything else is local-file-only — and
      once you've clicked it for a feature, it quietly re-checks every 5 minutes so it all stays fresh without you clicking again.
      <strong>Approve</strong> and comments update the local Status header (same as <code>sdd review approve --local</code>),
      mirror to Confluence if configured, and post a best-effort Jira comment.
      Running with <code>--share</code>? Approve/comment are read-only over the network unless the host machine also
      passed <code>--write</code>, in which case every write request must carry the one-time token baked into the
      link you were given — treat that link like a credential.
    </div>
  </details>
  <div id="root"></div>

<script>
// Theme: defaults to Auto (follows OS/browser prefers-color-scheme via the
// CSS media query). An explicit Light/Dark pick sets data-theme on <html>,
// which the CSS above gives higher specificity than the media query, and
// persists to localStorage so it survives reloads and doesn't depend on
// the OS signal reaching this page correctly.
const THEME_KEY = 'sdd-dashboard-theme';

function applyTheme(theme) {
  if (theme === 'light' || theme === 'dark') {
    document.documentElement.setAttribute('data-theme', theme);
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
  document.querySelectorAll('[data-theme-choice]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.themeChoice === theme);
  });
}

(function initTheme() {
  applyTheme(localStorage.getItem(THEME_KEY) || 'auto');
  document.querySelectorAll('[data-theme-choice]').forEach(btn => {
    btn.addEventListener('click', () => {
      const theme = btn.dataset.themeChoice;
      localStorage.setItem(THEME_KEY, theme);
      applyTheme(theme);
    });
  });
})();
</script>
<script>
// Client-side only — never re-fetched from /api/status, so it survives
// the 5s poll: which doc panels are expanded, their fetched content, and
// any live Jira/Confluence review-link results the user asked for.
// openDocs / docTab replace three separate expand-toggles (View, 👤
// Approvals, 💬 Comments) with one "Details" panel that has tabs -- see
// renderDocDetailsPanel(). docTab defaults to 'content' when a doc key
// has no entry yet.
const state = { openDocs: new Set(), docTab: {}, docContents: {}, reviewLinks: {}, commentDrafts: {} };
let lastData = null;
let dashboardInfo = { is_local: true, writes_enabled: true }; // overwritten by fetchDashboardInfo() below

// The server hands the write-access token to THIS browser via a one-time
// ?token= query param on the URL it auto-opens (see dashboard_command()) --
// read it once, keep it in memory for the life of this tab, then strip it
// from the visible URL/history so it doesn't linger somewhere it could be
// accidentally shared (a screenshot, a copied URL bar, browser history).
// Sent back on every write request as a custom header (X-SDD-Token), never
// a cookie -- a cookie would be attached automatically by the browser to
// any request to this origin, including one a malicious page tricked the
// user into triggering (classic CSRF); a header only goes out on requests
// this page's own JS explicitly builds, which a different origin's page
// cannot do (browsers don't let cross-origin JS read another origin's
// script state to forge it).
const _sddToken = new URLSearchParams(window.location.search).get('token');
if (_sddToken) {
  history.replaceState({}, '', window.location.pathname);
}

function writeHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (_sddToken) headers['X-SDD-Token'] = _sddToken;
  return headers;
}

async function fetchDashboardInfo() {
  try {
    const res = await fetch('/api/dashboard-info');
    dashboardInfo = await res.json();
  } catch (err) {
    // Leave the safe default (is_local: true, writes_enabled: true) --
    // worst case a local user briefly sees write controls that a retry
    // will confirm are actually fine, never the other way around.
  }
  render();
}

function renderNetworkBanner() {
  if (dashboardInfo.is_local) return '';
  return dashboardInfo.writes_enabled
    ? `<div class="network-banner network-banner-write">⚠ Shared over your network — write access is enabled. Anyone with this page's link can approve documents and post comments.</div>`
    : `<div class="network-banner network-banner-readonly">👁 Shared over your network — read-only. Approve/comment controls are hidden here; run with --write on the host machine to enable them.</div>`;
}

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
  } else if (kind === 'review') {
    const r = s.replace(/_/g, ' ');
    if (r === 'approved') cls = 'b-ok';
    else if (r === 'needs revision') cls = 'b-bad';
    else if (r === 'pending') cls = 'b-warn';
    return `<span class="badge ${cls}">${r}</span>`;
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
      <div class="kv"><span>Part 2 generated</span><span>${constitution.part2_generated ? 'yes' : 'no (still template placeholders)'}</span></div>
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

function outcomeBadge(outcome) {
  const map = {met: ['Met', 'b-ok'], not_met: ['Not Met', 'b-bad'], pending: ['Pending', 'b-warn']};
  if (!outcome || !map[outcome]) return '<span class="sub">—</span>';
  const [label, cls] = map[outcome];
  return `<span class="badge ${cls}">${label}</span>`;
}

function renderBusinessObjectives(bos, opts) {
  opts = opts || {};
  if (!bos || bos.length === 0) {
    return '<div class="empty">No BO-NNN rows in brd.md yet, or its Business Requirements section doesn’t cite a Serves BO column.</div>';
  }
  const rows = bos.map(bo => {
    const ucCell = (bo.uc_ids && bo.uc_ids.length) ? escapeHtml(bo.uc_ids.join(', ')) : '<span class="sub">none linked</span>';
    const progressCell = bo.task_count
      ? `${bo.percent_done}% <span class="sub">(${bo.tasks_done}/${bo.task_count})</span>`
      : '<span class="sub">no tasks linked</span>';
    const featureCell = opts.showFeature
      ? `<td><a href="#${featureAnchorId(bo.feature)}">${escapeHtml(bo.feature)}</a></td>`
      : '';
    const outcomeCell = `${outcomeBadge(bo.outcome)}${bo.measured_result ? `<div class="sub">${escapeHtml(bo.measured_result)}</div>` : ''}`;
    return `
      <tr>
        <td>${bo.bo_id}</td>
        <td>${escapeHtml(bo.objective)}${bo.metric ? `<div class="sub">${escapeHtml(bo.metric)}</div>` : ''}</td>
        ${featureCell}
        <td>${ucCell}</td>
        <td>${badge(bo.status, 'task')}</td>
        <td>${progressCell}</td>
        <td>${outcomeCell}</td>
      </tr>`;
  }).join('');
  const featureHeader = opts.showFeature ? '<th>Feature</th>' : '';
  return `
    <table><thead><tr><th>BO</th><th>Objective</th>${featureHeader}<th>Use Cases</th><th>Status</th><th>Progress</th><th>Business Outcome</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderBusinessObjectivesOverview(businessObjectives) {
  if (!businessObjectives || businessObjectives.length === 0) return '';
  return `
    <div class="card card-wide" style="margin-bottom:1.5rem">
      <h2>Business Objectives</h2>
      <div class="sub" style="margin-bottom:.5rem">Rolled up from each feature's brd.md (§2 Business Objectives → §5 Serves BO) through srd.md and tasks.md — which use cases implement each objective, and how much of that work is done.</div>
      ${renderBusinessObjectives(businessObjectives, {showFeature: true})}
    </div>`;
}

function linkPill(kind, link) {
  if (!link) return '';
  if (link.error) return `<span class="pill pill-bad" title="${escapeHtml(link.error)}">${kind} ⚠</span>`;
  const label = kind === 'Jira' ? `Jira ${link.key}` : 'Confluence';
  // link.status is the raw Jira workflow status (e.g. "In Review",
  // "Done") -- only present once the live check has run (reviewJira,
  // not the local-cache fallback), and distinct from review_status
  // (our own APPROVED/NEEDS REVISION/PENDING classification, shown as
  // its own badge) -- a ticket can be "Done" in the team's board while
  // still PENDING our classification, or vice versa.
  const statusSuffix = (kind === 'Jira' && link.status)
    ? ` <span class="sub">(${escapeHtml(link.status)})</span>` : '';
  return (link.url
    ? `<a class="pill pill-${kind === 'Jira' ? 'jira' : 'cf'}" href="${link.url}" target="_blank" rel="noopener">${label}</a>`
    : `<span class="pill pill-${kind === 'Jira' ? 'jira' : 'cf'}" title="No Atlassian base_url configured — run sdd config init">${label}</span>`
  ) + statusSuffix;
}

// "Who approved this, and how" needs one answer that works the same way
// regardless of review mode. d.local_approval only exists in local mode;
// reviewJira.review_status only exists once Jira has been checked. The
// document's own Approvals table (d.approvals, from status.py parsing
// its "## Approvals" section) is the one thing populated identically in
// every mode -- these helpers prefer the mode-specific record when it
// exists (it carries a note/mode label the table alone doesn't) and fall
// back to the table's Approver column otherwise.
//
// Both gate on the doc's live Status: header first -- the same
// authoritative-source check badge(d.status, 'doc') already uses (see
// CLAUDE.md "Document Review Gates": the Status: header is the
// authoritative gate in every mode). Without this, a document that was
// locally approved and later regenerated back to Draft would still show
// the old approver's checkmark pill -- .local-approvals.yml isn't
// cleared just because the doc content changed, so d.local_approval can
// outlive the approval it recorded.
const _APPROVAL_MODE_LABEL = { local: 'Local (dashboard/CLI)', jira: 'Jira', chat: 'Chat only — no audit file' };

function _statusSaysApproved(d) {
  return (d.status || '').toLowerCase().includes('approved');
}

function approvalMode(d, reviewJira) {
  if (!_statusSaysApproved(d)) return null;
  if (d.local_approval) return 'local';
  if (reviewJira && reviewJira.review_status === 'approved') return 'jira';
  return 'chat';
}

function approvedRowInfo(d) {
  if (!_statusSaysApproved(d)) return null;
  if (d.local_approval) {
    return { name: d.local_approval.approved_by || 'Approved', note: d.local_approval.note || '' };
  }
  const row = (d.approvals || []).find(r => (r.status || '').toLowerCase().includes('approved') && r.approver);
  return row ? { name: row.approver, note: '' } : null;
}

// Compact one-line answer to "who should approve this / who did", shown
// right under the Status badge with no click required — covers the
// common single-approver document without needing the 👤 detail panel.
function approvalSummaryLine(d) {
  const rows = d.approvals || [];
  if (!rows.length) return '';
  if (rows.length > 1) {
    const done = rows.filter(r => (r.status || '').toLowerCase().includes('approved')).length;
    return `<div class="doc-approval-line sub">${done}/${rows.length} sign-offs — see 👤 for detail</div>`;
  }
  const r = rows[0];
  if ((r.status || '').toLowerCase().includes('approved')) {
    return r.approver
      ? `<div class="doc-approval-line">👤 ${escapeHtml(r.approver)} <span class="sub">(${escapeHtml(r.role)})</span></div>`
      : '';
  }
  const who = r.approver || r.expected_approver;
  return `<div class="doc-approval-line doc-approval-pending">👤 Awaiting <strong>${escapeHtml(r.role)}</strong>${
    who ? ': ' + escapeHtml(who) : ' <span class="sub">(name not set in roles.yml)</span>'}</div>`;
}

// "How long has this document taken, and how many rounds did it go
// through" — derived server-side (status.py's _doc_timing) from the
// document's own '## Version History' table, so it works the same way
// regardless of review mode. Silent (renders nothing) whenever there's no
// created_date at all — an old document written before dates were
// standardized to ISO 8601, or one with no Version History table (e.g.
// release.md), rather than guessing or showing a broken "NaN days".
function timingSummaryLine(d) {
  const t = d.timing;
  if (!t || !t.created_date) return '';
  const parts = [];
  if (t.duration_days !== null && t.duration_days !== undefined) {
    parts.push(`${t.duration_days} day${t.duration_days === 1 ? '' : 's'}`);
  } else {
    parts.push(`created ${t.created_date}`);
  }
  if (t.revision_rounds) {
    parts.push(`${t.revision_rounds} revision${t.revision_rounds === 1 ? '' : 's'}`);
  }
  const title = [
    `Created ${t.created_date}`,
    t.approved_date ? `Approved ${t.approved_date}` : 'Not yet approved',
  ].join(' · ');
  return `<div class="doc-timing-line" title="${escapeHtml(title)}">🕐 ${escapeHtml(parts.join(' · '))}</div>`;
}

function renderApprovalsBody(d, mode) {
  const rows = d.approvals || [];
  const modeLine = mode
    ? `<div class="sub" style="margin-bottom:.4rem">Recorded via: <strong>${escapeHtml(_APPROVAL_MODE_LABEL[mode])}</strong></div>`
    : '<div class="sub" style="margin-bottom:.4rem">Not yet approved.</div>';
  const body = rows.length
    ? `<table><thead><tr><th>Role</th><th>Approver</th><th>Status</th><th>Date</th></tr></thead><tbody>${
        rows.map(r => {
          const who = r.approver
            ? escapeHtml(r.approver)
            : (r.expected_approver
                ? `<span class="sub">Expected: ${escapeHtml(r.expected_approver)}</span>`
                : '<span class="sub">— (not set in roles.yml)</span>');
          return `<tr><td>${escapeHtml(r.role)}</td><td>${who}</td><td>${badge(r.status, 'doc')}</td><td>${escapeHtml(r.date || '—')}</td></tr>`;
        }).join('')
      }</tbody></table>`
    : '<div class="sub">This document has no ## Approvals table yet.</div>';
  return `${modeLine}${body}`;
}

function renderCommentsBody(d, feature, reviewJira) {
  const comments = d.comments || [];
  const jiraComments = (reviewJira && reviewJira.comments) || [];
  const key = feature + '|' + d.key;
  const draft = state.commentDrafts[key] || { by: '', text: '' };
  const jiraList = jiraComments.length
    ? `<div class="sub" style="margin-bottom:.3rem">Jira review comments</div>` +
      jiraComments.map(c => `
        <div class="comment">
          <strong>${escapeHtml(c.author)}</strong> <span class="sub">${escapeHtml(c.created)}</span>
          <div>${escapeHtml(c.text)}</div>
        </div>`).join('')
    : '';
  const list = comments.length
    ? comments.map(c => `
        <div class="comment">
          <strong>${escapeHtml(c.by)}</strong> <span class="sub">${escapeHtml(c.at)}</span>
          <div>${escapeHtml(c.text)}</div>
        </div>`).join('')
    : '<div class="sub">No dashboard comments yet.</div>';
  const form = dashboardInfo.writes_enabled
    ? `<div class="comment-form">
      <input type="text" class="comment-by" data-feature="${feature}" data-doc="${d.key}"
             placeholder="Your name" maxlength="200" value="${escapeHtml(draft.by)}">
      <textarea class="comment-text" data-feature="${feature}" data-doc="${d.key}"
                placeholder="Add a review comment…" rows="2" maxlength="2000">${escapeHtml(draft.text)}</textarea>
      <button class="link-btn" data-action="submit-comment" data-feature="${feature}" data-doc="${d.key}">Post comment</button>
    </div>`
    : `<div class="sub">Read-only dashboard — commenting is disabled.</div>`;
  return `
    ${jiraList}
    ${list}
    ${form}`;
}

// One "Details" panel with tabs (Content / Approvals / Comments) instead
// of three independent expand-toggles -- keeps only one panel open per
// document instead of up to three stacking, and the Links cell down to
// [Approve] [Details] [Jira pill] [Confluence pill] [review badge].
function renderDocDetailsPanel(d, feature, mode, reviewJira) {
  const key = feature + '|' + d.key;
  const activeTab = state.docTab[key] || 'content';
  const commentCount = (d.comments || []).length;
  const approvalRows = d.approvals || [];
  const tabs = [
    { id: 'content', label: 'Content' },
    { id: 'approvals', label: 'Approvals' + (approvalRows.length ? ` (${approvalRows.length})` : '') },
    { id: 'comments', label: 'Comments' + (commentCount ? ` (${commentCount})` : '') },
  ];
  const tabStrip = `<div class="tab-strip">${tabs.map(t => `
    <button class="tab-btn${t.id === activeTab ? ' active' : ''}" data-action="switch-tab"
            data-tab="${t.id}" data-feature="${feature}" data-doc="${d.key}">${t.label}</button>`).join('')}</div>`;
  let body;
  if (activeTab === 'approvals') body = renderApprovalsBody(d, mode);
  else if (activeTab === 'comments') body = renderCommentsBody(d, feature, reviewJira);
  else body = `<pre class="doc-detail">${escapeHtml(state.docContents[key] ?? 'Loading…')}</pre>`;
  return `
    <tr class="doc-detail-row"><td colspan="3">
      <div class="details-panel">${tabStrip}<div class="tab-body">${body}</div></div>
    </td></tr>`;
}

function renderDocRow(d, feature, localConfluence, localJiraReview, reviewEntry) {
  const key = feature + '|' + d.key;
  const isOpen = state.openDocs.has(key);
  const localCf = (localConfluence || {})[d.key];
  const localJira = (localJiraReview || {})[d.key];
  const reviewJira = reviewEntry && reviewEntry.docs ? reviewEntry.docs[d.key]?.jira : null;
  const reviewCf   = reviewEntry && reviewEntry.docs ? reviewEntry.docs[d.key]?.confluence : null;
  const reviewStatusBadge = reviewJira && reviewJira.review_status ? badge(reviewJira.review_status, 'review') : '';
  const links = [
    linkPill('Jira', reviewJira || localJira),
    linkPill('Confluence', localCf || reviewCf),
  ].join('');
  const mode = approvalMode(d, reviewJira);
  const info = approvedRowInfo(d);
  const approveControl = info
    ? `<span class="pill pill-ok" title="${escapeHtml(info.note)}${mode ? ' · ' + _APPROVAL_MODE_LABEL[mode] : ''}">✓ ${escapeHtml(info.name)}</span>`
    : (dashboardInfo.writes_enabled
        ? `<button class="link-btn" data-action="approve-doc" data-feature="${feature}" data-doc="${d.key}">Approve</button>`
        : '');
  const commentCount = (d.comments || []).length;
  const detailsBtn = `<button class="link-btn" data-action="toggle-details" data-feature="${feature}" data-doc="${d.key}">${
    isOpen ? 'Hide' : 'Details'}${commentCount ? ' 💬' + commentCount : ''}</button>`;
  const row = `
    <tr>
      <td>${d.label}</td>
      <td>${badge(d.status, 'doc')}${approvalSummaryLine(d)}${timingSummaryLine(d)}</td>
      <td class="links-cell">
        ${approveControl}
        ${detailsBtn}${links}${reviewStatusBadge}
      </td>
    </tr>`;
  const detail = isOpen ? renderDocDetailsPanel(d, feature, mode, reviewJira) : '';
  return row + detail;
}

function renderDocs(docs, stage, feature, localConfluence, localJiraReview) {
  if (!docs || docs.length === 0) return '<div class="empty">No spec documents yet.</div>';
  const reviewEntry = state.reviewLinks[feature];
  const rows = docs.map(d => renderDocRow(d, feature, localConfluence, localJiraReview, typeof reviewEntry === 'object' ? reviewEntry : null)).join('');
  const p = stage.persona;
  const ask = p
    ? ` <span class="doc-next-ask">— or say: <em>"${escapeHtml(p.name)}, ${escapeHtml(p.ask)}"</em></span>`
    : '';
  const next = stage.next ? `<div class="sub">Next: ${escapeHtml(stage.next)}${ask}</div>` : '';
  return `<table><thead><tr><th>Document</th><th>Status</th><th>Links</th></tr></thead><tbody>${rows}</tbody></table>${next}`;
}

// exportEntry is state.reviewLinks[feature].export -- live ticket status
// for the Epic/Story/Task tickets, fetched by the same "Check Jira/
// Confluence status" click/auto-refresh as the review-gate tickets (see
// _fetch_export_ticket_statuses). null/undefined until that's run once.
function renderJiraExport(jira, exportEntry) {
  if (!jira || (!jira.epic && jira.stories.length === 0 && jira.tasks.length === 0)) {
    return '<div class="empty">No progressive Jira export yet (run /jira-push or sdd jira push).</div>';
  }
  const statuses = (exportEntry && exportEntry.statuses) || null;
  const itemLabel = x => {
    const label = x.url ? `<a href="${x.url}" target="_blank" rel="noopener">${x.key}</a>` : x.key;
    const status = statuses && statuses[x.key];
    return status ? `${label} <span class="sub">(${escapeHtml(status)})</span>` : label;
  };
  const list = arr => arr.length ? arr.map(itemLabel).join(', ') : '—';
  const errLine = exportEntry && exportEntry.error
    ? `<div class="sub" style="color:var(--bad)">${escapeHtml(exportEntry.error)}</div>` : '';
  return `
    ${errLine}
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
  else if (entry && entry.checked_at) status = `<span class="sub">Checked ${entry.checked_at} — auto-refreshes every 5 min</span>`;
  return `
    <div class="check-links-row">
      <button class="link-btn" data-action="check-review-links" data-feature="${feature}">🔄 Check Jira/Confluence status</button>
      ${status}
    </div>`;
}

function renderTokenUsage(tu) {
  if (!tu) return '<div class="empty">Token usage logging not enabled for this feature.</div>';
  const real = tu.real_commands || 0;
  const estimated = tu.estimated_commands || 0;
  const sourceMix = (real || estimated)
    ? `<div class="kv"><span>Source mix</span><span>
        <span class="badge b-ok" title="Real usage measured from Claude Code's own local session transcript via sdd token-log">Real ${real}</span>
        <span class="badge b-dim" title="Character-count approximation, used whenever Real usage isn't available">Est. ${estimated}</span>
      </span></div>`
    : '';
  return `
    <div class="kv"><span>Total Input Tokens</span><span>${tu.total_input ?? '—'}</span></div>
    <div class="kv"><span>Total Output Tokens</span><span>${tu.total_output ?? '—'}</span></div>
    <div class="kv"><span>Total Cost (USD)</span><span>${tu.total_cost ?? '—'}</span></div>
    <div class="kv"><span>Commands logged</span><span>${tu.commands_logged ?? '—'}</span></div>
    ${sourceMix}
    <div class="kv"><span>Last updated</span><span>${tu.last_updated ?? '—'}</span></div>
  `;
}

// Feature-level rollup of the same per-doc timing (status.py's
// _feature_timeline): start_date is the earliest doc's created_date
// (normally brd.md), end_date is release.md's approved_date. Either can be
// missing independently — a feature can have a known start with no end yet
// (release not approved), but never an end with no start.
function renderTimeline(t) {
  if (!t || (!t.start_date && !t.end_date)) {
    return '<div class="empty">Not enough dated documents yet to compute a timeline.</div>';
  }
  const duration = (t.duration_days !== null && t.duration_days !== undefined)
    ? `${t.duration_days} day${t.duration_days === 1 ? '' : 's'}`
    : '—';
  return `
    <div class="kv"><span>Start</span><span>${t.start_date || '—'}</span></div>
    <div class="kv"><span>End</span><span>${t.end_date || '— (release not yet approved)'}</span></div>
    <div class="kv"><span>Duration</span><span>${duration}</span></div>
  `;
}

// Converts `code` spans in an already-plain-text sentence (built server-side
// in status.py's _next_action_sentence) into <code> — escapeHtml runs first
// so this is safe against anything the sentence happens to contain.
function mdInlineCode(text) {
  return escapeHtml(text).replace(/`([^`]+)`/g, '<code>$1</code>');
}

const _PSTEP_CLASS = { done: 'pstep-done', current: 'pstep-current', upcoming: 'pstep-upcoming', skipped: 'pstep-skipped' };
const _PSTEP_ICON  = { done: '✓', current: '●', upcoming: '○', skipped: '—' };

function renderPipelineStep(s) {
  const cls = _PSTEP_CLASS[s.state] || 'pstep-upcoming';
  const icon = _PSTEP_ICON[s.state] || '○';
  const p = s.persona;
  const cmdLine = s.command ? `Command: ${s.command}` : 'Manual step — no command';
  const title = s.state === 'skipped'
    ? `Skipped — ${s.skip}`
    : (p ? `${p.name} — ${p.role}\n${cmdLine}\nOr say: "${p.name}, ${p.ask}"` : cmdLine);
  const optTag = s.optional ? ' <span class="pstep-optional">(optional)</span>' : '';
  const personaTag = (p && s.state !== 'skipped') ? `<span class="pstep-persona">${escapeHtml(p.name)}</span>` : '';
  return `<span class="pstep ${cls}" title="${escapeHtml(title)}">${icon} ${personaTag}${escapeHtml(s.label)}${optTag}</span>`;
}

function renderPipelineFlow(f, project) {
  const pipeline = f.pipeline;
  if (!pipeline || !pipeline.steps || !pipeline.steps.length) {
    return '<div class="empty">Pipeline data unavailable.</div>';
  }
  const meta = project
    ? `Scope: <strong>${escapeHtml(project.scope || '—')}</strong> · Plan mode: <strong>${escapeHtml(project.plan_mode || '—')}</strong>`
    : '';
  const flow = pipeline.steps.map(renderPipelineStep).join('<span class="pipeline-arrow">→</span>');
  const persona = pipeline.next_persona;
  const askLine = persona
    ? `<div class="next-persona-ask">💬 Or just say: <em>"${escapeHtml(persona.name)}, ${escapeHtml(persona.ask)}"</em>
        <span class="next-persona-role">(${escapeHtml(persona.name)} — ${escapeHtml(persona.role)})</span></div>`
    : '';
  return `
    ${meta ? `<div class="pipeline-caption">${meta}</div>` : ''}
    <div class="pipeline-flow">${flow}</div>
    <div class="pipeline-legend">✓ done · ● current — you are here · ○ upcoming · ┄ skipped for this scope/plan mode (hover a step for why)</div>
    <div class="next-action-box">
      <div class="next-action-main"><strong>Next:</strong> <span>${mdInlineCode(pipeline.next_action)}</span></div>
      ${askLine}
    </div>
  `;
}

function featureAnchorId(name) {
  return 'feature-' + encodeURIComponent(name);
}

function renderFeature(f, project) {
  const local = f.local_links || { jira: null, confluence: {}, jira_review: {} };
  const reviewEntry = state.reviewLinks[f.name];
  const exportEntry = (reviewEntry && typeof reviewEntry === 'object') ? reviewEntry.export : null;
  return `
  <div class="feature-block" id="${featureAnchorId(f.name)}">
    <div class="feature-title">${f.name}</div>
    ${renderReviewLinksControl(f.name)}
    <div class="grid feature-grid">
      <div class="card card-wide"><h2>Full Pipeline</h2>${renderPipelineFlow(f, project)}</div>
      <div class="card card-wide"><h2>Documents</h2>${renderDocs(f.docs, f.current_stage, f.name, local.confluence, local.jira_review)}</div>
      <div class="card card-wide"><h2>Business Objectives</h2>${renderBusinessObjectives(f.business_objectives)}</div>
      <div class="card"><h2>Timeline</h2>${renderTimeline(f.timeline)}</div>
      <div class="card"><h2>Tasks</h2>${renderTasks(f.tasks)}</div>
      <div class="card"><h2>Token Usage</h2>${renderTokenUsage(f.token_usage)}</div>
      <div class="card"><h2>Jira Export</h2>${renderJiraExport(local.jira, exportEntry)}</div>
    </div>
  </div>`;
}

// Only worth showing once there's more than one feature to scan through —
// for a single-feature project it would just duplicate the block below it.
function renderFeatureOverview(features) {
  if (!features || features.length < 2) return '';
  const rows = features.map(f => {
    const steps = (f.pipeline && f.pipeline.steps) || [];
    const current = steps.find(s => s.state === 'current');
    const stageLabel = current ? current.label : (steps.every(s => s.state === 'done' || s.state === 'skipped') ? 'Complete' : '—');
    const tasks = f.tasks || {};
    const pct = tasks.total ? Math.round(100 * tasks.done / tasks.total) : null;
    const tasksCell = pct !== null ? `${pct}% <span class="sub">(${tasks.done}/${tasks.total})</span>` : '<span class="sub">no tasks.md</span>';
    const nextAction = f.pipeline ? mdInlineCode(f.pipeline.next_action) : '—';
    return `
      <tr>
        <td><a href="#${featureAnchorId(f.name)}">${escapeHtml(f.name)}</a></td>
        <td>${escapeHtml(stageLabel)}</td>
        <td>${tasksCell}</td>
        <td>${nextAction}</td>
      </tr>`;
  }).join('');
  return `
    <div class="card card-wide" style="margin-bottom:1.5rem">
      <h2>Features Overview</h2>
      <table><thead><tr><th>Feature</th><th>Current Step</th><th>Tasks</th><th>Next Action</th></tr></thead><tbody>${rows}</tbody></table>
    </div>`;
}

function render() {
  if (!lastData) return;
  const data = lastData;
  document.getElementById('generated-at').textContent = 'Generated ' + data.generated_at;
  const overview = renderFeatureOverview(data.features);
  const boOverview = renderBusinessObjectivesOverview(data.business_objectives);
  const features = data.features.length
    ? data.features.map(f => renderFeature(f, data.project)).join('')
    : '<div class="empty">No features under .specify/features/ yet — run <code>/specify</code> (or <code>sdd specify</code>) to create your first one.</div>';

  // Rebuilding #root wholesale (below) would otherwise steal focus and reset
  // the caret out from under anyone actively typing in a comment field —
  // most visibly on the 5s auto-poll. Capture focus/selection first and
  // restore it on the freshly-built element with the same feature/doc data
  // attributes after the swap. The typed value itself is preserved
  // separately via state.commentDrafts (see the 'input' listener below),
  // since draft text must survive even *without* focus being restored.
  const root = document.getElementById('root');
  const active = document.activeElement;
  let focus = null;
  if (active && root.contains(active) &&
      (active.classList.contains('comment-by') || active.classList.contains('comment-text'))) {
    focus = {
      cls: active.classList.contains('comment-by') ? 'comment-by' : 'comment-text',
      feature: active.dataset.feature,
      doc: active.dataset.doc,
      start: active.selectionStart,
      end: active.selectionEnd,
    };
  }

  root.innerHTML = renderNetworkBanner() + renderProject(data.project, data.constitution) + overview + boOverview + features;

  if (focus) {
    const selector = `.${focus.cls}[data-feature="${CSS.escape(focus.feature)}"][data-doc="${CSS.escape(focus.doc)}"]`;
    const el = root.querySelector(selector);
    if (el) {
      el.focus();
      try { el.setSelectionRange(focus.start, focus.end); } catch (err) { /* not all inputs support this */ }
    }
  }
}

// Shared by 'toggle-details' (opening straight on the Content tab) and
// 'switch-tab' (switching to it later) -- fetches once per doc key and
// caches in state.docContents, matching the never-refetch behavior the
// old view-doc handler had.
async function ensureDocContentLoaded(feature, doc) {
  const key = feature + '|' + doc;
  if (key in state.docContents) return;
  state.docContents[key] = 'Loading…';
  render();
  try {
    const res = await fetch(`/api/doc?feature=${encodeURIComponent(feature)}&doc=${encodeURIComponent(doc)}`);
    const data = await res.json();
    state.docContents[key] = data.content ?? ('Error: ' + (data.error || 'unknown'));
  } catch (err) {
    state.docContents[key] = 'Error: ' + err;
  }
  render();
}

async function refresh() {
  // A failed poll (malformed file on disk, network hiccup) must not
  // silently freeze the UI on stale data with no indication anything is
  // wrong -- surface it, but keep the 5s setInterval polling regardless,
  // so the dashboard self-heals the moment the underlying issue is fixed.
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    lastData = data;
    render();
  } catch (err) {
    const root = document.getElementById('root');
    if (root) {
      root.innerHTML = `<div class="empty" style="color:var(--bad)">
        Couldn't load status: ${escapeHtml(String(err.message || err))}
        <br><span class="sub">Retrying in 5s…</span></div>`;
    }
  }
}

// Delegated 'input' listener: fires on every keystroke in a comment field
// and stashes the value in state.commentDrafts, keyed by feature+doc — so
// when the 5s poll rebuilds #root (see render()'s innerHTML swap above),
// the new input/textarea nodes are re-hydrated from state instead of
// coming back empty. This is what actually stops typed text from being
// lost; the focus/caret restore in render() just makes it feel seamless.
document.getElementById('root').addEventListener('input', (e) => {
  const el = e.target;
  const isBy = el.classList.contains('comment-by');
  const isText = el.classList.contains('comment-text');
  if (!isBy && !isText) return;
  const key = el.dataset.feature + '|' + el.dataset.doc;
  const draft = state.commentDrafts[key] || { by: '', text: '' };
  if (isBy) draft.by = el.value; else draft.text = el.value;
  state.commentDrafts[key] = draft;
});

// Event delegation on #root: click handlers survive innerHTML replacement
// on every refresh(), since the listener lives on the stable parent node.
document.getElementById('root').addEventListener('click', async (e) => {
  const btn = e.target.closest('[data-action]');
  if (!btn) return;
  const feature = btn.dataset.feature;

  if (btn.dataset.action === 'toggle-details') {
    const doc = btn.dataset.doc;
    const key = feature + '|' + doc;
    if (state.openDocs.has(key)) {
      state.openDocs.delete(key);
      render();
      return;
    }
    state.openDocs.add(key);
    render();
    if ((state.docTab[key] || 'content') === 'content') await ensureDocContentLoaded(feature, doc);

  } else if (btn.dataset.action === 'switch-tab') {
    const doc = btn.dataset.doc;
    const key = feature + '|' + doc;
    state.docTab[key] = btn.dataset.tab;
    render();
    if (btn.dataset.tab === 'content') await ensureDocContentLoaded(feature, doc);

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

  } else if (btn.dataset.action === 'approve-doc') {
    const doc = btn.dataset.doc;
    const by = window.prompt('Approve as (your name):');
    if (!by) return;
    const note = window.prompt('Optional note:') || '';
    btn.disabled = true;
    try {
      const res = await fetch('/api/approve', {
        method: 'POST',
        headers: writeHeaders(),
        body: JSON.stringify({ feature, doc, by, note }),
      });
      const result = await res.json();
      if (result.error) window.alert('Approve failed: ' + result.error);
      await refresh();
    } catch (err) {
      window.alert('Approve failed: ' + err);
      render();
    }

  } else if (btn.dataset.action === 'submit-comment') {
    const doc = btn.dataset.doc;
    const box = btn.closest('.tab-body');
    const by = box.querySelector('.comment-by').value.trim();
    const text = box.querySelector('.comment-text').value.trim();
    if (!text) return;
    btn.disabled = true;
    try {
      const res = await fetch('/api/comment', {
        method: 'POST',
        headers: writeHeaders(),
        body: JSON.stringify({ feature, doc, by, text }),
      });
      const result = await res.json();
      if (result.error) {
        window.alert('Comment failed: ' + result.error);
      } else {
        delete state.commentDrafts[feature + '|' + doc];
      }
      state.openDocs.add(feature + '|' + doc);
      state.docTab[feature + '|' + doc] = 'comments';
      await refresh();
    } catch (err) {
      window.alert('Comment failed: ' + err);
      render();
    }
  }
});

// Opt-in only: this never fires for a feature the user hasn't manually
// checked at least once via the "Check Jira/Confluence status"
// button -- the dashboard's one live-network-call path stays something
// the user explicitly triggered, it just doesn't require re-clicking
// every 5 minutes to stay fresh after that. Silently keeps the last good
// result on a transient failure rather than flashing an error over data
// that was fine a moment ago.
const REVIEW_LINKS_AUTO_REFRESH_MS = 5 * 60 * 1000;

async function autoRefreshReviewLinks() {
  const features = Object.keys(state.reviewLinks).filter(feature => {
    const entry = state.reviewLinks[feature];
    return entry && typeof entry === 'object' && !entry.error;
  });
  if (!features.length) return;
  let changed = false;
  for (const feature of features) {
    try {
      const res = await fetch(`/api/review-links?feature=${encodeURIComponent(feature)}`);
      state.reviewLinks[feature] = await res.json();
      changed = true;
    } catch (err) {
      // Leave the last known-good result in place — see comment above.
    }
  }
  if (changed) render();
}

fetchDashboardInfo();
refresh();
setInterval(refresh, 5000);
setInterval(autoRefreshReviewLinks, REVIEW_LINKS_AUTO_REFRESH_MS);
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

    def _check_write_access(self) -> str | None:
        """Returns an error message if this write request should be
        rejected, or None if it's allowed. Three gates, in order:

        1. Read-only mode: non-loopback binds without --write reject every
           POST outright, regardless of token -- writes are simply off.
        2. Origin/Host check (defense in depth, non-loopback only): if the
           browser sent an Origin header, it must match this server's own
           host:port. A cross-origin page (malicious or just a stray open
           tab) can't forge this the way it could once ambient cookies --
           this runs before the token check so a mismatched Origin is
           rejected even if a token somehow leaked.
        3. Token check (non-loopback only): the Origin check alone doesn't
           stop another device on the same network from calling the API
           directly (curl, not a browser) -- the token is what actually
           authenticates the request. Sent as a custom header
           (X-SDD-Token), never a cookie, precisely so it's never included
           automatically by the browser on a request this page didn't
           initiate itself -- that property is what makes it double as
           CSRF protection, not just as auth.

        Loopback binds (the default `sdd dashboard`, no flags) skip all
        three checks -- this function returns None immediately for them,
        so today's zero-friction local UX is completely unaffected.
        """
        if _ACCESS["is_local"]:
            return None
        if not _ACCESS["writes_enabled"]:
            return (
                "Dashboard is read-only over the network. Restart with "
                "--share --write to enable writes (requires the printed token)."
            )
        origin = self.headers.get("Origin")
        if origin and origin not in _ACCESS["allowed_origins"]:
            return f"Origin not allowed: {origin}"
        token = self.headers.get("X-SDD-Token")
        if not token or not secrets.compare_digest(token, _ACCESS["token"] or ""):
            return "Missing or invalid X-SDD-Token header."
        return None

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
    effective_host = "0.0.0.0" if share else host
    is_local = effective_host in ("127.0.0.1", "localhost")
    writes_enabled = is_local or write
    token = secrets.token_urlsafe(24) if (not is_local and writes_enabled) else None

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
                "Add --write to enable that (generates a token).[/dim]"
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
