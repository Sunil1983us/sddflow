# Release Plan
# Feature: {Feature Name}
> Version: 1.0 | Date: {date}
> Run after: /implement — all tasks complete ("PR ready" + merged in
> github mode, or "Task accepted" in local mode)
> Gate before: production go-live

---

## References

| Source | Sections / IDs Used |
|---|---|
| tasks.md | {sections/IDs referenced} |
| qa-testcases.summary.md | {sections/IDs referenced} |
| docs/runbook/local-setup.md (mvp+) | {sections/IDs referenced} |

## 1. Pre-Release Checklist

- [ ] All tasks in tasks.md complete and merged
- [ ] All PRs referenced TASK-NNN/CHG-NNN (constitution Git rule)
- [ ] Test suite green (unit + integration)
- [ ] Coverage ≥ gate (constitution Part 2)
- [ ] Security checklist passed (security-design.md section 1, +2 if mvp+)
- [ ] stories.md Traceability Matrix — every FR-NNN has ≥ 1 TC-NNN and is passing

---

## 2. UAT Plan

| UC-NNN (from use-cases.md) | Scenario | Tester | Environment | Result |
|---|---|---|---|---|
| UC-{NNN} | {happy path} | {role} | {staging} | [ ] Pass [ ] Fail |
| UC-{NNN} | {unhappy path} | {role} | {staging} | [ ] Pass [ ] Fail |

**UAT Sign-off:** [ ] Product Owner   [ ] QA Lead

---

## 3. Deployment Plan

| Step | Action | Owner | Rollback If Fails |
|---|---|---|---|
| 1 | Deploy DB migrations (V{NNN}) | {role} | Run down-script (docs/runbook/local-setup.md §6) |
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
| QA Lead | [ ] Go  [ ] No-Go | |
| Ops/SRE | [ ] Go  [ ] No-Go | |

---

## 6. Business Objective Closure

| BO-NNN | Success Metric (from BRD) | Measured Result | Met? |
|---|---|---|---|
| BO-{NNN} | {metric} | {result, or "measure after N days"} | [ ] Yes [ ] Pending |

---

## 7. Rollback Plan

{Summary — full detail in docs/runbook/local-setup.md §6}

---

## Approvals

| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
