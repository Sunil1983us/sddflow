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
    : (p ? `${p.name} — ${p.role}
${cmdLine}
Or say: "${p.name}, ${p.ask}"` : cmdLine);
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
    const confirmMsg =
      `Approve ${doc} for ${feature} as "${by}"?` +
      (note ? `\nNote: ${note}` : '') +
      '\n\nThis flips the document\'s Status header to Approved and syncs ' +
      'to Confluence/Jira if configured -- not easily undone from here.';
    if (!window.confirm(confirmMsg)) return;
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