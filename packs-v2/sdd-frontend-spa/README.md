# SDD Frontend SPA Pack
## React · Vue · Angular · Svelte
## Stacks: TypeScript · JavaScript

---

## What Is This?

Spec-Driven Development framework for single page applications.
You write what your system does — agent generates everything else.
Constitution Part 2 is auto-generated from your context as a DRAFT —
you review and finalize it (GATE-1) before work continues.

---

## The 3 Files You Need

### 1. contexts/{feature}.md — Your system description (15-30 min)
Include a Tech Stack section — agent extracts it for constitution.
Use CONTEXT-GUIDE.md as your guide.

### 2. manifest.yml — 4 fields only (2 min)
```yaml
project:
  name: "Your App"
  scope: "pilot"
  feature: "your-feature"
  context_file: "your-feature.md"
```

### 3. constitution.md Part 2 — Generated (draft) by /specify, finalized by you
Agent reads your context → fills Tech Stack (Framework, State Management,
Routing, API Client, Bundler, Accessibility, Hosting/CDN, and more) +
Principles + Rules as a DRAFT. You review every row and confirm
"Constitution Part 2 finalized" (GATE-1) before /validate runs.

---

## The 11 Commands

```
/specify    → Constitution Part 2 (DRAFT) + spec documents
[GATE-1]    → You review + finalize constitution Part 2 (manual)
/validate   → Business sign-off on BRD/SRD
/analyze    → Risks + dependencies + complexity
/clarify    → Questions → you answer them
/plan-arch  → Component architecture decisions + plan + refine scope docs
/plan-hld   → HLD + all Mermaid diagrams
/plan-lld   → Low Level Design (mvp+ only)
/plan-adr   → Architecture Decision Records (mvp+ only)
/task       → Feature → Story → Task + Jira CSV
/implement  → Code one task at a time, PR rules enforced
/release    → UAT + deployment plan + go-live gate
```

### Pilot Flow (9 commands + GATE-1)
```
/specify → [GATE-1] → /validate → /analyze → /clarify
→ /plan-arch → /plan-hld → /task → /implement → /release
```

### MVP+ Flow (11 commands + GATE-1)
```
/specify → [GATE-1] → /validate → /analyze → /clarify
→ /plan-arch → /plan-hld → /plan-lld → /plan-adr
→ /task → /implement → /release
```

---

## What /specify Does

Two actions automatically:
1. Reads context → fills constitution Part 2 (DRAFT):
   Language/Framework, Build Tool, State Management, Component
   Library/Design System, Routing, API Client, Bundler, Data Cache,
   Configuration, Secrets, Resilience, Observability, Logging, Testing,
   Coverage Gate, Linting/Formatting, Accessibility, CI/CD, Hosting/CDN
   + Core Principles + Domain Rules + Never Do

2. Generates spec documents per scope (see table below).

**GATE-1:** the constitution Part 2 is a DRAFT until you review every row
and tell the agent "Constitution Part 2 finalized". Manual edits after
that point are authoritative.

---

## PLAN — 4 Sub-Commands, Each Reviewed Separately

| Command | Generates | Reviewer (see roles.yml) |
|---|---|---|
| /plan-arch | Component architecture + plan.md + refine component-spec/ux-flow/api-spec/data-model/security-design/resilience/investigation | Tech lead |
| /plan-hld | HLD + all Mermaid diagrams | Stakeholders + tech lead |
| /plan-lld | LLD + component/class diagrams (mvp+) | Senior developer (frontend) |
| /plan-adr | ADRs (mvp+) | Architect |

---

## Document Inventory by Scope/Command (canonical)

| Command | Pilot | MVP | Full |
|---|---|---|---|
| /specify | BRD, SRD, Security-Design (§1) | + Component-Spec, UX-Flow, Backend API Contract (Consumer), Security-Design (§1-2) | + Frontend State & Storage Model, Frontend Resilience, Production Debugging & Error Tracking, Security-Design (§1-4) |
| GATE-1 | Constitution Part 2 finalized — all scopes |||
| /validate | validate.md — all scopes |||
| /analyze | analyze.md — all scopes |||
| /clarify | clarify.md — all scopes |||
| /plan-arch | arch.md + plan.md (+ refine the scope-scaled docs above) — all scopes |||
| /plan-hld | hld.md + plan.md — all scopes |||
| /plan-lld | ❌ | lld.md | lld.md |
| /plan-adr | ❌ | ADRs (also fills arch.md §4) | ADRs (also fills arch.md §4) |
| /task | stories.md, tasks.md, jira CSV — all scopes |||
| /implement | code + tests | + qa_cases, runbook | + qa_cases, runbook |
| /release | release.md — all scopes |||

---

## Quick Start

```bash
unzip sdd-frontend-spa-v2.zip -d my-app
cd my-app
git init
# Write .specify/contexts/my-feature.md
# Fill .specify/manifest.yml (4 fields)
# Fill .specify/memory/roles.yml (RACI owners — optional but recommended)
claude    # Claude Code Desktop — type /start, then /specify, /clarify, etc.
# OR open VS Code + Copilot Chat — type /specify, /clarify, etc.
```

Run `/start` (Claude Code) or follow Step 0 (Copilot) from PROMPT-GUIDE.md →
then run the 11 commands as native slash commands (no copy/paste needed —
see "Claude Code Native Slash Commands" in PROMPT-GUIDE.md).

---

## Read Next

| File | Purpose |
|---|---|
| GETTING-STARTED.md | Steps to first run |
| PROMPT-GUIDE.md | All 11 command prompts — copy-paste ready |
| HOW-TO-USE.md | Scope presets + command table |
| SDLC-COMPLETE-GUIDE.md | Full lifecycle reference + checklist |
| CHANGE-GUIDE.md | Making changes later |
| docs/SUMMARY-GUIDE.md | How summaries work |
| IMPROVEMENT-BACKLOG.md | Deferred Phase-3 improvements |
