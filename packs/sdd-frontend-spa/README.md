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

## Virtual Team

Your SDD project comes with a named team. Address them directly in any AI tool:

| Name | Role | Say their name for… |
|---|---|---|
| **Maya** | Business Analyst | BRD · Use Cases · Validate · Context · Change Request |
| **Rex** | Requirements Engineer | SRD · Clarify |
| **Ava** | Software Architect | Analyze · Design · Security · API Spec · Data Model |
| **Leo** | Lead Developer | LLD · Implement · Pre-review · Bug fix |
| **Kai** | Engineering Manager | Tasks · Stories · Export to Jira |
| **Quinn** | QA Lead | Spec quality checklist |
| **Riley** | Release Manager | Release planning and go-live |
| **Morgan** | Delivery Manager | Full pipeline (`/orchestrate`) |

**Three ways to invoke — all work in all AI tools:**
```
/maya                                    ← slash command (Claude Code + Copilot)
Maya, create BRD for the payment feature ← natural language (any AI tool)
Hey Ava, I need a design for auth        ← conversational (any AI tool)
```

---

## Quick Start

```bash
# Recommended: use the CLI
pip install sddflow
sdd init                # interactive: project name, scope, AI tool — copies pack automatically

# OR: manual setup
unzip sdd-frontend-spa.zip -d my-project
cd my-project
git init
# Write .specify/contexts/my-feature.md  (or run /create-context)
# Fill .specify/manifest.yml (4 fields)

# Then start your AI tool
claude                  # Claude Code: type /specify
# OR open VS Code + GitHub Copilot Chat: type /specify
```

---

## Setup — 3 Files

### 1. contexts/{feature}.md — Your project description (15-30 min)
Must include a Tech Stack section:
```markdown
## Tech Stack
| Concern | Choice |
|---|---|
| Language | TypeScript |
| Framework | React 18 |
| State | Redux Toolkit |
| Build | Vite |
| Testing | Vitest + RTL |
```
Not confident writing this? Run `/create-context` — paste any rough notes
and the agent drafts it with you.

### 2. manifest.yml — 4 required fields
```yaml
project:
  name: "Your App"
  scope: "pilot"       # pilot | mvp | full
  feature: "your-feature"
  context_file: "your-feature.md"

reading_mode: "auto"     # auto | summary | full
                         # Set "full" for richer quality at higher token cost
```

### 3. constitution.md Part 2 — Generated (DRAFT) by /specify, finalized by you
Agent reads your context → fills Tech Stack + Principles + Rules as a DRAFT.
You review every row and say "Constitution Part 2 finalized" (GATE-1).

---

## Command Flow

### SPECIFY — 5 Sub-Commands

| Command | What it generates | Gate |
|---|---|---|
| `/specify` | Constitution Part 2 (DRAFT) | — |
| `/specify-brd` | Business Requirements Document | GATE-1 passed |
| `/specify-uc` | Use Case Specification (Actors + UC-NNN with MP/AP/EP) | BRD approved |
| `/specify-srd` | Software Requirements Document | Use Cases approved |
| `/specify-doc {name}` | Extended docs (security, data-model, resilience…) | SRD approved |

### PLAN — 2 Sub-Commands

| Command | What it generates | Scope |
|---|---|---|
| `/plan-design` | Architecture + Diagrams + API Design + ADRs | all scopes |
| `/plan-lld` | Detailed class/sequence design | mvp+ only |

### Orchestrated Pipeline
Run `/orchestrate` to drive the full pipeline from a single command.
Pauses at every human gate. Supports `--list`, `--from STEP`, `--to STEP`.

### Full Command Order

```
/specify → [GATE-1] → /specify-brd → /specify-uc → /specify-srd
→ /specify-doc {name}... → /checklist (mandatory mvp+, optional pilot)
→ /validate → /analyze → /clarify → /plan-design
→ /plan-lld (mvp+) → /task → /implement → /release
```

#### Pilot (shorter path)
```
/specify → [GATE-1] → /specify-brd → /specify-uc → /specify-srd
→ /checklist (optional) → /validate → /analyze → /clarify
→ /plan-design → /task → /implement → /release
```

#### MVP+ (full path)
```
/specify → [GATE-1] → /specify-brd → /specify-uc → /specify-srd
→ /specify-doc security → /specify-doc component-spec → /specify-doc ux-flow
→ /checklist (mandatory) → /validate → /analyze → /clarify
→ /plan-design → /plan-lld → /task → /implement → /release
```

---

## Document Inventory by Scope

| Command | Pilot | MVP | Full |
|---|---|---|---|
| `/specify` | Constitution Part 2 | same | same |
| `/specify-brd` | BRD | same | same |
| `/specify-uc` | Use Cases | same | same |
| `/specify-srd` | SRD + Security-Design §1 | + §1-2 | + §1-4 |
| `/specify-doc` | security | + component-spec, ux-flow | + data-model, resilience, investigation |
| `/checklist` | Optional | Mandatory | Mandatory |
| `/validate` | Validation report | same | same |
| `/analyze` | Analysis report | same | same |
| `/clarify` | Clarification report | same | same |
| `/plan-design` | Architecture + API Design + ADRs | same | same |
| `/plan-lld` | ❌ | LLD | LLD |
| `/task` | Stories + Tasks + Jira | + QA test cases | + QA test cases |
| `/implement` | Code + tests | + Runbook | + Runbook + OpenAPI |
| `/release` | Release plan | same | same |

---

## Key Gates

| Gate | What it guards |
|---|---|
| **GATE-1** | Constitution Part 2 finalized — blocks everything after /specify |
| **/checklist** | Spec quality (mandatory mvp+) — catches unmeasured NFRs, missing acceptance scenarios |
| **/validate** | Business sign-off on BRD + Use Cases + SRD |
| **AI-8** | No unresolved [ASSUMPTION-NNN] before /plan-design |
| **PR Contract** | Estimate → SPLIT if > max lines → files + lines + "PR ready" |

---

## Upgrading Scope

To upgrade `pilot → mvp` or `mvp → full`:
1. Update `manifest.yml` → `scope: mvp` (or `full`)
2. Generate newly required docs: `/specify-doc {name}` for each
3. Run `/plan-lld` if upgrading from pilot
4. Append `CHG-NNN` tasks to `tasks.md`

---

## Read Next

| File | Purpose |
|---|---|
| `QUICKSTART.md` | Steps to first run |
| `.specify/memory/constitution.md` | Universal rules + your tech stack |
| `.specify/memory/roles.yml` | RACI — fill in reviewer names |
| `.specify/contexts/CONTEXT-GUIDE.md` | How to write a good context file |
| `docs/SUMMARY-GUIDE.md` | How AI-2 summary-first reading works |
| `CHANGELOG.md` | Version history |
