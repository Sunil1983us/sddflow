---
applyTo: "src/test/**"
---

- Naming: should_{expected}_when_{condition}
- Unit tests: mock all external dependencies — no real calls
- Mock adapters: @Profile("mock") — not in test classes
- Testcontainers: for all DB integration tests
- Coverage: minimum 80% on service classes
- Every class has a paired test class
