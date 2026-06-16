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
- [ ] Backend test suite green (unit + integration)
- [ ] Frontend test suite green (unit + component + E2E)
- [ ] Coverage ≥ gate (constitution Part 2) — backend and frontend
- [ ] Security checklist passed (security-design.md section 1, +2 if mvp+ —
      both server-side and client-side controls)
- [ ] traceability.md — no FR/NFR without a passing test

---

## 2. UAT Plan

| UC-NNN (from SRD) | Scenario | Tester | Environment | Result |
|---|---|---|---|---|
| UC-001 | {happy path — backend API} | {role} | {staging} | [ ] Pass [ ] Fail |
| UC-002 | {happy path — frontend screen/flow} | {role} | {staging} | [ ] Pass [ ] Fail |
| UC-003 | {unhappy path} | {role} | {staging} | [ ] Pass [ ] Fail |

**UAT Sign-off:** [ ] Product Owner   [ ] QA Lead

---

## 3. Deployment Plan

| Step | Action | Owner | Rollback If Fails |
|---|---|---|---|
| 1 | Deploy DB migrations (V{NNN}) | {role} | Run down-script (runbook §6) |
| 2 | Deploy backend application — {strategy: rolling/blue-green/canary} | {role} | Redeploy previous image tag |
| 3 | Build + deploy frontend static assets (CDN/static host or backend-served) | {role} | Redeploy previous frontend build / revert CDN deploy (runbook §6a) |
| 4 | Invalidate CDN cache (if applicable) | {role} | No action needed — previous assets still cached |
| 5 | Smoke test (section 4) | {role} | Roll back steps 2-4 |
| 6 | Enable feature flag / traffic shift | {role} | Disable flag / revert traffic |

**Environment promotion order:** {dev → staging → prod, or as applicable}

---

## 4. Post-Deploy Smoke Test

| Check | Expected | Result |
|---|---|---|
| `GET /actuator/health` | 200, status UP | [ ] |
| {key happy-path endpoint} | {expected response} | [ ] |
| Frontend app loads at {URL} | 200, app shell renders | [ ] |
| {key screen/flow} renders + calls backend successfully | {expected behaviour} | [ ] |
| Logs show no ERROR within {N} min (backend + frontend RUM) | true | [ ] |
| {key NFR — e.g. P99 latency or Core Web Vital} | within target (NFR-{NNN}) | [ ] |

---

## 5. Go-Live Gate

| Role | Decision | Date |
|---|---|---|
| Tech Lead | [ ] Go  [ ] No-Go | |
| Product Owner | [ ] Go  [ ] No-Go | |
| Ops/SRE | [ ] Go  [ ] No-Go | |

---

## 6. Business Objective Closure

| BO-NNN | Success Metric (from BRD) | Measured Result | Met? |
|---|---|---|---|
| BO-001 | {metric} | {result, or "measure after N days"} | [ ] Yes [ ] Pending |

---

## 7. Rollback Plan

{Summary — full detail in runbook.md §6 (backend) and §6a (frontend)}

---

## Approvals
| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
