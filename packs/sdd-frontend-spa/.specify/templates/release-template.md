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
| docs/runbook/local-setup.md | {sections/IDs referenced} |

## 1. Pre-Release Checklist

- [ ] All tasks in tasks.md complete and merged
- [ ] All PRs referenced TASK-NNN/CHG-NNN (constitution Git rule)
- [ ] Test suite green (unit + component + E2E)
- [ ] Coverage ≥ gate (constitution Part 2)
- [ ] Security checklist passed — see `security-design.md §1` signed by {security_officer} on {date} (evidence required, not self-attestation)
- [ ] stories.md Traceability Matrix — every FR-NNN has ≥ 1 TC-NNN and is passing

---

## 2. UAT Plan

| UC-NNN (from use-cases.md) | Scenario | Tester | Browser/Device Target | Environment | Environment Prerequisites | Result |
|---|---|---|---|---|---|---|
| UC-{NNN} | {happy path} | {role} | {e.g. Chrome desktop / iOS Safari} | {staging} | {e.g. feature flag X enabled, mock API set to success mode} | [ ] Pass [ ] Fail |
| UC-{NNN} | {unhappy path} | {role} | {e.g. Firefox desktop / Android Chrome} | {staging} | {e.g. mock API set to error mode} | [ ] Pass [ ] Fail |

**UAT Sign-off:** [ ] Product Owner   [ ] QA Lead

---

## 3. Static Deploy Plan

### Strategy Selection

Choose deployment strategy based on NFR requirements:

| Condition | Strategy | Rationale |
|---|---|---|
| Zero-downtime required + instant rollback | Blue-Green (dual CDN origins) | Swap CDN origin between two identical deployments; rollback = swap back |
| Gradual rollout with traffic split | Canary (CDN routing rules) | Route {N}% traffic to new build, monitor errors, shift to 100% |
| Standard release, CDN invalidation acceptable | Rolling (single CDN deploy) | Default — replace assets, invalidate cache, monitor post-deploy |

**Selected strategy for this release:** {rolling | blue-green | canary} — Reason: {NFR-NNN or explicit decision}

### Steps

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

**Preconditions — every box checked before any Go decision is recorded:**

- [ ] All TASK-NNN merged ("PR ready" / "Task accepted" + merged)
- [ ] UAT scenarios (§2) passed and signed off
- [ ] Rollback plan (§7) documented — and rehearsed or verified for mvp+ scope
- [ ] Monitoring/alerting in place for the success metrics in §6

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
| BO-{NNN} | {metric} | {result, or "measure after N days"} | [ ] Yes [ ] Pending |

---

## 7. Rollback Plan

{Summary — full detail in docs/runbook/local-setup.md §6: CDN cache invalidation
rollback, redeploy previous static build, feature-flag revert}

---

## Approvals

| Role | Status | Date |
|---|---|---|
| QA Lead (responsible — UAT sign-off) | Pending | |
| Product Owner (accountable — go-live decision) | Pending | |
| Tech Lead (consulted — technical readiness) | Pending | |
| DevOps/SRE (consulted — deployment readiness) | Pending | |
