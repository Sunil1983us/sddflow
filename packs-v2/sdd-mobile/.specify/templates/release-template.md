# Release Plan
# Feature: {Feature Name}
> Version: 1.0 | Date: {date} | Input: tasks.md (all complete) + qa-testcases.summary.md
> Run after: /implement — all tasks "PR ready" and merged
> Gate before: production go-live (app store / OTA)

---

## 1. Pre-Release Checklist

- [ ] All tasks in tasks.md complete and merged
- [ ] All PRs referenced TASK-NNN/CHG-NNN (constitution Git rule)
- [ ] Test suite green (unit + screen/component + E2E)
- [ ] Coverage ≥ gate (constitution Part 2)
- [ ] Security checklist passed (security-design.md section 1, +2 if mvp+)
- [ ] traceability.md — no FR/NFR without a passing test

---

## 2. UAT Plan

| UC-NNN (from SRD) | Scenario | Tester | Device/OS Target | Environment | Result |
|---|---|---|---|---|---|
| UC-001 | {happy path} | {role} | {e.g. iPhone 15 / iOS 17} | {staging/TestFlight} | [ ] Pass [ ] Fail |
| UC-002 | {unhappy path — offline} | {role} | {e.g. Pixel 8 / Android 14} | {staging/internal track} | [ ] Pass [ ] Fail |

**UAT Sign-off:** [ ] Product Owner   [ ] QA Lead

---

## 3. Store Release Plan

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

{Summary — full detail in runbook.md §6: staged rollout halt, OTA
rollback, store-listing rollback / emergency hotfix path}

---
*Generated from: tasks.md + qa-testcases.summary.md + runbook.md*
