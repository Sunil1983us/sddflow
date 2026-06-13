# Release Plan
# Feature: {Feature Name}
> Version: 1.0 | Date: {date} | Input: tasks.md (all complete) + qa-testcases.summary.md
> Run after: /implement — all tasks "PR ready" and merged
> Gate before: production go-live

---

## 1. Pre-Release Checklist

- [ ] All tasks in tasks.md complete and merged
- [ ] All PRs referenced TASK-NNN/CHG-NNN (constitution Git rule)
- [ ] Test suite green (unit + integration)
- [ ] Coverage ≥ gate (constitution Part 2)
- [ ] Security checklist passed (security-design.md section 1, +2 if mvp+)
- [ ] traceability.md — no FR/NFR without a passing test

---

## 2. UAT Plan

| UC-NNN (from SRD) | Scenario | Tester | Environment | Result |
|---|---|---|---|---|
| UC-001 | {happy path} | {role} | {staging} | [ ] Pass [ ] Fail |
| UC-002 | {unhappy path} | {role} | {staging} | [ ] Pass [ ] Fail |

**UAT Sign-off:** [ ] Product Owner   [ ] QA Lead

---

## 3. Deployment Plan

| Step | Action | Owner | Rollback If Fails |
|---|---|---|---|
| 1 | Deploy DB migrations (V{NNN}) | {role} | Run down-script (runbook §6) |
| 2 | Deploy application — {strategy: rolling/blue-green/canary} | {role} | Redeploy previous image tag |
| 3 | Smoke test (section 4) | {role} | Roll back step 2 |
| 4 | Enable feature flag / traffic shift | {role} | Disable flag / revert traffic |

**Environment promotion order:** {dev → staging → prod, or as applicable}

---

## 4. Post-Deploy Smoke Test

| Check | Expected | Result |
|---|---|---|
| `GET /actuator/health` | 200, status UP | [ ] |
| {key happy-path endpoint} | {expected response} | [ ] |
| Logs show no ERROR within {N} min | true | [ ] |
| {key NFR — e.g. P99 latency} | within target (NFR-{NNN}) | [ ] |

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

{Summary — full detail in runbook.md §6}

---
*Generated from: tasks.md + qa-testcases.summary.md + runbook.md*
