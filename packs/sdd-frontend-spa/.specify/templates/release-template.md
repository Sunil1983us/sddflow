# Release Plan
# Feature: {Feature Name}
> Version: 1.0 | Date: {date}
> Run after: /implement — all tasks "PR ready" and merged
> Gate before: production go-live

---

## References
| Source | Sections / IDs Used |
|---|---|
| tasks.md | {sections/IDs referenced} |
| qa-testcases.summary.md | {sections/IDs referenced} |
| runbook.md | {sections/IDs referenced} |

## 1. Pre-Release Checklist

- [ ] All tasks in tasks.md complete and merged
- [ ] All PRs referenced TASK-NNN/CHG-NNN (constitution Git rule)
- [ ] Test suite green (unit + component + E2E)
- [ ] Coverage ≥ gate (constitution Part 2)
- [ ] Security checklist passed (security-design.md section 1, +2 if mvp+)
- [ ] stories.md Traceability Matrix — every FR-NNN has ≥ 1 TC-NNN and is passing

---

## 2. UAT Plan

| UC-NNN (from use-cases.md) | Scenario | Tester | Browser/Device Target | Environment | Result |
|---|---|---|---|---|---|
| UC-001 | {happy path} | {role} | {e.g. Chrome desktop / iOS Safari} | {staging} | [ ] Pass [ ] Fail |
| UC-002 | {unhappy path} | {role} | {e.g. Firefox desktop / Android Chrome} | {staging} | [ ] Pass [ ] Fail |

**UAT Sign-off:** [ ] Product Owner   [ ] QA Lead

---

## 3. Static Deploy Plan

| Step | Action | Owner | Rollback If Fails |
|---|---|---|---|
| 1 | Build static assets (`{build command}`) | {role} | Discard artifact, fix, rebuild |
| 2 | Deploy to CDN/object storage (constitution OPS-7) | {role} | Redeploy previous build artifact |
| 3 | Invalidate/purge CDN cache for `index.html` (hashed assets unaffected — immutable) | {role} | Re-purge with previous `index.html` |
| 4 | Smoke test (section 4) | {role} | Roll back step 2-3 |
| 5 | Enable feature flag / staged rollout (if applicable) | {role} | Disable flag / revert rollout |

**Environment promotion order:** {dev → staging → prod, or as applicable}

---

## 4. Post-Deploy Smoke Test

| Check | Expected | Result |
|---|---|---|
| `GET /` (production URL) | 200, latest bundle hash in `index.html` | [ ] |
| {key happy-path screen flow} | {expected behaviour} | [ ] |
| Browser console / network tab | No new errors, no failed asset requests (404/CORS) | [ ] |
| Error-tracking dashboard (Sentry/RUM) | No new error spike within {N} min of deploy | [ ] |
| {key NFR — e.g. LCP/CLS/INP budget} | within target (NFR-{NNN}) | [ ] |

---

## 5. Go-Live Gate

| Role | Decision | Date |
|---|---|---|
| Tech Lead | [ ] Go  [ ] No-Go | |
| Product Owner | [ ] Go  [ ] No-Go | |
| QA Lead | [ ] Go  [ ] No-Go | |
| Ops/SRE | [ ] Go  [ ] No-Go | |

---

## 6. Business Objective Closure

| BO-NNN | Success Metric (from BRD) | Measured Result | Met? |
|---|---|---|---|
| BO-001 | {metric} | {result, or "measure after N days"} | [ ] Yes [ ] Pending |

---

## 7. Rollback Plan

{Summary — full detail in runbook.md §6: CDN cache invalidation
rollback, redeploy previous static build, feature-flag revert}

---

## Approvals
| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
