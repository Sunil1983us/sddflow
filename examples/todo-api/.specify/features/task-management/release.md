# Release Plan
## Feature: Task Management
## Project: Todo API | Run by: /release

---

## Pre-Release Checklist

### Code & Quality
- [x] All 10 tasks merged and PR-approved
- [x] Test coverage ≥ 80% (gate in CI)
- [x] SAST scan (Semgrep) passing — 0 HIGH/CRITICAL findings
- [x] Load test (k6, 100 concurrent users, 5 min): p95 < 200 ms ✅

### Observability
- [x] Structured JSON logging with request_id and hashed user_id on all endpoints
- [x] Prometheus metrics: `sdd_tasks_created_total`, `sdd_tasks_purged_total`
- [x] Alerts configured: p95 > 300 ms → warning; error rate > 1% → critical

### Data & Migration
- [x] Migration `20260617_task_management` applied to staging ✅
- [x] Indexes created and verified via `EXPLAIN ANALYZE` on staging data

---

## UAT Scenarios

| Scenario | Steps | Expected | Tester | Status |
|---|---|---|---|---|
| UAT-001 Create task | Log in → POST /tasks {title: "Buy milk", priority: "high"} → verify 201 | Task created, visible in GET /tasks | QA Lead | ✅ PASS |
| UAT-002 Filter by priority | GET /tasks?priority=high | Only high-priority tasks returned | QA Lead | ✅ PASS |
| UAT-003 Mark complete | PATCH /tasks/:id {status: "done"} | 200; completed_at set | QA Lead | ✅ PASS |
| UAT-004 Delete task | DELETE /tasks/:id; GET /tasks | 204; task absent from list | QA Lead | ✅ PASS |
| UAT-005 Isolation | User A creates task; User B GET /tasks | User B sees 0 tasks from User A | QA Lead | ✅ PASS |

---

## Deployment Plan

| Step | Action | Owner | Rollback |
|---|---|---|---|
| 1 | Deploy to staging; run smoke tests | Tech Lead | Revert Helm chart |
| 2 | Run UAT scenarios | QA Lead | N/A |
| 3 | Run migration on production (zero-downtime: additive) | DevOps/SRE | Revert migration script available |
| 4 | Deploy to production (blue-green) | DevOps/SRE | Switch traffic to blue |
| 5 | Monitor error rate + p95 for 30 min post-deploy | On-call | Immediate rollback if error rate > 1% |

---

## Go / No-Go Gate

| Role | Name | Decision | Date |
|---|---|---|---|
| QA Lead | Priya Nair | **GO** | 2026-06-17 |
| Product Owner | Sarah Chen | **GO** | 2026-06-17 |
| Tech Lead | Marcus Webb | **GO** | 2026-06-17 |
| DevOps/SRE | Raj Patel | **GO** | 2026-06-17 |

**Decision: GO — deploy to production on 2026-06-17 at 14:00 UTC.**

---

## Business Objective Closure

| BO | Objective | Measurement plan |
|---|---|---|
| BO-001 | Free-to-paid conversion +5% | Monitor via analytics dashboard; review at 30, 60, 90 days post-launch |
| BO-002 | 30-day retention 60% → 70% | Cohort analysis in product analytics; first checkpoint at 30 days |
