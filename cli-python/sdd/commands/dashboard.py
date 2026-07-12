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
import socket
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
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
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
  .feature-grid { grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
  .feature-grid .card-wide { grid-column: 1 / -1; }
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
  .pill-ok   { color: var(--ok); border-color: var(--ok); }
  .links-cell { display: flex; flex-wrap: wrap; align-items: center; gap: .35rem; }
  .doc-detail-row td { padding: 0; border-bottom: 1px solid var(--border); }
  .doc-detail {
    margin: 0; padding: .75rem 1rem; background: var(--bg); max-height: 360px; overflow: auto;
    font-size: .8rem; white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  .check-links-row { display: flex; align-items: center; gap: .6rem; margin: .5rem 0 1rem; }
  .comments-box { padding: .75rem 1rem; background: var(--bg); }
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
  .pipeline-arrow { color: var(--dim); font-size: .8rem; }
  .pipeline-legend { color: var(--dim); font-size: .74rem; margin-bottom: .75rem; }
  .next-action-box {
    display: flex; gap: .5rem; align-items: baseline; padding: .6rem .8rem;
    border-radius: 8px; background: color-mix(in srgb, var(--accent) 10%, transparent);
    border: 1px solid var(--accent); font-size: .88rem;
  }
  .next-action-box strong { color: var(--accent); white-space: nowrap; }
  .next-action-box code, .pstep code {
    background: var(--card); border-radius: 4px; padding: .05rem .35rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .85em;
  }
</style>
</head>
<body>
  <h1>SDD Dashboard</h1>
  <div class="sub" id="generated-at">loading…</div>
  <div id="root"></div>
  <div class="refresh-note">Snapshot of <code>.specify/</code> — refreshes every 5s. Task/PR status reflects tasks.md, not live PR state.
    "View" reads the raw .md file from disk. Jira/Confluence pills next to a document are from local cache (progressive export /
    <code>sdd confluence push</code>) — "Check Jira/Confluence review links" additionally queries live for <code>sdd review submit</code> tickets.
    "Approve" and comments update the local Status header (same as <code>sdd review approve --local</code>), mirror to Confluence if configured,
    and post a best-effort Jira comment.</div>

<script>
// Client-side only — never re-fetched from /api/status, so it survives
// the 5s poll: which doc panels are expanded, their fetched content, and
// any live Jira/Confluence review-link results the user asked for.
const state = { expandedDocs: new Set(), expandedComments: new Set(), docContents: {}, reviewLinks: {}, commentDrafts: {} };
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

function renderCommentsPanel(d, feature) {
  const comments = d.comments || [];
  const key = feature + '|' + d.key;
  const draft = state.commentDrafts[key] || { by: '', text: '' };
  const list = comments.length
    ? comments.map(c => `
        <div class="comment">
          <strong>${escapeHtml(c.by)}</strong> <span class="sub">${escapeHtml(c.at)}</span>
          <div>${escapeHtml(c.text)}</div>
        </div>`).join('')
    : '<div class="sub">No comments yet.</div>';
  return `
    <tr class="doc-detail-row"><td colspan="3">
      <div class="comments-box">
        ${list}
        <div class="comment-form">
          <input type="text" class="comment-by" data-feature="${feature}" data-doc="${d.key}"
                 placeholder="Your name" maxlength="200" value="${escapeHtml(draft.by)}">
          <textarea class="comment-text" data-feature="${feature}" data-doc="${d.key}"
                    placeholder="Add a review comment…" rows="2" maxlength="2000">${escapeHtml(draft.text)}</textarea>
          <button class="link-btn" data-action="submit-comment" data-feature="${feature}" data-doc="${d.key}">Post comment</button>
        </div>
      </div>
    </td></tr>`;
}

function renderDocRow(d, feature, localConfluence, reviewEntry) {
  const key = feature + '|' + d.key;
  const expanded = state.expandedDocs.has(key);
  const commentsOpen = state.expandedComments.has(key);
  const localCf = (localConfluence || {})[d.key];
  const reviewJira = reviewEntry && reviewEntry.docs ? reviewEntry.docs[d.key]?.jira : null;
  const reviewCf   = reviewEntry && reviewEntry.docs ? reviewEntry.docs[d.key]?.confluence : null;
  const links = [
    linkPill('Jira', reviewJira),
    linkPill('Confluence', localCf || reviewCf),
  ].join('');
  const approveControl = d.local_approval
    ? `<span class="pill pill-ok" title="${escapeHtml(d.local_approval.note || '')}">✓ ${escapeHtml(d.local_approval.approved_by || 'Approved')}</span>`
    : `<button class="link-btn" data-action="approve-doc" data-feature="${feature}" data-doc="${d.key}">Approve</button>`;
  const commentCount = (d.comments || []).length;
  const commentBtn = `<button class="link-btn" data-action="toggle-comments" data-feature="${feature}" data-doc="${d.key}">💬${commentCount ? ' ' + commentCount : ''}</button>`;
  const row = `
    <tr>
      <td>${d.label}</td>
      <td>${badge(d.status, 'doc')}</td>
      <td class="links-cell">
        <button class="link-btn" data-action="view-doc" data-feature="${feature}" data-doc="${d.key}">${expanded ? 'Hide' : 'View'}</button>
        ${approveControl}
        ${commentBtn}${links}
      </td>
    </tr>`;
  const detail = expanded
    ? `<tr class="doc-detail-row"><td colspan="3"><pre class="doc-detail">${escapeHtml(state.docContents[key] ?? 'Loading…')}</pre></td></tr>`
    : '';
  const commentsPanel = commentsOpen ? renderCommentsPanel(d, feature) : '';
  return row + detail + commentsPanel;
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
  const title = s.state === 'skipped'
    ? `Skipped — ${s.skip}`
    : (s.command ? `Command: ${s.command}` : 'Manual step — no command');
  const optTag = s.optional ? ' <span class="pstep-optional">(optional)</span>' : '';
  return `<span class="pstep ${cls}" title="${escapeHtml(title)}">${icon} ${escapeHtml(s.label)}${optTag}</span>`;
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
  return `
    ${meta ? `<div class="pipeline-caption">${meta}</div>` : ''}
    <div class="pipeline-flow">${flow}</div>
    <div class="pipeline-legend">✓ done · ● current — you are here · ○ upcoming · ┄ skipped for this scope/plan mode (hover a step for why)</div>
    <div class="next-action-box"><strong>Next:</strong> <span>${mdInlineCode(pipeline.next_action)}</span></div>
  `;
}

function renderFeature(f, project) {
  const local = f.local_links || { jira: null, confluence: {} };
  return `
  <div class="feature-block">
    <div class="feature-title">${f.name}</div>
    ${renderReviewLinksControl(f.name)}
    <div class="grid feature-grid">
      <div class="card card-wide"><h2>Full Pipeline</h2>${renderPipelineFlow(f, project)}</div>
      <div class="card card-wide"><h2>Documents</h2>${renderDocs(f.docs, f.current_stage, f.name, local.confluence)}</div>
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
    ? data.features.map(f => renderFeature(f, data.project)).join('')
    : '<div class="empty">No features under .specify/features/ yet.</div>';

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

  root.innerHTML = renderProject(data.project, data.constitution) + features;

  if (focus) {
    const selector = `.${focus.cls}[data-feature="${CSS.escape(focus.feature)}"][data-doc="${CSS.escape(focus.doc)}"]`;
    const el = root.querySelector(selector);
    if (el) {
      el.focus();
      try { el.setSelectionRange(focus.start, focus.end); } catch (err) { /* not all inputs support this */ }
    }
  }
}

async function refresh() {
  const res = await fetch('/api/status');
  lastData = await res.json();
  render();
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

  } else if (btn.dataset.action === 'toggle-comments') {
    const key = feature + '|' + btn.dataset.doc;
    if (state.expandedComments.has(key)) state.expandedComments.delete(key);
    else state.expandedComments.add(key);
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
        headers: { 'Content-Type': 'application/json' },
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
    const box = btn.closest('.comments-box');
    const by = box.querySelector('.comment-by').value.trim();
    const text = box.querySelector('.comment-text').value.trim();
    if (!text) return;
    btn.disabled = true;
    try {
      const res = await fetch('/api/comment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feature, doc, by, text }),
      });
      const result = await res.json();
      if (result.error) {
        window.alert('Comment failed: ' + result.error);
      } else {
        delete state.commentDrafts[feature + '|' + doc];
      }
      state.expandedComments.add(feature + '|' + doc);
      await refresh();
    } catch (err) {
      window.alert('Comment failed: ' + err);
      render();
    }
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
    never invoked by /api/status. Jira lookup is feature-qualified to match
    the label `sdd review submit` writes; Confluence page titles only
    support {project} today, matching `sdd review status`'s own behavior,
    so the Confluence half is still shared across features on one project.
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
                issue = jira_client.find_by_label(cfg.jira.project_key, f"sdd-doc:{feature}:{doc_key}")
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


_COMMENTS_FILE = Path(".specify") / ".dashboard-comments.json"
_MAX_TEXT_LEN = 2000  # by/note/comment fields — generous but bounded


def _clip_text(value, max_len=_MAX_TEXT_LEN) -> str:
    text = str(value or "").strip()
    return text[:max_len]


def _jira_client_for_comments():
    """Build (client, cfg) for posting a Jira comment, or None if Jira isn't
    configured. Never raises — callers treat None as 'skip, not an error'."""
    from sdd.utils.integrations import load_integrations
    from sdd.utils.atlassian_auth import load_profile, build_session
    from sdd.utils.jira_client import JiraClient
    try:
        cfg = load_integrations()
    except FileNotFoundError:
        return None
    if not cfg.jira:
        return None
    try:
        prof = load_profile(cfg.profile)
        session = build_session(prof)
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
        issue = client.find_by_label(cfg.jira.project_key, f"sdd-doc:{feature}:{doc}")
        if not issue:
            return {"posted": False, "reason": "no review ticket found for this document"}
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
        _save_local_approval, _mark_md_approved, _push_doc_page, _doc_md_path,
    )

    by = _clip_text(by) or "dashboard user"
    note = _clip_text(note) or "approved via dashboard"

    _save_local_approval(doc, by, note)
    result: dict = {"local_approval": True, "md_updated": False, "confluence": None, "jira_comment": None}

    md_path = _doc_md_path(doc, feature)
    if md_path and md_path.exists():
        result["md_updated"] = _mark_md_approved(md_path)
        try:
            title = _push_doc_page(doc, md_path)
            result["confluence"] = {"updated": bool(title), "title": title}
        except Exception as e:
            result["confluence"] = {"error": str(e)}
    else:
        result["error"] = f"{doc}.md not found for feature {feature}"

    result["jira_comment"] = _post_jira_comment(feature, doc, f"Approved via SDD Dashboard by {by}.")
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
    entry = {"by": by, "text": text, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    comments.setdefault(key, []).append(entry)
    _COMMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _COMMENTS_FILE.write_text(json.dumps(comments, indent=2))

    jira_comment = _post_jira_comment(feature, doc, f"{by} (via SDD Dashboard): {text}")
    return {"saved": True, "comment": entry, "jira_comment": jira_comment}


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

    def do_POST(self):  # noqa: N802 - http.server API
        parsed = urlparse(self.path)
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
                result = _do_approve(feature, doc, payload.get("by", ""), payload.get("note", ""))
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)

        elif parsed.path == "/api/comment":
            try:
                result = _do_comment(feature, doc, payload.get("by", ""), payload.get("text", ""))
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
@click.option("--host", default="127.0.0.1", show_default=True,
              help="Bind address. Use 0.0.0.0 to let teammates on the same "
                   "network reach this instance (see the printed warning).")
@click.option("--no-open", is_flag=True, help="Don't auto-open a browser tab")
def dashboard_command(port, host, no_open):
    """Local web UI over the current project's .specify/ status.

    Shows pipeline progress, task status, and token usage per feature.
    Mostly a viewer — it also lets you Approve a document or leave a
    review comment, which updates the local .md Status header (same as
    `sdd review approve --local`), mirrors to Confluence if configured,
    and posts a best-effort Jira comment. Works without Jira/Confluence
    configured at all (unlike `sdd review status`).

    By default this only listens on 127.0.0.1 (your machine only). Run
    with --host 0.0.0.0 on a shared devbox to let teammates on the same
    network open it from their own browser at that machine's IP — there's
    still just one server process; it isn't a hosted/always-on service.
    Anyone who can reach it can also approve documents and post comments
    (see the printed warning) — only do this on a network you trust.
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
            "machine on the network can view this project's .specify/ status, "
            "AND approve documents / post review comments on your behalf "
            "(no credentials pass through it, but the actions themselves are "
            "unauthenticated). Only use this on a network you trust.[/yellow]"
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
