# Task List
# Feature: {Feature Name}
> Version: 1.0 | Date: {date}

---

## References
| Source | Sections / IDs Used |
|---|---|
| design.summary.md | {architecture, API design, implementation order applied} |

## Task Field Reference
Every task includes:
- `Story:` — STORY-NNN this task belongs to (from stories.md) —
  populates the Jira CSV Parent column for this task
- `Satisfies:` — FR-NNN / NFR-NNN / architectural rule this task delivers
- `Verifies:` — TC-NNN (mvp+, from qa-testcases.md) this task's paired
  test covers. If qa-testcases.md not yet generated (pilot, or before
  /implement), write `Verifies: TBD — link at /implement`.
- `Dependencies:`, `Estimated lines:`, `PR:`, `Files:`, `Acceptance criteria:`

---

## Phase A — Foundation

### TASK-001 — Project Scaffold + Dependencies
Story: STORY-001
Satisfies: NFR-001 (build), NFR-{N} (tech stack)
Dependencies: none
Estimated lines: ~50 | PR: single
Files: pom.xml / package.json / build.gradle
Acceptance criteria:
  - [ ] Build tool configured with all dependencies
  - [ ] {language} version set correctly
  - [ ] Mock profile activates cleanly
  - [ ] `{build command}` passes

### TASK-002 — Domain Entity + Enum
Story: STORY-001
Satisfies: FR-{NNN}
Verifies: TC-{NNN} (unit — entity creation + state transitions)
Dependencies: TASK-001
Estimated lines: ~60 | PR: single
Files: {Entity}.java, {EntityStatus}.java, {Entity}Test.java
Acceptance criteria:
  - [ ] Entity has all fields from data model
  - [ ] All status values defined in enum
  - [ ] Unit test covers creation + state transitions

### TASK-003 — Port Interfaces
Story: STORY-001
Satisfies: Architecture — hexagonal pattern
Dependencies: TASK-002
Estimated lines: ~40 | PR: single
Files: {Feature}UseCase.java, {Integration}Port.java, {Repository}Port.java
Acceptance criteria:
  - [ ] Inbound port defines use case contract
  - [ ] All outbound ports defined as interfaces
  - [ ] No implementation in port files

### TASK-004 — DB Migration Scripts
Story: STORY-002
Satisfies: FR-{NNN} (persistence)
Dependencies: TASK-002
Estimated lines: ~30 | PR: single
Files: V001__{desc}.sql, V002__{desc}.sql
Acceptance criteria:
  - [ ] All tables created with correct types
  - [ ] All indexes created
  - [ ] Migration runs cleanly on empty DB

---

## Phase B — Mock Layer

### TASK-005 — MockDataFactory
Story: STORY-002
Satisfies: Testing strategy
Dependencies: TASK-002
Estimated lines: ~80 | PR: single
Files: MockDataFactory.java
Acceptance criteria:
  - [ ] Factory provides all test data needed
  - [ ] All entities constructable from factory
  - [ ] All mock responses constructable

### TASK-006 — Mock Adapters
Story: STORY-003
Satisfies: FR-{NNN} (integration mocks)
Dependencies: TASK-003, TASK-005
Estimated lines: ~120 | PR: SPLIT (A: mock1+mock2, B: mock3+mock4)
Files: Mock{Integration1}Adapter.java, Mock{Integration2}Adapter.java...
Acceptance criteria:
  - [ ] All outbound ports have mock implementation
  - [ ] All mocks annotated @Profile("mock")
  - [ ] Happy path returns correct mock response

---

## Phase C — Persistence

### TASK-007 — JPA Repository
Story: STORY-003
Satisfies: FR-{NNN} (persistence)
Dependencies: TASK-002, TASK-004
Estimated lines: ~80 | PR: single
Files: {Entity}JpaEntity.java, Spring{Entity}Repository.java, Jpa{Entity}Adapter.java, Jpa{Entity}AdapterTest.java
Acceptance criteria:
  - [ ] Entity persisted and retrieved correctly
  - [ ] Status update persists correctly
  - [ ] Testcontainers test passes with real DB

---

## Phase D — Service Layer

### TASK-008 — Service Implementation
Story: STORY-003
Satisfies: FR-{NNN}, FR-{NNN}
Verifies: TC-{NNN}, TC-{NNN} (unit — service happy path + failure paths)
Dependencies: TASK-003, TASK-006, TASK-007
Estimated lines: ~150 | PR: SPLIT (A: steps 1-3, B: steps 4-6)
Files: {Feature}Service.java, {Feature}ServiceTest.java
Acceptance criteria:
  - [ ] Happy path flow completes end-to-end
  - [ ] Status persisted before each integration call
  - [ ] All integration results handled correctly
  - [ ] Unit test with mocked ports passes

---

## Phase E — API Layer

### TASK-009 — DTOs (Records)
Story: STORY-004
Satisfies: FR-{NNN} (API contract)
Dependencies: TASK-002
Estimated lines: ~60 | PR: single
Files: {Feature}Request.java, {Feature}Response.java, {Error}Response.java
Acceptance criteria:
  - [ ] All request fields validated with annotations
  - [ ] Response contains all required fields
  - [ ] Records are immutable

### TASK-010 — Controller
Story: STORY-004
Satisfies: FR-{NNN}
Verifies: TC-{NNN} (controller — request/response contract)
Dependencies: TASK-003, TASK-009
Estimated lines: ~60 | PR: single
Files: {Feature}Controller.java, {Feature}ControllerTest.java
Acceptance criteria:
  - [ ] Endpoint accepts correct request
  - [ ] Returns correct HTTP status
  - [ ] Missing mandatory field returns 400
  - [ ] Delegates to use case — no logic in controller

### TASK-011 — Exception Handler
Story: STORY-004
Satisfies: NFR-{NNN} (error handling)
Dependencies: TASK-009
Estimated lines: ~60 | PR: single
Files: GlobalExceptionHandler.java, GlobalExceptionHandlerTest.java
Acceptance criteria:
  - [ ] All exception types mapped to correct HTTP status
  - [ ] Error response uses standard format
  - [ ] No stack traces in response

### TASK-012 — Integration Test
Story: STORY-005
Satisfies: All FRs — end-to-end verification
Verifies: TC-{NNN} (integration — full request→DB→response path)
Dependencies: TASK-007, TASK-008, TASK-010
Estimated lines: ~120 | PR: single
Files: {Feature}IntegrationTest.java
Acceptance criteria:
  - [ ] Full HTTP request → DB verified
  - [ ] Happy path status sequence verified
  - [ ] Error paths return correct responses

---

## Phase F — Infrastructure

### TASK-013 — Docker + Config
Story: STORY-005
Satisfies: NFR-{NNN} (deployment)
Dependencies: TASK-012
Estimated lines: ~80 | PR: single
Files: Dockerfile, docker-compose.yml, application.yml, application-mock.yml
- If Orchestration = Kubernetes (constitution.md Tech Stack): also
  k8s/deployment.yaml, k8s/service.yaml, k8s/hpa.yaml,
  k8s/networkpolicy.yaml, k8s/configmap.yaml, k8s/secret.yaml — from
  k8s-manifest-template.md
Acceptance criteria:
  - [ ] docker-compose up starts all services
  - [ ] Health check passes
  - [ ] Mock profile activates in compose
  - [ ] No secrets in any committed file
  - [ ] If Orchestration = Kubernetes: `kubectl apply --dry-run=client
        -f k8s/` validates cleanly

---

## Phase G — Performance Tests (NFR-driven)

> Generated for each NFR with a measurable threshold (from srd.md §3).
> Tool is set from constitution Part 2 → Testing row (k6 / Gatling / Locust / JMeter).

### PERF-001 — Load Test: {NFR-NNN title}
Story: STORY-{NNN}
Satisfies: NFR-{NNN} ({threshold, e.g. P99 ≤ 500ms at 100 TPS})
Dependencies: TASK-012 (integration test green), staging environment ready
Estimated lines: ~60 | PR: single
Files: {perf/load-test-{nfr}.js or similar}
Acceptance criteria:
  - [ ] {N} concurrent virtual users sustained for 60 seconds
  - [ ] P99 response ≤ {threshold}
  - [ ] Error rate < 1%
  - [ ] Results attached to PR

---

## Summary
| Phase | Tasks | Est. Lines | PRs |
|---|---|---|---|
| A Foundation | TASK-001 to 004 | ~180 | 4 |
| B Mocks | TASK-005 to 006 | ~200 | 3 |
| C Persistence | TASK-007 | ~80 | 1 |
| D Service | TASK-008 | ~150 | 2 |
| E API | TASK-009 to 012 | ~300 | 4 |
| F Infra | TASK-013 | ~80 | 1 |
| **Total** | **13 tasks** | **~990** | **15 PRs** |

---

## Approvals
| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
