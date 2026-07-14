# Release Plan
# Feature: {Feature Name}
> Version: 1.0 | Date: {date}
> Run after: /implement — all tasks complete ("PR ready" + merged in
> github mode, or "Task accepted" in local mode)
> Gate before: production go-live (app store / OTA)

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
- [ ] Test suite green (unit + screen/component + E2E)
- [ ] Coverage ≥ gate (constitution Part 2)
- [ ] Security checklist passed — see `security-design.md §1` signed by {security_officer} on {date} (evidence required, not self-attestation)
- [ ] stories.md Traceability Matrix — every FR-NNN has ≥ 1 TC-NNN and is passing

---

## 2. UAT Plan

| UC-NNN (from use-cases.md) | Scenario | Tester | Device/OS Target | Environment | Environment Prerequisites | Result |
|---|---|---|---|---|---|---|
| UC-{NNN} | {happy path} | {role} | {e.g. iPhone 15 / iOS 17} | {staging/TestFlight} | {e.g. push notifications enabled, backend on staging v2} | [ ] Pass [ ] Fail |
| UC-{NNN} | {unhappy path — offline} | {role} | {e.g. Pixel 8 / Android 14} | {staging/internal track} | {e.g. airplane mode enabled, offline sync queue seeded} | [ ] Pass [ ] Fail |

**UAT Sign-off:** [ ] Product Owner   [ ] QA Lead

---

## 3. Store Release Plan

### Strategy Selection

Choose release strategy based on risk and NFR requirements:

| Condition | Strategy | Rationale |
|---|---|---|
| High-risk change, large user base | Staged rollout (1% → 10% → 50% → 100%) | Limit blast radius; automated rollback on crash-rate threshold breach |
| OTA-eligible change (JS/config only, React Native/EAS) | OTA update (CodePush/EAS Update) | Instant delivery, instant rollback — no store review wait |
| Standard release, acceptable downtime window | Full rollout | Default — submit to store, release to 100% on approval |

**Selected strategy for this release:** {staged rollout | OTA update | full rollout} — Reason: {NFR-NNN or explicit decision}

### Steps

| Step | Action | Owner | Rollback If Fails |
|---|---|---|---|
| 1 | Build + sign release artifact (CI build container §OPS-7) | {role} | Discard artifact, fix, rebuild |
| 2 | Upload to TestFlight / Play Console internal track | {role} | Remove build from track |
| 3 | Staged rollout — {e.g. 10% → 50% → 100% over N days} | {role} | Halt rollout — runbook §staged rollout halt |
| 4 | OTA update push (CodePush/EAS — if applicable) | {role} | OTA rollback to previous bundle — runbook §OTA rollback |
| 5 | Smoke test on real device (section 4) | {role} | Halt rollout / pull OTA bundle |

**Environment promotion order:** {dev → internal track / TestFlight → staged rollout → 100%}

---

## 4. Post-Release Smoke Test

| Check | Expected | Result |
|---|---|---|
| App launch / cold start | App opens within {N}s, no crash | [ ] |
| {key happy-path screen flow} | {expected behaviour} | [ ] |
| Crash-free rate (Crashlytics / Play Vitals) | ≥ {target %} within {N}h of rollout | [ ] |
| {key NFR — e.g. cold start time, frame rate} | within target (NFR-{NNN}) | [ ] |

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

{Summary — full detail in docs/runbook/local-setup.md §6: staged rollout halt, OTA
rollback, store-listing rollback / emergency hotfix path}

---

## Approvals

| Role | Approver | Status | Date |
|---|---|---|---|
| QA Lead (responsible — UAT sign-off) | | Pending | |
| Product Owner (accountable — go-live decision) | | Pending | |
| Tech Lead (consulted — technical readiness) | | Pending | |
| DevOps/SRE (consulted — deployment readiness) | | Pending | |
