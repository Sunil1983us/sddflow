# Task List
# Feature: {Feature Name}
> Version: 1.0 | Date: {date}

---

## References
| Source | Sections / IDs Used |
|---|---|
| plan.summary.md | {sections/IDs referenced} |

## Phase A — Foundation

### TASK-001 — Project Scaffold + Dependencies
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
Satisfies: FR-{NNN}
Dependencies: TASK-001
Estimated lines: ~60 | PR: single
Files: {Entity}.java, {EntityStatus}.java, {Entity}Test.java
Acceptance criteria:
  - [ ] Entity has all fields from data model
  - [ ] All status values defined in enum
  - [ ] Unit test covers creation + state transitions

### TASK-003 — Port Interfaces
Satisfies: Architecture — hexagonal pattern
Dependencies: TASK-002
Estimated lines: ~40 | PR: single
Files: {Feature}UseCase.java, {Integration}Port.java, {Repository}Port.java
Acceptance criteria:
  - [ ] Inbound port defines use case contract
  - [ ] All outbound ports defined as interfaces
  - [ ] No implementation in port files

### TASK-004 — DB Migration Scripts
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
Satisfies: Testing strategy
Dependencies: TASK-002
Estimated lines: ~80 | PR: single
Files: MockDataFactory.java
Acceptance criteria:
  - [ ] Factory provides all test data needed
  - [ ] All entities constructable from factory
  - [ ] All mock responses constructable

### TASK-006 — Mock Adapters
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
Satisfies: FR-{NNN}, FR-{NNN}
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
Satisfies: FR-{NNN} (API contract)
Dependencies: TASK-002
Estimated lines: ~60 | PR: single
Files: {Feature}Request.java, {Feature}Response.java, {Error}Response.java
Acceptance criteria:
  - [ ] All request fields validated with annotations
  - [ ] Response contains all required fields
  - [ ] Records are immutable

### TASK-010 — Controller
Satisfies: FR-{NNN}
Dependencies: TASK-003, TASK-009
Estimated lines: ~60 | PR: single
Files: {Feature}Controller.java, {Feature}ControllerTest.java
Acceptance criteria:
  - [ ] Endpoint accepts correct request
  - [ ] Returns correct HTTP status
  - [ ] Missing mandatory field returns 400
  - [ ] Delegates to use case — no logic in controller

### TASK-011 — Exception Handler
Satisfies: NFR-{NNN} (error handling)
Dependencies: TASK-009
Estimated lines: ~60 | PR: single
Files: GlobalExceptionHandler.java, GlobalExceptionHandlerTest.java
Acceptance criteria:
  - [ ] All exception types mapped to correct HTTP status
  - [ ] Error response uses standard format
  - [ ] No stack traces in response

### TASK-012 — Integration Test
Satisfies: All FRs — end-to-end verification
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
Satisfies: NFR-{NNN} (deployment)
Dependencies: TASK-012
Estimated lines: ~80 | PR: single
Files: Dockerfile, docker-compose.yml, application.yml, application-mock.yml
Acceptance criteria:
  - [ ] docker-compose up starts all services
  - [ ] Health check passes
  - [ ] Mock profile activates in compose
  - [ ] No secrets in any committed file

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
