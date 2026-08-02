## Scope Reference — What Each Scope Produces

`lean`/`standard`/`regulated` are accepted as friendlier aliases for `pilot`/`mvp`/`full` wherever scope is set (`setup.sh`/`setup.ps1`'s `--scope`, `sdd init`'s `-s`/`--scope`) — resolved to the canonical name before anything is written. `manifest.yml`'s own `scope:` field, and everything below, only ever uses `pilot`/`mvp`/`full`.

| Document / Command | pilot (lean) | mvp (standard) | full (regulated) |
|---|---|---|---|
| BRD, Use Cases, SRD | ✅ | ✅ | ✅ |
| `/checklist` | Optional | **Mandatory** | **Mandatory** |
| Security Design (living — `.specify/service/security-design.md`) | §1 only | §1–2 | §1–4 |
| API Spec — services that **provide** an API (living — `.specify/service/api-spec.md`, via `/plan-design` §3) | — | ✅ | ✅ |
| API Spec — components that only **consume** an API (frontend-spa, mobile: per-feature, in `design.md` §3 — not living, see `plan-design.prompt.md`) | — | ✅ | ✅ |
| Data Model (living — `.specify/service/data-model.md`, or this pack's equivalent — state/storage model, local cache model) | — | ✅ | ✅ |
| Resilience (`resilience.md`) | — | — | ✅ |
| Investigation (`investigation.md`) | — | — | ✅ |
| `/plan-lld` | **SKIPPED** | ✅ | ✅ |
| QA Test Cases (`qa-testcases.md`) | **SKIPPED** | ✅ | ✅ |
| Smoke Tests (`smoke-tests.md`, ≤10 cases from UC paths) | ✅ | — (superseded by QA Test Cases) | — |
| Runbook (living — `docs/runbook/local-setup.md`) | — | ✅ | ✅ |

**Key skips at `pilot` scope:**
- `/plan-lld` — skipped; go directly from `/plan-design` to `/task`
- QA test cases — `/task` generates a ≤10-case `smoke-tests.md` instead of the full `qa-testcases.md`
- `/checklist` — optional (run for extra quality assurance or skip)
- Security Design stops at §1 (Threat Assessment only; no OWASP/STRIDE/DAST)
- Extended docs (API Spec, Data Model, Resilience, Investigation) — not generated
