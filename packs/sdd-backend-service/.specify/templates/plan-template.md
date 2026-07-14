# Implementation Plan
# Feature: {Feature Name}
> Version: 1.0 | Status: Draft | Date: {date} | Author: {author}

---

## References

| Source | Sections / IDs Used |
|---|---|
| design.summary.md | {architecture pattern, layers, API design applied} |

## 1. Tech Stack (from constitution)

| Concern | Choice |
|---|---|
| Language | {from constitution} |
| Framework | {from constitution} |
| Database | {from constitution} |
| Build | {from constitution} |
| Testing | {from constitution} |

## 2. Implementation Order

### Phase A — Foundation
1. Project scaffold + dependencies
2. Domain entities + enums
3. Port interfaces (in + out)
4. DTOs (records)
5. DB migration scripts (Flyway)

### Phase B — Mock Layer
6. MockDataFactory
7. Mock adapters for all outbound ports (@Profile mock)
8. Verify happy path end-to-end with mocks

### Phase C — Persistence
9. JPA entity + repository
10. Repository adapter (implements port)
11. Testcontainers integration test

### Phase D — Service Layer
12. Service implementation
13. Service unit tests (mock all ports)

### Phase E — API Layer
14. Controller
15. Exception handler
16. Request validation
17. Integration test (full HTTP → DB)

### Phase F — Infrastructure
18. docker-compose.yml
19. Dockerfile (multi-stage)
20. application.yml (mock + prod profiles)
21. CI/CD pipeline file

## 3. Test Strategy

| Layer | Framework | Scope |
|---|---|---|
| Domain | JUnit 5 | Pure unit — no deps |
| Service | JUnit 5 + Mockito | Mock all ports |
| Repository | Testcontainers | Real DB |
| Controller | MockMvc / WebTestClient | Full HTTP |
| Integration | Testcontainers | Full stack |

## 4. Mock Strategy
- All outbound integrations start as mocks.
- @Profile("mock") — activated in dev + test.
- @Profile("prod") — real adapter in production.
- MockDataFactory provides all test data.
- Mocks only return happy path in pilot scope.

## 5. Configuration

| Profile | Purpose | DB | Integrations |
|---|---|---|---|
| mock | Development + test | H2 or Testcontainers | All mocked |
| prod | Production | Real DB | All real |

## 6. Delivery Checklist
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Coverage ≥ gate from constitution
- [ ] docker-compose up — health check passes
- [ ] All FRs verified against acceptance criteria

---

## Approvals

| Role | Approver | Status | Date |
|---|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | | Pending | |

## Version History

| Version | Date | Changed By | Summary of Changes | CHG-NNN |
|---|---|---|---|---|
| 1.0 | {date} | {author} | Initial draft | — |
