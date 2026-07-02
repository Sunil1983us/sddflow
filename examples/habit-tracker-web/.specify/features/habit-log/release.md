# Release Plan — Habit Log
## Feature: habit-log | Run by: /release
> Version: 1.0 | Status: Approved | Date: 2026-07-01

---

## 1. Deployment

Static hosting (GitHub Pages). Rollback = redeploy previous tagged build.

## 2. UAT Scenarios

| ID | Scenario | Source | Result |
|---|---|---|---|
| UAT-001 | Create habit → check in → reload → streak persists | TC-S-001/002 | PASSED |
| UAT-002 | Miss a scheduled day → current streak resets, best kept | STORY-002 AC-3 | PASSED |
| UAT-003 | Archive habit → gone from today, history intact | TC-S-008 | PASSED |
| UAT-004 | Offline reload → app fully functional | TC-S-010 | PASSED |

## 5. Go-Live Gate

**Preconditions:** all TASK-001..008 merged ✅ · UAT passed ✅ · rollback documented (§1) ✅ · opt-in WAU counter live ✅

| Role | Decision | Date |
|---|---|---|
| Tech Lead | GO | 2026-07-01 |
| Product Owner | GO | 2026-07-01 |
| QA Lead | GO | 2026-07-01 |

**Decision: GO — APPROVED for launch.**

## 6. Business Objective Closure

| BO | Metric | Result |
|---|---|---|
| BO-001 | 500 WAU in 60 days | Measure after 60 days — counter live |
| BO-002 | ≥ 40% 7-day return | Measure after 14 days |
