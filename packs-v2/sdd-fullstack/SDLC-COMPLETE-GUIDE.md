# Complete SDLC Guide
# SDD — 11 Commands + GATE-1, Constitution Generated from Context

---

## Overview

You write one context file (or run `/create-context` first if you'd
rather paste rough notes — covering backend, frontend, or both — and have
the agent draft it with you — see .specify/contexts/CONTEXT-GUIDE.md).
Agent generates everything else.
Constitution Part 2 is auto-generated as a DRAFT — split Backend /
Frontend / Shared — you review and finalize it (GATE-1) before /validate
runs. Manual edits after that point are authoritative.
PLAN is split into 4 sub-commands — each reviewed separately.
/validate (business sign-off) and /release (UAT/go-live) bookend the
technical pipeline.

---

## The 11 Commands

| # | Command | Does | Gate Before |
|---|---|---|---|
| 1 | `/specify` | Constitution Part 2 (DRAFT, both layers) + spec docs | None |
| — | **GATE-1** | You finalize constitution Part 2 (manual) | After /specify |
| 2 | `/validate` | Business sign-off on BRD/SRD | GATE-1 passed |
| 3 | `/analyze` | Risks + dependencies + complexity | validate.summary.md |
| 4 | `/clarify` | Questions → you answer | After /analyze |
| 5 | `/plan-arch` | Architecture + plan.md + refine scope docs (both layers) | clarify.summary.md, no open [ASSUMPTION-NNN] (AI-8) |
| 6 | `/plan-hld` | HLD + Mermaid diagrams | arch.md reviewed |
| 7 | `/plan-lld` | LLD (mvp+ only) | hld.md reviewed |
| 8 | `/plan-adr` | ADRs (mvp+ only) | arch.md reviewed |
| 9 | `/task` | Stories + Tasks + Jira | plan.md reviewed |
| 10 | `/implement` | One task at a time (both layers) | tasks approved |
| 11 | `/release` | UAT + deployment + go-live gate | all tasks merged |

---

## /specify — Two Actions

**Action 1 — Constitution Part 2 (DRAFT):**
Reads context → fills Tech Stack, split Backend / Frontend / Shared:
```
Backend:  Language, Framework, Build Tool, Messaging/Async, Schema,
          Data Store, Data Cache, DB Migration, Resilience, Testing,
          Coverage Gate
Frontend: Language, Framework, Build Tool, State Management, Component
          Library/Design System, Routing, API Client, Data Cache,
          Testing, Coverage Gate, Accessibility
Shared:   API Style, Serialisation, Configuration, Secrets,
          Observability, Logging, Quality/Security, Orchestration, CI/CD
```

Also extracts: Core Principles, Domain Rules, Never Do

**Action 2 — Spec Documents (canonical doc inventory):**
```
pilot: brd → srd → security-design (§1)
mvp:   + api-spec (Shared API Contract) → component-spec → ux-flow →
         data-model (Backend Schema & Persistence Model) →
         security-design (§1-2)
full:  + resilience → investigation → security-design (§1-4)
```

---

## GATE-1 — Finalize Constitution Part 2 (manual, blocking)

After Action 1, Part 2 is a DRAFT. Before any later command runs:
1. Review every row — Backend Tech Stack, Frontend Tech Stack, Shared
   Tech Stack, Core Principles, Domain Rules, Never Do
2. Resolve `[MISSING — ask user]` markers
3. Edit anything wrong — manual edits are AUTHORITATIVE
4. Tell agent: "Constitution Part 2 finalized"

A later /specify re-run proposes changes for review — never silently
overwrites a finalized Part 2.

---

## /validate — Business Sign-Off

Reviewer: Product Owner (accountable) + Business Analyst (responsible) —
see roles.yml.

- Business Objective Trace: every BO-NNN → FR-NNN (backend FRs and
  frontend/UX FRs alike)
- Business Requirements Review: every BR-NNN reflected in SRD
- Assumptions Sign-Off: every [ASSUMPTION-NNN] confirmed/rejected
- Scope Confirmation: in/out of scope
- Sign-off table: Approved / Changes Requested

Outcome: "VALIDATE complete — ready for /analyze" or
"VALIDATE incomplete — {N} items need changes."

---

## PLAN — 4 Sub-Commands

```
/plan-arch   Architecture decisions + plan.md
             + refine api-spec.md (mvp+ — align with port/adapter
               contracts and frontend service layer — single shared
               contract), component-spec.md/ux-flow.md (mvp+ — frontend
               component tree + state architecture), data-model.md
               (mvp+ — backend schema/persistence design),
               security-design.md (all — both layers),
               resilience.md + investigation.md (full — both layers)
             Who reviews: Tech lead
             AI-8 gate: no unresolved [ASSUMPTION-NNN] anywhere
             ↓
/plan-hld    HLD + all Mermaid diagrams
             Who reviews: Stakeholders + tech lead
             ↓
/plan-lld    LLD + class/component diagrams (mvp+ only)
             Who reviews: Senior developer (backend + frontend)
             ↓
/plan-adr    Architecture Decision Records (mvp+ only)
             Who reviews: Architect
```

**Pilot scope:** only /plan-arch and /plan-hld required.
Agent auto-skips /plan-lld and /plan-adr for pilot — states reason.

---

## Pilot Flow
```
/specify → [GATE-1] → /validate → /analyze → /clarify
→ /plan-arch (review) → /plan-hld (review)
→ /task (review) → /implement → /release
```

## MVP+ Flow
```
/specify → [GATE-1] → /validate → /analyze → /clarify
→ /plan-arch (review) → /plan-hld (review)
→ /plan-lld (review) → /plan-adr (review)
→ /task (review) → /implement → /release
```

---

## PR Rules (enforced at /implement)

Every task before coding:
1. Agent estimates lines
2. If > max_lines_per_pr → SPLIT A/B/C → confirm → one at a time
3. After task → state files + lines + "PR ready" → wait for go

---

## Feature → Story → Task (/task)

```
FEATURE (from BRD)
  └── STORY (As/I want/So that — linked to FRs)
        ├── Story points + Sprint
        ├── Acceptance criteria
        └── TASK (one PR each)
              ├── Estimated lines
              ├── Files that will change
              └── PR strategy: single or SPLIT
```

Jira CSV generated at /task — import before /implement starts.

---

## /release — UAT, Deployment, Go-Live

Runs after /implement — all tasks "PR ready" and merged.

1. Pre-Release Checklist (all tasks complete + merged, PRs reference
   TASK-NNN/CHG-NNN, backend + frontend test suites green, coverage ≥
   gate (constitution Part 2), security checklist passed
   (security-design.md §1, +§2 mvp+, covering both server-side and
   client-side controls), traceability.md has no FR/NFR without a
   passing test if present)
2. UAT Plan — one row per UC-NNN from srd.md: scenario, tester role
   (roles.yml), environment, result — include both backend (API/data)
   and frontend (screen/component) scenarios
3. Deployment Plan — DB migrations, backend app deploy strategy,
   frontend build + static asset deploy/CDN invalidation, smoke test,
   feature flag/traffic shift, each with owner + rollback-if-fails
   (constitution Part 1 — OPS-7)
4. Post-Deploy Smoke Test — backend health check, key happy-path
   endpoint, frontend app loads + key screen renders, log check, key
   NFR check
5. Go-Live Gate — Tech Lead / Product Owner / Ops-SRE: Go/No-Go (from
   roles.yml)
6. Business Objective Closure — BO-NNN → measured result → met?
7. Rollback Plan (full detail in runbook.md §6 backend / §6a frontend)

---

## Change Management

Rule: context.md first — always.

```
Update context.md + CHANGELOG
→ Re-run /specify for affected docs only
→ Re-run /analyze if risk changed
→ Append CHG-NNN tasks
→ /implement CHG tasks (same PR rules)
→ /release for the change set if it ships independently
```

See CHANGE-GUIDE.md for the full impact matrix and AI-8 assumption rule.

---

## Full Checklist

### Setup
- [ ] manifest.yml filled (4 fields)
- [ ] roles.yml filled (RACI owners — both senior_developer_backend and
      senior_developer_frontend)
- [ ] context.md written with Backend + Frontend + Shared tech stack
      sections (directly, or via `/create-context` from informal notes)
- [ ] Git initialised

### /specify
- [ ] Constitution Part 2 generated (DRAFT) — Backend / Frontend / Shared
      Tech Stack tables reviewed
- [ ] All spec docs generated + .summary.md (brd, srd, security-design
      §1, + api-spec/component-spec/ux-flow/data-model + security-design
      §1-2 for mvp+, + resilience/investigation/security-design §1-4 for
      full)
- [ ] BRD + SRD reviewed

### GATE-1
- [ ] Every Part 2 row reviewed (Backend, Frontend, Shared), [MISSING]
      markers resolved
- [ ] "Constitution Part 2 finalized" confirmed

### /validate
- [ ] Every BO-NNN traced to FR-NNN (backend + frontend)
- [ ] Every BR-NNN reflected in SRD
- [ ] Every [ASSUMPTION-NNN] confirmed or rejected
- [ ] Product Owner + Business Analyst sign-off

### /analyze
- [ ] Risk register reviewed
- [ ] Complexity hotspots noted

### /clarify
- [ ] All items answered
- [ ] clarify.summary.md confirmed

### /plan-arch
- [ ] AI-8: no unresolved [ASSUMPTION-NNN] anywhere
- [ ] Architecture reviewed by tech lead
- [ ] plan.md reviewed
- [ ] api-spec/component-spec/ux-flow/data-model/security-design/
      resilience/investigation refined (where applicable)

### /plan-hld
- [ ] All diagrams correct
- [ ] Stakeholders reviewed

### /plan-lld (mvp+)
- [ ] Class + component diagrams reviewed by senior developer (backend +
      frontend)

### /plan-adr (mvp+)
- [ ] All key decisions captured

### /task
- [ ] Stories make business sense
- [ ] All tasks have estimated lines
- [ ] Over-limit tasks marked SPLIT
- [ ] Jira CSV imported
- [ ] stories.md + tasks.md BOTH approved

### /implement
- [ ] Each task estimated before coding
- [ ] Each PR under line + file limits
- [ ] Paired test every PR (backend + frontend)
- [ ] All criteria confirmed per task
- [ ] Backend + frontend tests passing, E2E tests passing before merge
- [ ] openapi.yaml generated (+ qa_cases/runbook for mvp+)

### /release
- [ ] Pre-release checklist green
- [ ] UAT plan executed (backend + frontend scenarios), sign-off recorded
- [ ] Deployment + rollback plan reviewed (OPS-7)
- [ ] Go-live gate: all roles "Go"
- [ ] Business objective closure recorded
