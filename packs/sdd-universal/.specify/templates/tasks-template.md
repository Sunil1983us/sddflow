# Task List
# Feature: {Feature Name}
> Version: 1.0 | Date: {date: YYYY-MM-DD}

---

## Stack Reference (derived from constitution.md Part 2)
> Kai fills this table before writing any task. File names, test commands,
> and build commands in tasks.md must come from these values — never hardcode
> a stack-specific idiom in a task.

| Row | Value from constitution.md |
|---|---|
| Language + file extension | {e.g. TypeScript → .ts / Kotlin → .kt / Dart → .dart / Python → .py} |
| Framework | {e.g. React / Spring Boot / Flutter / FastAPI / Next.js} |
| File naming convention | {e.g. PascalCase components / snake_case modules / kebab-case files} |
| Test framework + command | {e.g. Jest `npm test` / JUnit `./mvnw test` / pytest `pytest` / flutter test} |
| Build command | {e.g. `npm run build` / `./mvnw package` / `flutter build apk`} |
| Data Store | {e.g. PostgreSQL / MongoDB / SQLite / None} |
| DB Migration tool | {e.g. Flyway / Liquibase / Alembic / prisma migrate / None} |
| Orchestration | {None / Docker Compose / Kubernetes} |

---

## References
| Source | Sections / IDs Used |
|---|---|
| constitution.md | Tech Stack rows — Language, Framework, Testing, Orchestration |
| srd.summary.md | FR-NNN list and priorities (order tasks CRITICAL → HIGH → MEDIUM) |
| analyze.summary.md | R-NNN risk items → SPLIT flags + story-point inflation |
| use-cases.summary.md | EP-NNN exception paths → paired TC-NNN targets |
| design.summary.md / lld.summary.md | Architecture layers, component / service names |
| data-model.summary.md | Entity / schema names used in file name derivation (if present) |
| api-spec.summary.md | Endpoint names used in file name derivation (if present) |

## Task Field Reference
Every task includes:
- `Story:` — STORY-NNN this task belongs to (from stories.md) —
  populates the Jira CSV Parent column for this task
- `Satisfies:` — FR-NNN / NFR-NNN / architectural rule this task delivers
- `Verifies:` — TC-NNN (mvp+, from qa-testcases.md) this task's paired
  test covers. If qa-testcases.md not yet generated (pilot, or before
  /implement), write `Verifies: TBD — link at /implement`.
- `Risk:` — R-NNN from analyze.summary.md §2 if this task carries a flagged risk
- `Dependencies:`, `Estimated lines:`, `PR:`, `Files:`, `Acceptance criteria:`

> **Numbering rule:** Kai assigns TASK-{NNN} numbers sequentially when
> generating tasks.md — the numbers in this template are placeholders only.
> Dependencies are expressed as descriptions (e.g. "scaffold task",
> "domain models task") so that Kai replaces them with the real TASK-NNN
> numbers once the full list is assembled.
>
> **File name rule:** `{Entity}`, `{Feature}`, `{ext}` are placeholders.
> Kai derives real values from Stack Reference above + entity names in
> data-model.summary.md (or srd.md if no data-model). Never copy `.java`,
> `.ts`, or any other extension from this template — read constitution first.

---

## Phase A — Foundation

### TASK-{NNN} — Project Scaffold + Dependencies
Story: STORY-{NNN}
Satisfies: NFR-{NNN} (build), NFR-{NNN} (tech stack)
Dependencies: none
Estimated lines: ~50 | PR: single
Files:
  {build file — package.json / pom.xml / pubspec.yaml / build.gradle / Cargo.toml / pyproject.toml}
  {config file — tsconfig.json / .eslintrc / application.yml / pytest.ini}
Acceptance criteria:
  - [ ] **If the build/config files already exist from a prior feature:
        this task is a no-op unless this feature adds a genuinely new
        dependency — add only that dependency, don't regenerate the
        file.** Scaffold is a once-per-service task, not once-per-feature.
  - [ ] Build tool configured with all required dependencies
  - [ ] Language version locked (from constitution.md Language row)
  - [ ] `{build command}` completes with zero errors
  - [ ] Test runner executes with `{test command}` — zero tests, zero failures

### TASK-{NNN} — Domain Models / Entities
Story: STORY-{NNN}
Satisfies: FR-{NNN} (core data model)
Verifies: TC-{NNN} (unit — model creation + field validation)
Risk: R-{NNN} — add if analyze.md flags schema or data complexity
Dependencies: scaffold task
Estimated lines: ~60 | PR: single
Files:
  {Entity}.{ext}                        ← domain model / entity class
  {Entity}Status.{ext}                  ← status/state enum (if applicable)
  {Entity}.test.{ext}                   ← unit test (naming per constitution Testing row)
Acceptance criteria:
  - [ ] All fields present per data-model.summary.md (or srd.md if no data-model)
  - [ ] All status / enum values defined
  - [ ] Unit test covers creation and field-level constraints

### TASK-{NNN} — Contracts / Interfaces (Architecture Layer)
Story: STORY-{NNN}
Satisfies: Architecture — {layer pattern from design.summary.md, e.g. hexagonal / clean / layered / component}
Dependencies: domain models task
Estimated lines: ~40 | PR: single
Files:
  {Feature}UseCase.{ext} / {Feature}Service.{ext}     ← inbound contract
  {Feature}Repository.{ext} / {Feature}Port.{ext}     ← outbound contract
  (exact names from architecture layer in design.summary.md)
Acceptance criteria:
  - [ ] All inbound contracts (service interface / use case / port) defined
  - [ ] All outbound contracts (repository / gateway / port) defined
  - [ ] No implementation logic in interface / contract files

### TASK-{NNN} — Data Store Setup
> Skip this task entirely if constitution.md Data Store row = "None".
Story: STORY-{NNN}
Satisfies: FR-{NNN} (persistence)
Dependencies: domain models task
Estimated lines: ~30 | PR: single
Files:
  {migration — V{NNN}__{desc}.sql / {NNN}_{desc}.up.sql / {timestamp}_{desc}.py / schema.prisma}
  (tool from constitution.md DB Migration row)
Acceptance criteria:
  - [ ] All tables / collections / schemas created with correct types
  - [ ] All required indexes defined
  - [ ] Migration runs cleanly on a fresh data store

---

## Phase B — Test Doubles / Stubs

> One stub per outbound contract defined in the contracts task (Phase A).
> Stub tool = constitution.md Testing row (Jest mocks / Mockito / MockK / unittest.mock / mockito_dart).
> Skip Phase B stub files if the project's test strategy uses a real embedded
> data store for all tests (e.g. H2 in-memory / Testcontainers always-on).

### TASK-{NNN} — Test Data Factory
Story: STORY-{NNN}
Satisfies: Testing strategy (constitution.md Testing row)
Dependencies: domain models task
Estimated lines: ~80 | PR: single
Files:
  {Feature}Factory.{ext} / mock_{feature}.{ext} / fixtures/{feature}.{ext}
  (naming follows project convention — check existing tests if any)
Acceptance criteria:
  - [ ] Factory provides all test entities / DTOs needed by subsequent tasks
  - [ ] All domain models constructable from factory without boilerplate
  - [ ] All mock / stub responses constructable from factory

### TASK-{NNN} — {Integration} Stubs
Story: STORY-{NNN}
Satisfies: FR-{NNN} (integration contracts)
Dependencies: contracts task, test data factory task
Estimated lines: ~{N} | PR: SPLIT A/B if > {max_lines_per_pr from manifest.pr_rules}
Files:
  {Mock}{Integration1}.{ext}, {Mock}{Integration2}.{ext}
  (one file per outbound contract / external API from design.summary.md)
Acceptance criteria:
  - [ ] All outbound contracts have a stub / mock implementation
  - [ ] Happy path returns a valid canned response
  - [ ] Stubs isolated to test scope — no production code path affected

---

## Phase C — Feature Implementation (one task per Story / FR-NNN)

> Kai generates one task per story from stories.md, ordered CRITICAL → HIGH → MEDIUM.
> Assign sequential TASK-{NNN} numbers continuing from the last Phase B number.
> Flag SPLIT on any task where analyze.md carries a matching R-NNN high-risk item,
> or where the estimated line count exceeds max_lines_per_pr.

### TASK-{NNN} — {Story-001 capability, e.g. "Process Payment / Register User / Render Dashboard"}
Story: STORY-{NNN}
Satisfies: FR-{NNN}, FR-{NNN}
Verifies: TC-{NNN}, TC-{NNN} (from qa-testcases.md, mvp+)
Risk: R-{NNN} — {risk title from analyze.md, if applicable}
Dependencies: contracts task, test data factory task, integration stubs task
Estimated lines: ~{N} | PR: {single | SPLIT A: … B: …}
Files:
  {Feature}Service.{ext}          ← service / use-case implementation
  {Feature}Repository.{ext}       ← data-access adapter (if persistence needed)
  {Feature}Service.test.{ext}     ← unit test with mocked dependencies
Acceptance criteria:
  - [ ] FR-{NNN}: {acceptance condition from srd.md}
  - [ ] FR-{NNN}: {acceptance condition from srd.md}
  - [ ] Unit test passes with all dependencies mocked
  - [ ] EP-{NNN} exception paths produce correct error / recovery (from use-cases.md)

### TASK-{NNN} — {Story-002 capability}
Story: STORY-{NNN}
Satisfies: FR-{NNN}
Verifies: TC-{NNN}
Risk: R-{NNN} — {if flagged}
Dependencies: previous feature task (or contracts task if independent)
Estimated lines: ~{N} | PR: single
Files:
  {derived from Stack Reference + design.summary.md}
Acceptance criteria:
  - [ ] FR-{NNN}: {acceptance condition}
  - [ ] Unit test passes

> … Kai generates TASK-{NNN}, TASK-{NNN} … for every remaining story in priority order …

---

## Phase D — API / Presentation Layer

> One task per public interface type. Choose tasks that apply to this project:
> — REST: DTOs + Controller + Exception Handler
> — GraphQL: schema + resolver + error type
> — tRPC: router + procedure + error handler
> — Frontend SPA: page component + routing + form validation
> — Mobile: screen + navigation + state binding
> Derive naming convention from constitution.md Framework row.

### TASK-{NNN} — Request / Response Types (DTOs / Schemas / Props)
Story: STORY-{NNN}
Satisfies: FR-{NNN} (API or UI contract)
Dependencies: domain models task
Estimated lines: ~60 | PR: single
Files:
  {Feature}Request.{ext}, {Feature}Response.{ext}, {Feature}ErrorResponse.{ext}
Acceptance criteria:
  - [ ] All request fields validated per srd.md constraints
  - [ ] Response shape matches api-spec.summary.md (if present)
  - [ ] Types / records / schemas are immutable

### TASK-{NNN} — {Controller / Resolver / Router / Page / Screen}
Story: STORY-{NNN}
Satisfies: FR-{NNN}
Verifies: TC-{NNN} (contract — request / response / render shape)
Dependencies: contracts task, request/response types task
Estimated lines: ~60 | PR: single
Files:
  {Feature}Controller.{ext} / {Feature}Screen.{ext} / {Feature}Page.{ext}
  {Feature}Controller.test.{ext} / {Feature}Screen.test.{ext}
Acceptance criteria:
  - [ ] Endpoint / screen accepts correct input shape
  - [ ] Returns correct HTTP status / navigation outcome
  - [ ] Missing mandatory field returns validation error (400 or equivalent)
  - [ ] No business logic — delegates to service / use case only

### TASK-{NNN} — Error / Exception Handling
Story: STORY-{NNN}
Satisfies: NFR-{NNN} (error handling)
Dependencies: request/response types task
Estimated lines: ~60 | PR: single
Files:
  GlobalExceptionHandler.{ext} / ErrorBoundary.{ext} / error-handler.{ext}
  GlobalExceptionHandler.test.{ext}
Acceptance criteria:
  - [ ] All exception types mapped to correct response (HTTP status or UI error state)
  - [ ] Error response follows standard format from srd.md §Error Handling
  - [ ] No internal stack traces or sensitive data exposed

---

## Phase E — Integration + End-to-End Tests

### TASK-{NNN} — Integration / E2E Test Suite
Story: STORY-{NNN}
Satisfies: All FRs — end-to-end verification
Verifies: TC-{NNN} (integration — full input → data store → response path)
Dependencies: all Phase C + Phase D tasks
Estimated lines: ~120 | PR: single
Files:
  {Feature}IntegrationTest.{ext} / {feature}.e2e.{ext} / test_{feature}_integration.{ext}
  (naming per constitution.md Testing row)
Acceptance criteria:
  - [ ] Full request → data store → response path verified end-to-end
  - [ ] Happy path completes with expected status / output
  - [ ] All EP-{NNN} exception paths return correct errors (from use-cases.md)
  - [ ] All TC-{NNN} from qa-testcases.md covered (mvp+)

---

## Phase F — Infrastructure

### TASK-{NNN} — Container + Runtime Config
Story: STORY-{NNN}
Satisfies: NFR-{NNN} (deployment)
Dependencies: integration test green
Estimated lines: ~80 | PR: single
Files:
  Dockerfile
  docker-compose.yml
  {runtime config — application.yml / .env.example / config.ts / settings.py}
Acceptance criteria:
  - [ ] **If `Dockerfile`/`docker-compose.yml` already exist from a prior
        feature: extend them (add only the new service(s)/config this
        feature needs) — do NOT regenerate from the template. A blind
        regeneration silently drops whatever a previous feature added.**
  - [ ] `docker-compose up` (or equivalent) starts all services
  - [ ] Health check / readiness probe passes
  - [ ] Test / mock profile activates correctly in compose
  - [ ] No credentials or secrets in any committed file

> **If constitution.md Orchestration row = Kubernetes:**
> Add to this task (or split as a separate TASK-{NNN} if > max_lines_per_pr):
> Files (Leo generates from k8s-manifest-template.md during /implement):
>   k8s/deployment.yaml, k8s/service.yaml, k8s/hpa.yaml,
>   k8s/networkpolicy.yaml, k8s/configmap.yaml, k8s/secret.yaml
> Extra acceptance criteria:
>   - [ ] **If these manifests already exist from a prior feature: extend
>         them — do NOT regenerate from the template.**
>   - [ ] `kubectl apply --dry-run=client -f k8s/` validates cleanly
>   - [ ] HPA min / max replicas satisfy NFR-{NNN} throughput target
>   - [ ] NetworkPolicy restricts ingress to intended services only
>   - [ ] No plaintext secrets in any k8s manifest (use Secret references)

---

## Phase G — Performance Tests (NFR-driven)

> Generate one PERF task per NFR that has a measurable numeric threshold
> (from srd.md §NFRs — e.g. P99 ≤ 500ms, 100 TPS, < 1% error rate).
> Skip this phase entirely if no NFR has a measurable threshold.
> Tool: k6 / Gatling / Locust / JMeter / Lighthouse — from constitution.md Testing row.

### PERF-{NNN} — Load Test: {NFR-NNN title}
Story: STORY-{NNN}
Satisfies: NFR-{NNN} ({threshold, e.g. P99 ≤ 500ms at 100 TPS})
Dependencies: integration test green, staging environment ready
Estimated lines: ~60 | PR: single
Files: {perf/load-test-{nfr}.js | perf/LoadTest{NFR}.scala | tests/perf/test_{nfr}.py}
Acceptance criteria:
  - [ ] {N} concurrent virtual users sustained for 60 seconds
  - [ ] P99 response ≤ {threshold}
  - [ ] Error rate < 1%
  - [ ] Results artifact attached to PR

---

## Summary
| Phase | Tasks | Est. Lines | PRs |
|---|---|---|---|
| A Foundation | TASK-{NNN} to TASK-{NNN} | ~{sum} | {count} |
| B Test Doubles | TASK-{NNN} to TASK-{NNN} | ~{sum} | {count} |
| C Feature Impl | TASK-{NNN} to TASK-{NNN} | ~{sum} | {count} |
| D API / Presentation | TASK-{NNN} to TASK-{NNN} | ~{sum} | {count} |
| E Integration | TASK-{NNN} | ~120 | 1 |
| F Infrastructure | TASK-{NNN} | ~80 | {1-2} |
| G Performance | PERF-{NNN} to PERF-{NNN} | ~{sum} | {count} |
| **Total** | **{N} tasks** | **~{sum}** | **{count} PRs** |

---

## Approvals
| Role | Approver | Status | Date |
|---|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | | Pending | |
