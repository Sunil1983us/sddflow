# Release Plan
# Feature: {Feature Name}
> Version: 1.0 | Date: {date: YYYY-MM-DD}
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
- [ ] Security checklist passed — see `security-design.md §1` signed by {security_officer} on {date: YYYY-MM-DD} (evidence required, not self-attestation)
- [ ] stories.md Traceability Matrix — every FR-NNN has ≥ 1 TC-NNN and is passing

---

## 2. UAT Plan

| UC-NNN (from use-cases.md) | TC-NNN (from qa-testcases.md, UAT Relevant: Yes) | Scenario | Tester | Environment | Environment Prerequisites | Result |
|---|---|---|---|---|---|---|
| UC-{NNN} | TC-{NNN} | {happy path} | {role} | {staging} | {e.g. payment sandbox v2 configured, test card set loaded} | [ ] Pass [ ] Fail |
| UC-{NNN} | TC-{NNN} | {unhappy path} | {role} | {staging} | {e.g. mock integration set to timeout mode} | [ ] Pass [ ] Fail |

> TC-NNN column traces to qa-testcases.md §1 Test Coverage Summary rows marked `UAT Relevant: Yes` — every such TC-NNN must appear in exactly one row above before UAT sign-off.

**UAT Sign-off:** [ ] Product Owner   [ ] QA Lead

---

## 3. Deployment Plan

### Strategy Selection

Choose deployment strategy based on NFR requirements:

| Condition | Strategy | Rationale |
|---|---|---|
| Zero-downtime required (NFR mandates < 0.1% error rate during deploy) | Blue-Green | Full environment swap with instant traffic cut-over; rollback = flip DNS back |
| Gradual rollout preferred + monitoring in place to catch error-rate spikes | Canary | Shift 5% → 25% → 100% traffic with automated rollback trigger |
| No strict uptime NFR + simple single-instance service | Rolling | Default — replace instances one at a time; simplest operational model |

**Selected strategy for this release:** {rolling | blue-green | canary} — Reason: {NFR-NNN or explicit decision}

### Steps

| Step | Action | Owner | Rollback If Fails |
|---|---|---|---|
| 1 | Deploy DB migrations (V{NNN}) | {role} | Run down-script (docs/runbook/local-setup.md §6 or §7 below for pilot) |
| 2 | Deploy application — {selected strategy} | {role} | Redeploy previous image tag |
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
| No new P1/P2 alerts in monitoring system within {N} min of deploy | Zero new alerts | [ ] |
| Error rate in APM/dashboard | < 1% baseline | [ ] |

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
| BO-{NNN} | {metric} | {result, or "measure after N days"} | [ ] Yes  [ ] No  [ ] Pending |

---

## 7. Rollback Plan

> **MVP+ scope:** Full rollback detail is in `docs/runbook/local-setup.md §6`. Summary below for quick reference.
>
> **Pilot scope:** Runbook not generated at pilot scope. Document your rollback steps here before proceeding to §5 Go-Live Gate. Minimum required:

| Step | Action | Owner | Time Estimate |
|---|---|---|---|
| 1 | Revert application to previous image / deployment | {devops_sre} | {N} min |
| 2 | Roll back DB migrations if any were applied (run V{NNN}__down.sql) | {devops_sre} | {N} min |
| 3 | Verify health endpoint returns 200 on previous version | {devops_sre} | {N} min |
| 4 | Notify stakeholders — rollback complete | {tech_lead} | {N} min |

**Rollback decision owner:** Tech Lead — triggers rollback if smoke test fails or P1 alert fires within {N} min of go-live.
**Maximum acceptable rollback time:** {N} minutes (from decision to stable previous state).

---

## Approvals

| Role | Approver | Status | Date |
|---|---|---|---|
| QA Lead (responsible — UAT sign-off) | | Pending | |
| Product Owner (accountable — go-live decision) | | Pending | |
| Tech Lead (consulted — technical readiness) | | Pending | |
| DevOps/SRE (consulted — deployment readiness) | | Pending | |
