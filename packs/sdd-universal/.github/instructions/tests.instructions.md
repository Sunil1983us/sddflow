---
applyTo: "**/test/**,**/tests/**,**/*.test.*,**/*.spec.*,**/test_*.py,**/*_test.go,**/*Test.java,**/*Test.kt"
---

- Naming: should_{expected}_when_{condition} (adapt casing to language convention)
- Style: follow manifest.testing_style — paired (default) / tdd / bdd
- Unit tests: mock all external dependencies — no real network, DB, or filesystem
- Every class/module/component has a paired test — same PR, never deferred
- Integration tests: real dependency via container/fixture — never against shared envs
- Coverage: meet the Coverage Gate row in constitution.md Part 2
- Assert behaviour and outputs — never implementation details (private state, call counts without cause)
