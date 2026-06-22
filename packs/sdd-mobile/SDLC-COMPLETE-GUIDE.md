# Complete SDLC Guide
# SDD — Complete Command Reference, Constitution Generated from Context

---

## Overview

You write one context file (or run `/create-context` first if you'd
rather paste rough notes and have the agent draft it with you — see
.specify/contexts/CONTEXT-GUIDE.md). Agent generates everything else.
Constitution Part 2 is auto-generated as a DRAFT — you review and
finalize it (GATE-1) before /validate runs. Manual edits after that
point are authoritative.
PLAN is split into 2 sub-commands — each reviewed separately.
/validate (business sign-off) and /release (UAT/store-release/go-live)
bookend the technical pipeline.

---

## Command Flow

| # | Command | Does | Gate Before |
|---|---|---|---|
| 1 | `/specify` | Constitution Part 2 (DRAFT) + spec docs | None |
| — | **GATE-1** | You finalize constitution Part 2 (manual) | After /specify |
| 2 | `/validate` | Business sign-off on BRD/SRD | GATE-1 passed |
| 3 | `/analyze` | Risks + dependencies + complexity | validate.summary.md |
| 4 | `/clarify` | Questions → you answer | After /analyze |
| 5 | `/plan-design` | Architecture + Diagrams + API Design + ADRs | clarify.summary.md, no open [ASSUMPTION-NNN] (AI-8) |
| 6 | `/plan-lld` | LLD class/sequence diagrams (mvp+ only) | design.md reviewed |
| 7 | `/task` | Stories + Tasks + Jira | design.md reviewed |
| 10 | `/implement` | One task at a time | tasks approved |
| 11 | `/release` | UAT + store-release plan + go-live gate | all tasks merged |

---

## /specify — Two Actions

**Action 1 — Constitution Part 2 (DRAFT):**
Reads context → fills Tech Stack:
Language/Framework, Navigation, State Management, Local Storage/DB,
API Client, Push Notifications, Crash/Analytics, Build Tool, Testing,
Coverage Gate, Quality/Security, CI/CD, App Store Distribution, plus the
remaining backend-style concerns adapted for mobile (see constitution.md
Part 2 Tech Stack table)

Also extracts: Core Principles (Offline-First, Accessible, Cross-Platform,
Performant), Domain Rules, Never Do

**Action 2 — Spec Documents (canonical doc inventory):**
```
pilot: brd → srd → security-design (§1)
mvp:   + screen-spec → ux-flow → api-spec (Backend API Contract —
         Consumer) → security-design (§1-2)
full:  + data-model (Local Data & Cache Model) →
         resilience (Mobile Resilience) →
         investigation (Crash & Incident Triage) →
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

## PLAN — 2 Sub-Commands

```
/plan-design  Architecture + Diagrams + API Design + ADR entries
              Who reviews: Tech lead + Architect + Stakeholders
              AI-8 gate: no unresolved [ASSUMPTION-NNN] anywhere
              ↓
/plan-lld     LLD + class/sequence diagrams (mvp+ only)
              Who reviews: Senior developer
```

**Pilot scope:** only /plan-design required.
Agent auto-skips /plan-lld for pilot — states reason.


---

## Pilot Flow
```
/specify → [GATE-1] → /validate → /analyze → /clarify
→ /plan-design (review)
→ /task (review) → /implement → /release
```

## MVP+ Flow
```
/specify → [GATE-1] → /validate → /analyze → /clarify
→ /plan-design (review) → /plan-lld (review)
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

## /release — UAT, Store Release, Go-Live

Runs after /implement — all tasks "PR ready" and merged.

1. Pre-Release Checklist (tests green, coverage, security checklist,
   traceability — no FR/NFR without a passing test)
2. UAT Plan — UC-NNN → tester (roles.yml) → device/OS target →
   environment (staging/TestFlight/internal track) → result
3. Store Release Plan — build + sign release artifact (CI build
   container §OPS-7) → upload to TestFlight / Play Console internal
   track → staged rollout (e.g. 10% → 50% → 100%) → OTA update push
   (CodePush/EAS, if applicable) → smoke test on real device, each step
   with owner + rollback-if-fails (constitution Part 1 — OPS-7)
4. Post-Release Smoke Test (app launch/cold start, key happy-path flow,
   crash-free rate target)
5. Go-Live Gate — Tech Lead / Product Owner / Ops-SRE: Go/No-Go
6. Business Objective Closure — BO-NNN → measured result → met?
7. Rollback Plan (full detail in runbook.md §6 — staged rollout halt,
   OTA rollback, store-listing rollback)

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
- [ ] context.md written with tech stack section (directly, or via
      `/create-context` from informal notes)
- [ ] Git initialised

### /specify
- [ ] Constitution Part 2 generated (DRAFT) — Tech Stack table reviewed
- [ ] All spec docs generated + .summary.md (brd, srd, security-design
      §1, + screen-spec/ux-flow/api-spec §1-2 for mvp+,
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
- [ ] validate.summary.md = "VALIDATE complete"

### /analyze
- [ ] Gated on validate.summary.md = "VALIDATE complete"
- [ ] Risk register reviewed — every risk linked to FR/NFR (AR-3)
- [ ] Complexity hotspots noted

### /clarify
- [ ] All items answered
- [ ] clarify.summary.md confirmed — all RESOLVED

### /plan-design
- [ ] AI-8: no unresolved [ASSUMPTION-NNN] anywhere
- [ ] Architecture reviewed by tech lead
- [ ] Diagrams complete
- [ ] API Design locked
- [ ] design.md reviewed

### /plan-lld (mvp+)
- [ ] Class + sequence diagrams reviewed

### /task
- [ ] Stories make business sense
- [ ] All tasks have estimated lines + Verifies: TC-NNN
- [ ] Over-limit tasks marked SPLIT
- [ ] Jira CSV imported
- [ ] stories.md + tasks.md BOTH approved

### /implement
- [ ] AI-7: .github/instructions/* applied to matching files
- [ ] Each task estimated before coding
- [ ] Each PR under line + file limits
- [ ] Paired test every PR
- [ ] All criteria confirmed per task
- [ ] Confirm Verifies: TC-NNN covered by paired test
- [ ] Tests passing before merge
- [ ] qa_cases/runbook (mvp+) generated
- [ ] All tasks "PR ready" → "Ready for /release"

### /release
- [ ] Pre-release checklist green
- [ ] UAT plan executed, sign-off recorded
- [ ] Store release plan reviewed (OPS-7 — TestFlight/Play Console,
      staged rollout, OTA if applicable)
- [ ] Post-release smoke test + crash-free rate target met
- [ ] Go-live gate: all roles "Go"
- [ ] Business objective closure recorded
- [ ] Rollback plan confirmed (runbook.md §6)
