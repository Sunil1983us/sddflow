## Scope Reference — What Each Scope Produces

| Document / Command | pilot | mvp | full |
|---|---|---|---|
| BRD, Use Cases, SRD | ✅ | ✅ | ✅ |
| `/checklist` | Optional | **Mandatory** | **Mandatory** |
| Security Design | §1 only | §1–2 | §1–4 |
| API Spec (`api-spec.md`) | — | ✅ | ✅ |
| Data Model (`data-model.md`) | — | ✅ | ✅ |
| Resilience (`resilience.md`) | — | — | ✅ |
| Investigation (`investigation.md`) | — | — | ✅ |
| `/plan-lld` | **SKIPPED** | ✅ | ✅ |
| QA Test Cases (`qa-testcases.md`) | **SKIPPED** | ✅ | ✅ |
| Smoke Tests (`smoke-tests.md`, ≤10 cases from UC paths) | ✅ | — (superseded by QA Test Cases) | — |
| Runbook (`runbook.md`) | — | ✅ | ✅ |

**Key skips at `pilot` scope:**
- `/plan-lld` — skipped; go directly from `/plan-design` to `/task`
- QA test cases — `/task` generates a ≤10-case `smoke-tests.md` instead of the full `qa-testcases.md`
- `/checklist` — optional (run for extra quality assurance or skip)
- Security Design stops at §1 (Threat Assessment only; no OWASP/STRIDE/DAST)
- Extended docs (API Spec, Data Model, Resilience, Investigation) — not generated
