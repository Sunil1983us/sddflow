# Complete SDLC Guide
# SDD — 11 Commands + GATE-1, Constitution Generated from Context

---

## Overview

You write one context file. Agent generates everything else.
Constitution Part 2 is auto-generated as a DRAFT — you review and
finalize it (GATE-1) before /validate runs. Manual edits after that
point are authoritative.
PLAN is split into 4 sub-commands — each reviewed separately.
/validate (business sign-off) and /release (UAT/go-live) bookend the
technical pipeline.

---

## The 11 Commands

| # | Command | Does | Gate Before |
|---|---|---|---|
| 1 | `/specify` | Constitution Part 2 (DRAFT) + spec docs | None |
| — | **GATE-1** | You finalize constitution Part 2 (manual) | After /specify |
| 2 | `/validate` | Business sign-off on BRD/SRD | GATE-1 passed |
| 3 | `/analyze` | Risks + dependencies + complexity | validate.summary.md |
| 4 | `/clarify` | Questions → you answer | After /analyze |
| 5 | `/plan-arch` | Component architecture + plan.md + refine scope docs | clarify.summary.md, no open [ASSUMPTION-NNN] (AI-8) |
| 6 | `/plan-hld` | HLD + Mermaid diagrams | arch.md reviewed |
| 7 | `/plan-lld` | LLD (mvp+ only) | hld.md reviewed |
| 8 | `/plan-adr` | ADRs (mvp+ only) | arch.md reviewed |
| 9 | `/task` | Stories + Tasks + Jira | hld.md reviewed |
| 10 | `/implement` | One task at a time | tasks approved |
| 11 | `/release` | UAT + deployment + go-live gate | all tasks merged |

---

## /specify — Two Actions

**Action 1 — Constitution Part 2 (DRAFT):**
Reads context → fills Tech Stack:
Language/Framework, Build Tool, State Management, Component
Library/Design System, Routing, API Client, Bundler, Data Cache,
Configuration, Secrets, Resilience, Observability, Logging, Testing,
Coverage Gate, Linting/Formatting, Accessibility, CI/CD, Hosting/CDN

Also extracts: Core Principles, Domain Rules, Never Do

**Action 2 — Spec Documents (canonical doc inventory):**
```
pilot: brd → srd → security-design (§1)
mvp:   + component-spec → ux-flow → api-spec (Backend API Contract —
         Consumer) → security-design (§1-2)
full:  + data-model (Frontend State & Storage Model) →
         resilience (Frontend Resilience) →
         investigation (Production Debugging & Error Tracking) →
         security-design (§1-4)
```

---

## GATE-1 — Finalize Constitution Part 2 (manual, blocking)

After Action 1, Part 2 is a DRAFT. Before any later command runs:
1. Review every row (Tech Stack, Core Principles, Domain Rules, Never Do)
2. Resolve `[MISSING — ask user]` markers
3. Edit anything wrong — manual edits are AUTHORITATIVE
4. Tell agent: "Constitution Part 2 finalized"

A later /specify re-run proposes changes for review — never silently
overwrites a finalized Part 2.

---

## /validate — Business Sign-Off

Reviewer: Product Owner (accountable) + Business Analyst (responsible) —
see roles.yml.

- Business Objective Trace: every BO-NNN → FR-NNN
- Business Requirements Review: every BR-NNN reflected in SRD
- Assumptions Sign-Off: every [ASSUMPTION-NNN] confirmed/rejected
- Scope Confirmation: in/out of scope
- Sign-off table: Approved / Changes Requested

Outcome: "VALIDATE complete — ready for /analyze" or
"VALIDATE incomplete — {N} items need changes."

---

## PLAN — 4 Sub-Commands

```
/plan-arch   Component architecture decisions + plan.md
             + refine component-spec/ux-flow/api-spec (mvp+),
               data-model/resilience/investigation (full),
               security-design (all)
             Who reviews: Tech lead
             AI-8 gate: no unresolved [ASSUMPTION-NNN] anywhere
             ↓
/plan-hld    HLD + all Mermaid diagrams (component diagrams)
             Who reviews: Stakeholders + tech lead
             ↓
/plan-lld    LLD + component/class diagrams (mvp+ only)
             Who reviews: Senior developer (frontend)
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
4. Confirm Verifies: TC-NNN now covered by the paired test

---

## Feature → Story → Task (/task)

```
FEATURE (from BRD)
  └── STORY (As/I want/So that — linked to FRs)
        ├── Story points + Sprint
        ├── Acceptance criteria
        └── TASK (one PR each)
              ├── Satisfies: FR/NFR | Verifies: TC-NNN
              ├── Estimated lines
              └── PR strategy: single or SPLIT
```

Traceability matrix (QA-1): Story → FR → Task → TC-NNN → R-NNN.
Jira CSV generated at /task — import before /implement starts.

---

## /release — UAT, Deployment, Go-Live

Runs after /implement — all tasks "PR ready" and merged.

1. Pre-Release Checklist (tests green, coverage, accessibility checks,
   security, traceability)
2. UAT Plan — UC-NNN → tester (roles.yml) → environment/browser-matrix →
   result
3. Deployment Plan — build static assets → upload to CDN/object storage
   → cache invalidation → smoke test → traffic shift, each with owner +
   rollback-if-fails (constitution Part 1 — OPS-7)
4. Post-Deploy Smoke Test
5. Go-Live Gate — Tech Lead / Product Owner / Ops-SRE: Go/No-Go
6. Business Objective Closure — BO-NNN → measured result → met?
7. Rollback Plan (full detail in runbook.md §6)

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
- [ ] roles.yml filled (RACI owners)
- [ ] context.md written with tech stack section
- [ ] Git initialised

### /specify
- [ ] Constitution Part 2 generated (DRAFT) — Tech Stack table reviewed
- [ ] All spec docs generated + .summary.md (brd, srd, security-design
      §1, + component-spec/ux-flow/api-spec §1-2 for mvp+,
      + data-model/resilience/investigation/security-design §1-4 for full)
- [ ] BRD + SRD reviewed

### GATE-1
- [ ] Every Part 2 row reviewed, [MISSING] markers resolved
- [ ] "Constitution Part 2 finalized" confirmed

### /validate
- [ ] Every BO-NNN traced to FR-NNN
- [ ] Every BR-NNN reflected in SRD
- [ ] Every [ASSUMPTION-NNN] confirmed or rejected
- [ ] Product Owner + Business Analyst sign-off

### /analyze
- [ ] Risk register reviewed — every risk linked to FR/NFR (AR-3)
- [ ] Complexity hotspots noted

### /clarify
- [ ] All items answered
- [ ] clarify.summary.md confirmed

### /plan-arch
- [ ] AI-8: no unresolved [ASSUMPTION-NNN] anywhere
- [ ] Architecture reviewed by tech lead
- [ ] plan.md reviewed
- [ ] NFR → Decision mapping complete (arch.md §4a)
- [ ] component-spec/ux-flow/api-spec/data-model/resilience/investigation/
      security-design refined (where applicable)

### /plan-hld
- [ ] All diagrams correct
- [ ] Stakeholders reviewed

### /plan-lld (mvp+)
- [ ] Component + class diagrams reviewed

### /plan-adr (mvp+)
- [ ] All key decisions captured, arch.md §4 ADR column filled

### /task
- [ ] Stories make business sense
- [ ] All tasks have estimated lines + Verifies: TC-NNN
- [ ] Over-limit tasks marked SPLIT
- [ ] Jira CSV imported
- [ ] stories.md + tasks.md BOTH approved

### /implement
- [ ] Each task estimated before coding
- [ ] Each PR under line + file limits
- [ ] Paired test every PR
- [ ] All criteria confirmed per task
- [ ] axe-core accessibility check passed per component
- [ ] Tests passing before merge
- [ ] qa_cases/runbook (mvp+) generated

### /release
- [ ] Pre-release checklist green
- [ ] UAT plan executed, sign-off recorded
- [ ] Deployment + rollback plan reviewed (OPS-7 — static asset deploy)
- [ ] Go-live gate: all roles "Go"
- [ ] Business objective closure recorded
