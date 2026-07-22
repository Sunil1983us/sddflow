# How To Use — SDD Frontend SPA

---

No `.specify/contexts/{feature}.md` yet? Run `/create-context` first —
paste rough notes and the agent drafts context.md with you, instead of
writing it by hand. See `.specify/contexts/CONTEXT-GUIDE.md`.

---

## This Pack — sdd-frontend-spa

**For:** React, Vue, Angular, and Svelte single-page applications

This pack adds component-level and UX flow design documents and enforces accessibility, component architecture, and SPA-specific tech concerns. It does not include backend or server-side concerns.

### Pack-Specific Templates

Included in addition to the 28 core spec templates:

| Template | Use it for |
|---|---|
| `component-spec-template.md` | UI component specification — props, state, events, slots, accessibility |
| `ux-flow-template.md` | User journey flows and screen-to-screen transitions |

### Extended Documents Available

| Document | Command | Scope |
|---|---|---|
| Security Design | `/specify-doc security` | All scopes |
| Component Spec | `/specify-doc component-spec` | mvp+ |
| UX Flow | `/specify-doc ux-flow` | mvp+ |
| Data Model (living — `.specify/service/data-model.md`) | `/specify-doc data-model` | mvp+ |
| Resilience Plan | `/specify-doc resilience` | full only |
| Technical Investigation | `/specify-doc investigation` | full only |

### SPA-Specific Rules

The following rules are added to `constitution.md Never Do` by `/specify`:

- Never call an API directly from a component — always go through a service layer
- Never use inline styles — use the project's styling solution
- Never ship a component without an axe-core accessibility check
- Never use `any` type in TypeScript
- Never log sensitive data to the console in production

> Need a different pack? Run `sdd init --pack <name>` to switch. Use `sdd-universal` if you're unsure which pack fits your project.

---

## Using With Your AI Tool

The SDD pack works with any AI coding assistant. How you invoke a command depends on your tool:

| AI Tool | How to run a command |
|---|---|
| **Claude Code** | Open the project folder in Claude Code and type the slash command, e.g. `/specify` |
| **GitHub Copilot** | Open VS Code with Copilot Chat — type the slash command, e.g. `/specify` |
| **Cursor** | In Cursor chat, type: `Read and follow .github/prompts/specify.prompt.md exactly` |
| **Windsurf** | In Windsurf chat, type: `Run specify` |
| **Other / not sure** | Open `.github/prompts/specify.prompt.md` and copy-paste its contents into your AI tool |

### Where Each Tool Reads Its Instructions

| AI Tool | Instruction source |
|---|---|
| Claude Code | `.claude/commands/{cmd}.md` — loaded automatically as native slash commands |
| GitHub Copilot | `.github/copilot-instructions.md` + `.github/prompts/{cmd}.prompt.md` |
| Cursor / Windsurf / Other | `.github/prompts/{cmd}.prompt.md` — reference or paste into chat |

> Your selected AI tool is saved in `.specify/manifest.yml` as `ai_tool` (set during `sdd init`). You can change it anytime by editing that field — all prompt files in `.github/prompts/` work with any tool.

### Switching AI Tool Mid-Project

1. Edit `manifest.yml` → update `ai_tool:` to your new tool
2. All `.github/prompts/` files remain available — any tool can reference them
3. Claude Code `.claude/commands/` slash commands remain available if you return to Claude Code

---

### Virtual Team — Address by Name

You can address any team member by name — no slash command needed.
They read your message, check the pipeline state, and run the right step automatically.

| Name | Role | Handles |
|---|---|---|
| **Maya** | Business Analyst | BRD, Use Cases, Validate, Context, Change Request |
| **Rex** | Requirements Engineer | SRD, Clarify |
| **Ava** | Software Architect | Analyze, Design, Security, API Spec, Data Model, Resilience |
| **Leo** | Lead Developer | LLD, Implement, Pre-review, Address review, Bug assess, Bug fix |
| **Kai** | Engineering Manager | Tasks, Stories, Export to Jira / GitHub Issues |
| **Quinn** | QA Lead | Spec quality checklist |
| **Riley** | Release Manager | Release planning and go-live |
| **Morgan** | Delivery Manager | Full pipeline orchestration, progressive Jira push |

**Works three ways — all equivalent:**

```
/maya                                   ← slash command (Claude Code + Copilot)
Maya, create BRD for payments           ← natural language (any AI tool)
"Hey Ava, I need a design for auth"     ← conversational (any AI tool)
```

**Routing rule:** When a name appears at the start of a message or is addressed
directly (e.g. "Maya, …" / "Hey Ava" / "Can Rex clarify"), read and follow
`.github/prompts/{name}.prompt.md` exactly. The prompt file handles context
detection and routes to the correct underlying command automatically.

---

## Command Flow

| Command | What It Does | Scope |
|---|---|---|
| `/specify` | Constitution Part 2 (DRAFT) only | Always |
| **GATE-1** | You review + finalize constitution Part 2 (manual) | Always |
| `/specify-brd` | Business Requirements Document | Always |
| `/specify-uc` | Use Case Specification (Actors + MP/AP/EP) | Always |
| `/specify-srd` | Software Requirements Document | Always |
| `/specify-doc {name}` | Extended docs (security, data-model, resilience…) | Scope-dependent |
| `/checklist` | Spec quality gate | Mandatory mvp+, optional pilot |
| `/validate` | Business sign-off on BRD + Use Cases + SRD | Always |
| `/analyze` | Risks + complexity + distributed systems check | Always |
| `/clarify` | Questions → you answer → update spec | Always |
| `/plan-design` | Architecture + Diagrams + API Design + ADRs | Always |
| `/plan-lld` | LLD + class/sequence diagrams | MVP+ only |
| `/task` | Feature → Story → Task + Jira CSV | Always |
| `/implement` | Code one task at a time | Always |
| `/release` | UAT + deployment plan + go-live gate | Always |
| `/orchestrate` | Drive full pipeline automatically — pauses at every human gate | Optional |
| `/jira-push` | Push Epic/Story/Task/CHG to Jira progressively at each gate | Optional |

---

## Command Flow Diagrams

### Pilot
```
/specify → [GATE-1] → /specify-brd → /specify-uc → /specify-srd
→ /checklist (optional) → /validate → /analyze → /clarify
→ /plan-design → /task → /implement → /release
```

### MVP+
```
/specify → [GATE-1] → /specify-brd → /specify-uc → /specify-srd
→ /specify-doc security → /specify-doc data-model
→ /checklist (mandatory) → /validate → /analyze → /clarify
→ /plan-design → /plan-lld → /task → /implement → /release
```

---

## Command Reference — Step by Step

A detailed guide for every command: what it is, exactly when to run it, what it produces, and what you do next.

---

### Phase 0 — Setup (before any command)

#### `/create-context` — Optional pre-phase

**What:** You paste informal notes (emails, Confluence pages, rough bullets); the agent drafts a structured `context.md`. For Endpoints and NFRs it also proposes scope-appropriate starting defaults (marked `SUGGESTED DEFAULT`) instead of leaving them blank, then lists a plain-language review checklist split into "confirm or edit these defaults" and "still need your input." You iterate until complete.

Before drafting, a **Feature Size Check** (Step 1.5) looks for signs your notes actually describe 2+ independently-shippable features rather than one. If found, it asks whether to build them one at a time — the chosen feature proceeds as normal, and every other feature's raw notes are saved to `.specify/contexts/{slug}.raw.md` for a later `/create-context` run.

**When to run:** Before `/specify`, only if you do not already have a `.specify/contexts/{feature}.md`.

**Produces:** `.specify/contexts/{feature}.md`

**You do next:** Review the draft — confirm or override the suggested Endpoints/NFR defaults, correct any wrong tech choices, fill in any [MISSING] items, add business rules the agent didn't catch. Then fill `manifest.yml` and run `/specify`.

**Skip if:** You already have a well-structured context file.

---

#### Initializing a project — `sdd init` (recommended) or `setup.sh`

**Option 1 — `sdd init` (recommended, requires the CLI):**

Install the CLI once:
```bash
pip install sddflow          # Python (any platform)
# OR
# (Node.js CLI: from source only — see the framework repo's cli/README.md;
#  the sdd-init package on npm is an unrelated third-party project)
```

Then run in your project folder:
```bash
sdd init                      # interactive — prompts for name, feature, scope, type
sdd init -p "My API" -f "payments" -s mvp   # non-interactive
```

`sdd init` auto-detects your project type, fills `manifest.yml` (including `sdd_version`), creates the context placeholder, and creates the feature output directory.

**Option 2 — `bash setup.sh` (no install needed):**

Every pack ships with a shell script as a zero-dependency fallback:
```bash
bash setup.sh                 # Mac / Linux — interactive
.\setup.ps1                   # Windows — interactive
bash setup.sh --project "My API" --feature "payments" --scope mvp  # non-interactive
```

Does the same as `sdd init` except it does not set `sdd_version` (set by the CLI) and does not auto-detect project type.

**When:** Once, immediately after copying the pack into your project. Before running `/specify`.

---

#### Jira/Confluence integration — `sdd config init` (optional)

Skip this if chat-mode approvals are fine for now — nothing else in this
pack requires it, and you can run it later at any point, not just here.

```bash
sdd config init
```

Interactive wizard: Atlassian base URL, auth mode, and credential storage
(OS keychain recommended), then optionally scaffolds
`.specify/integrations.yml` (Jira project key, Confluence space key,
parent page ID) from this pack's own `.specify/integrations.yml.example`
— every section it documents (reviewer routing, diagrams, PR automation,
...) is included, most left commented out until you need them.

Verify it actually connects:
```bash
sdd config test
```

**When:** Any time before your first `sdd review submit` / `sdd jira push` / `sdd confluence push` — not required to run `/specify`.

---

### Phase 1 — SPECIFY

#### `/specify` — Constitution Part 2 (DRAFT)

**What:** Reads your context file and extracts all tech decisions. Fills the Tech Stack table, Core Principles, Domain Rules, and Never Do in `constitution.md` Part 2 as a DRAFT. Lists any `[MISSING — ask user]` rows as Open Items.

**When to run:** After `manifest.yml` is filled and `context.md` exists.

**Prerequisites:** `manifest.yml` (4 fields) + `.specify/contexts/{feature}.md`

**Produces:** Updated `constitution.md` Part 2 (DRAFT status)

**You do next:** See GATE-1 below — review every row before anything else can run.

**Tip:** A richer context produces a more accurate constitution draft. The more detail in your tech stack, NFRs, and business rules sections, the fewer `[MISSING]` rows you will see.

---

#### GATE-1 — Finalize Constitution Part 2 (manual, blocking)

**What:** You personally review the DRAFT constitution Part 2 that `/specify` produced. This is the single most important human step — the constitution governs every document and every line of code that follows.

**When:** Immediately after `/specify` completes. No other command may run until this gate passes.

**Steps:**
1. Open `.specify/memory/constitution.md` → scroll to Part 2
2. Review every row: Tech Stack, Core Principles, Domain Rules, Never Do
3. Resolve every `[MISSING — ask user]` marker — fill in the correct value
4. Edit anything incorrect directly — your manual edits are AUTHORITATIVE and override what the agent generated
5. Tell the agent: **"Constitution Part 2 finalized"**

**Gate unlocks:** `/specify-brd` (and all subsequent commands)

**A later `/specify` re-run** will propose a Constitution Amendment Summary (row diffs + version bump) and wait for your confirmation — it will never silently overwrite a finalized Part 2.

---

#### `/specify-brd` — Business Requirements Document

**What:** Writes the Business Requirements Document. Captures business objectives (BO-NNN), business requirements (BR-NNN), assumptions, and out-of-scope items. Traces every BR to a BO.

**When to run:** After GATE-1 is passed.

**Prerequisite:** `"Constitution Part 2 finalized"` confirmed by you.

**Produces:** `.specify/features/{feature}/brd.md` + `brd.summary.md`

**You do next:** Share `brd.md` with the Product Owner for review. When approved, tell the agent "BRD approved" to unlock `/specify-uc`. If changes are needed: edit the document directly, then re-share with the reviewer.

**Reviewer:** Product Owner

---

#### `/specify-uc` — Use Case Specification

**What:** Writes the Use Case Specification. Identifies all actors (ACT-NNN), defines use cases (UC-NNN), and documents the Main Path, Alternative Paths (AP-NNN-X), and Exception Paths (EP-NNN-X) for each. An actor already defined in another feature's `use-cases.md` (same real-world role) is reused, not re-derived — its description carries over, only the local ACT-NNN numbering is fresh.

**When to run:** After BRD is approved.

**Prerequisite:** BRD approval + `brd.summary.md` exists.

**Produces:** `.specify/features/{feature}/use-cases.md` + `use-cases.summary.md`

**You do next:** Share with Business Analyst + Product Owner. When approved, tell the agent "Use Cases approved" to unlock `/specify-srd`.

**Reviewer:** Business Analyst + Product Owner

---

#### `/specify-srd` — Software Requirements Document

**What:** Writes the Software Requirements Document. Defines Functional Requirements (FR-NNN), Non-Functional Requirements (NFR-NNN), acceptance scenarios for every FR, and Security Design §1 (threat model basics). The first feature to reach this command fills constitution.md's App NFR Baseline (Load Time/Bundle Size/Interactivity/Accessibility); every later feature references that baseline instead of restating the same numbers, and only adds its own NFR-NNN row for something genuinely different.

**When to run:** After Use Cases are approved.

**Prerequisite:** Use Cases approval + `use-cases.summary.md` exists.

**Produces:** `.specify/features/{feature}/srd.md` + `srd.summary.md`

**You do next:** Share with Business Analyst. When approved, run scope-dependent `/specify-doc` commands (see below), then `/checklist`.

**Reviewer:** Business Analyst

---

#### `/specify-doc {name}` — Extended Documents

**What:** Writes one extended specification document per invocation. Which documents to run depends on scope:

| Scope | Documents to generate |
|---|---|
| pilot | None required (Security Design §1 already in SRD) |
| mvp | `/specify-doc security` → `/specify-doc component-spec` → `/specify-doc ux-flow` → `/specify-doc data-model` |
| full | `/specify-doc security` → `/specify-doc component-spec` → `/specify-doc ux-flow` → `/specify-doc data-model` → `/specify-doc resilience` → `/specify-doc investigation` |

**When to run:** After SRD is approved, one at a time.

**Prerequisites:** SRD approval + `srd.summary.md` exists.

**Available document names:**
- `security` → `security-design.md` (STRIDE threat model, §1-2 for mvp, §1-4 for full)
- `component-spec` → `component-spec.md` (component props, state, events, accessibility) — **mvp+** (its "Shared Components Used" section is living, at `.specify/service/component-library.md`)
- `ux-flow` → `ux-flow.md` (user journey flows, screen transitions) — **mvp+**
- `data-model` → `.specify/service/data-model.md` (client data structures, API response shapes — living, app-level) — **mvp+**
- `resilience` → `resilience.md` (error boundaries, retry, offline handling) — **full only**
- `investigation` → `investigation.md` (spike / technical investigation) — **full only**

**You do next:** Review each doc. The agent presents it; you approve or request changes before generating the next one.

---

#### `/checklist` — Spec Quality Gate

**What:** Audits all spec documents for quality issues before business sign-off. Catches unmeasured NFRs, FRs without acceptance scenarios, vague adjectives (fast/scalable/secure without a number), terminology drift, and missing out-of-scope items.

**When to run:** After all `/specify-doc` commands are done, before `/validate`.

**Scope rule:** Mandatory for mvp and full. Optional for pilot (recommended even then).

**Produces:** `.specify/features/{feature}/checklists/{feature}-spec-quality.md`

**Finding severity:**
- **CRITICAL** — block `/validate` until resolved: unresolved [NEEDS CLARIFICATION], unmeasured NFRs, FRs without acceptance scenarios
- **HIGH** — resolve in `/clarify`: vague performance/security attributes, UCs without Independent Test
- **MEDIUM** — address before `/plan-design`: terminology drift, missing out-of-scope items

**You do next:** Fix all CRITICAL items (edit the relevant spec docs directly, then re-run `/checklist`). HIGH and MEDIUM items carry into `/clarify`. When zero CRITICAL items remain, `/validate` can run.

---

### Phase 2 — VALIDATE

#### `/validate` — Business Sign-Off

**What:** Formal business sign-off audit on BRD + Use Cases + SRD. Checks traceability (BR → FR, FR → UC), measures NFRs, confirms acceptance criteria exist for every FR. Produces a sign-off report with APPROVED / BLOCKED status.

**When to run:** After GATE-1 passed, all spec docs approved, and `/checklist` has zero CRITICAL items.

**Position in pipeline:** Runs once after SPECIFY phase; gates ANALYZE. It is **not** repeatable at arbitrary phases — it runs at this exact position in the sequence.

**Produces:** `.specify/features/{feature}/validate.md`

**You do next:** If BLOCKED → read the blockers, fix the relevant spec docs, re-run `/validate`. If APPROVED → `/analyze` can run.

**Reviewer:** Product Owner + Business Analyst

**Jira/Confluence:** optional — see "Document Review Workflow" below (also covers `push-questions`/`pull-answers` for collecting answers to blocking `[NEEDS CLARIFICATION-NNN]` items before the document is even submitted for review).

---

### Phase 3 — ANALYZE

#### `/analyze` — Technical Risk and Complexity Audit

**What:** Principal Architect read-only audit of all spec documents. Does NOT generate code or change any spec. Produces a 9-section analysis report covering:

1. Executive Summary (overall complexity: LOW / MEDIUM / HIGH)
2. Risk Register (R-NNN — likelihood × impact, linked to FR/NFR)
3. Dependency Map (blocking vs non-blocking, owner, contingency)
4. Complexity Assessment (per area, likely SPLIT flags)
5. NFR Impact Analysis (what each NFR forces in design)
6. Unknowns — Spike Work Needed
7. Recommendation (approach + items for /clarify)
8. Consistency Findings (CF-NNN — cross-artifact conflicts and gaps)
9. Distributed Systems Consistency (race conditions, idempotency, saga, eventual consistency)

**When to run:** After `/validate` is approved. Runs **once** at this position — it is not a command you re-run at arbitrary phases.

**Produces:** `.specify/features/{feature}/analyze.md`

**You do next:** Review `analyze.md` with the tech lead. CRITICAL CF findings (constitution conflicts, FRs with zero UC coverage) must be resolved before `/clarify` can run. Note R-NNN risks — they carry into `/task` as mitigating task assignments.

**Reviewer:** Tech Lead (accountable), Architect + Security Officer (consulted)

**Jira/Confluence:** optional — see "Document Review Workflow" below.

---

### Phase 4 — CLARIFY

#### `/clarify` — Resolve Ambiguities Before Design

**What:** Agent presents all open questions from the analysis — grouped as Ambiguities (AMB-NNN), Specification Gaps (GAP-NNN), Assumptions (ASM-NNN), and Open Questions (OQ-NNN). You answer each one. Spec documents are updated with the answers.

**When to run:** After `analyze.md` is reviewed and CRITICAL CF findings are resolved.

**Position in pipeline:** Runs **once** at this position. It is not a command you re-run at arbitrary phases — all questions must be resolved here before design can proceed.

**How it works:**
1. Agent reads `analyze.md` and all spec summaries
2. Presents a numbered list of open items
3. You answer each item (type the answer inline or say "Skip" to defer)
4. Agent updates the relevant spec docs with your answers
5. All items reach RESOLVED status
6. `/clarify` session is complete → `clarify.md` written

**Produces:** `.specify/features/{feature}/clarify.md`

**You do next:** Confirm all items show RESOLVED. Ensure no `[ASSUMPTION-NNN]` markers remain in any spec doc (AI-8 gate). Then `/plan-design` can run.

**Reviewer:** Product Owner (accountable), Business Analyst (consulted)

**Jira/Confluence:** optional — see "Document Review Workflow" below.

---

### Phase 5 — PLAN

#### `/plan-design` — Architecture + API Design + ADRs

**What:** Unified design document. Generates:
- System architecture (component-based / feature-folder / layered — derived from context) — established once by the first feature; later features reference it ("unchanged from {feature}, see there") instead of re-deriving the same pattern/layers/cross-cutting concerns
- Component / service decomposition
- Sequence diagrams for all critical flows (including exception paths)
- API design (§3): the API contract this feature consumes (endpoints, request/response schemas, error codes) — a consumer-side view only, since this pack does not own the API; nothing here is a living document
- Architecture Decision Records (ADR-NNN) — one per major technology decision

**When to run:** After `clarify.md` all RESOLVED and no unresolved `[ASSUMPTION-NNN]` in any spec doc.

**Gate (AI-8):** The agent checks every spec doc for `[ASSUMPTION-NNN]` markers before proceeding. Any unresolved assumption blocks this command.

**Produces:** `.specify/features/{feature}/design.md`

**You do next:** Tech lead + architect + stakeholders review. When approved, if pilot scope → go to `/task`. If mvp+ → run `/plan-lld` first.

**Reviewer:** Tech Lead + Architect + Stakeholders

**Replaces:** The former `/plan-arch`, `/plan-hld`, and `/plan-adr` commands all redirect to `/plan-design` for backwards compatibility.

---

#### `/plan-lld` — Low-Level Design (mvp+ only)

**What:** Detailed class and sequence diagrams; key class designs with methods, fields, and relationships; package structure; integration contracts.

**When to run:** After `design.md` is approved. **SKIP if pilot scope** — the agent states skip reason and proceeds to `/task`.

**Prerequisite:** `design.md` approved.

**Produces:** `.specify/features/{feature}/lld.md`

**You do next:** Senior developer reviews. When approved, run `/task`.

**Reviewer:** Senior Developer

---

### Phase 6 — TASK

#### `/task` — Stories + Tasks + Jira Export

**What:** Breaks the design into deliverable units:
- **User stories** (story-NNN) with acceptance criteria, story points, sprint assignments
- **Tasks** (TASK-NNN) with effort estimates and PR split guidance (flags tasks likely to exceed `max_lines_per_pr`)
- **Jira-ready CSV** for immediate import
- **Risk → Task traceability** — each R-NNN risk from `/analyze` is assigned mitigating TASK-NNN

**When to run:** After `design.md` approved (+ `lld.md` approved if mvp+).

**Produces:**
- `.specify/features/{feature}/stories.md`
- `.specify/features/{feature}/tasks.md`
- `.specify/features/{feature}/jira-export.csv`

**You do next:** Product Owner + dev team review. Calibrate story points against your team's actual velocity — the agent's estimates are a starting baseline. When approved, say "Tasks approved" to unlock `/implement`.

**Reviewer:** Product Owner + dev team (QA lead consulted)

**Important:** Story points are AI estimates. Always calibrate against your team's historical velocity before sprint planning.

---

### Phase 7 — IMPLEMENT

#### `/implement [TASK-NNN]` — Code One Task at a Time

**What:** Writes production code + paired tests for a single task. Respects PR size limits (splits into A/B/C if the task would exceed `max_lines_per_pr`). Ends with "PR ready" (github mode) or runs checks locally and ends with "Task accepted" (local mode).

**When to run:** After Tasks approved. Run one task at a time in TASK-NNN order.

**Prerequisites:** `tasks.md` approved + `constitution.md` (full read, always).

**Per-task flow:**
1. `/implement TASK-NNN` — agent writes code + tests, commits
2. `/pre-review TASK-NNN` — agent self-reviews the diff (correctness, security, quality, performance), presents a numbered findings checklist; you pick which to fix; agent commits fixes
3. `sdd pr create --task TASK-NNN` — creates PR (pre-review summary auto-included in PR body)
4. Human reviewer approves or adds inline comments
5. If changes requested: `/address-review PR-NNN` — agent shows unresolved threads as a checklist; you pick which to fix; agent pushes fixes and requests re-review
6. PR approved → merge → TASK-NNN complete

**Produces:** Code + tests committed, PR created

**Repeat for every TASK-NNN until all tasks are done.**

**Local mode (`workflow_mode: local`):** Agent runs build/test/coverage/lint locally, reports ✅/❌ per check, ends with "Task accepted". No PR created — you approve and say "go" directly.

---

### Phase 8 — RELEASE

#### `/release` — UAT Plan + Deployment + Go-Live Gate

**What:** Writes the release document:
- UAT test plan (scenarios, expected results, pass/fail criteria)
- Deployment runbook (step-by-step deployment instructions)
- Go-live gate checklist (all DoD items verified, monitoring live, rollback plan confirmed)
- Business Owner sign-off record

**When to run:** After ALL tasks complete — every PR approved and merged (github mode), or every task "Task accepted" (local mode).

**Gate:** `/release` will refuse to run if any task is not yet "PR ready + merged" (github) or "Task accepted" (local).

**Produces:** `.specify/features/{feature}/release.md`

**You do next:** QA lead + Product Owner + Tech Lead + DevOps sign off on the go-live checklist. Confirm every gate item. Deploy.

**Reviewer:** QA Lead (responsible), Product Owner (accountable), Tech Lead + DevOps/SRE (consulted)

---

### Optional and Utility Commands

#### `/orchestrate` — Run the Full Pipeline Automatically

Drives the entire pipeline in one command, pausing at every human gate for your input.

```
/orchestrate                    # run full pipeline
/orchestrate --list             # show pipeline status dashboard
/orchestrate --from validate    # resume from /validate
/orchestrate --to task          # stop after /task (don't implement yet)
```

Use when you want to generate all documents in a single session with minimal interruption.

---

#### `/bug-fix [description]` — Fix a Bug With Traceability

Assesses the bug, identifies the affected TASK-NNN and story-NNN, writes the fix + paired test, creates a `FIX-NNN` task in `tasks.md`, and follows the same PR flow as `/implement`.

#### `/bug-assess [description]` — Assess Before Fixing

Read-only: evaluates the bug's impact (which FRs/NFRs are threatened, blast radius, root cause hypothesis). Use before `/bug-fix` for complex bugs.

#### `/change [description]` — Controlled Scope Change

Initiates a Constitution Amendment. Writes a Constitution Amendment Summary (row diffs + version bump), waits for your review, then updates the affected spec docs and appends `CHG-NNN` tasks to `tasks.md`.

#### `/pre-review [TASK-NNN]` — AI Self-Review

Agent analyses the diff for the completed task: correctness, security, quality, performance. Presents a numbered checklist. You pick which findings to fix. Run this before creating a PR.

#### `/address-review [PR-NNN]` — Resolve Reviewer Comments

Agent reads all unresolved comment threads on the PR, presents them as a numbered checklist, applies selected fixes, pushes, replies to threads, and requests re-review.

#### `/submit-review --doc {name}` / `/check-review --doc {name}` — Review Workflow

Slash commands that help manage the document review cycle — present the agent with reviewer comments and let it update the document.

Without the CLI, share documents manually with reviewers and tell the agent the outcome (e.g. "BRD approved").

#### `/taskstoissues` — Export Tasks and Stories to GitHub Issues

Run as **Kai**. Reads `tasks.md` and `stories.md` and produces `tasks-to-issues.md` (GitHub-flavored markdown, one issue per task/story) plus `gh-create-issues.sh` (bulk-creates them via the `gh` CLI). Use once tasks/stories are approved and you want to work the backlog from GitHub Issues instead of `tasks.md`.

---

## Jira & Confluence Integration

The `sdd` CLI connects your spec documents and tasks directly to your Atlassian workspace. This is optional — without it, share documents manually and tell the agent the review outcome.

### One-Time Setup

**Step 1 — Configure credentials:**
```bash
sdd config init
```
This interactive wizard asks for your Atlassian base URL, auth mode, and — importantly — how to store the credential:

- **System keychain (recommended)** — the wizard asks for your token directly and saves it via your OS's secure credential store (macOS Keychain / Windows Credential Manager / Linux Secret Service). Works immediately in any terminal or AI tool on this machine — nothing to export, nothing to configure per-shell.
- **Environment variable** — the wizard only asks for an env var *name* (never the value); you export it yourself. This only works in shells where you've actually run that export — if you're driving `sdd` from an AI coding tool, its subprocess shell often doesn't inherit an env var you set in a different terminal tab, which shows up as "can't connect to Jira/Confluence" even though the token itself is fine.

Either way, `~/.sdd/config.yml` never contains a plaintext secret. Optionally creates `.specify/integrations.yml` for this project too.

**Step 2 — (environment variable option only) export your token:**
```bash
# Jira Cloud (basic auth — email + API token)
export JIRA_API_TOKEN=your-api-token

# Jira Server / Data Center (Personal Access Token)
export JIRA_PAT=your-personal-access-token
```
Get your API token: Atlassian account → Security → API tokens → Create API token. Skip this step entirely if you chose keychain storage above — the wizard already asked for the token and stored it. To rotate a keychain-stored token later: `sdd config set-secret --profile {name}`.

**Step 3 — Test the connection:**
```bash
sdd config test
```
Expected output:
```
  ✓  Jira       — connected as Jane Smith
  ✓  Confluence — connected as Jane Smith
```
A red ✗ means the env var is missing, the base URL is wrong, or the token is expired.

**Step 4 — Discover your Jira custom field IDs:**
```bash
sdd config fields --project MYPROJ
```
Lists every custom field in your Jira instance. Find your `story_points` field (commonly `customfield_10016` on Jira Cloud) and update `.specify/integrations.yml → jira.custom_fields.story_points`.

---

### Jira — Push Stories and Tasks

After `/task` generates `stories.md` and `tasks.md`:
```bash
sdd jira push                    # create/update Feature → Story → Task in Jira
sdd jira push --dry-run          # preview the plan without calling the API
sdd jira push --feature payments # push a specific feature (default: from manifest.yml)
```
Pushes are idempotent — re-running updates existing issues rather than creating duplicates (keyed on `sdd:{feature}:STORY-001`-style labels, qualified by feature). On a multi-feature project, each feature's Story/Task issues stay distinct even when both features independently number their own stories/tasks starting from 001 — matching the Feature → Story → Task hierarchy: the Feature-level issue is already keyed by feature name (`sdd-feature:{feature}`), and Story/Task labels now are too.

---

### Jira — Progressive Push (`/jira-push`)

`sdd jira push` above pushes everything at once, by default. If you want Jira
issues created earlier — Epic right after BRD approval, Stories after Use
Cases/SRD approval — use `--level`, or the agent's `/jira-push` slash command
(a thin wrapper around the exact same command, with bare-shorthand parsing).
Both work unattended from CI/CD — there's no separate script anymore.

| | `sdd jira push` (no `--level`) | `sdd jira push --level ...` / `/jira-push` |
|---|---|---|
| Config | `.specify/integrations.yml` + `~/.sdd/config.yml` (same for both) |
| Timing | Once, after `/task` | Progressive: Epic → BRD, Story → Use Cases/SRD, Task → `/task`, CHG → `/change` |
| Hierarchy | Full Feature/Epic → Story → Task | Same, one level at a time (plus CHG) |
| Field mapping | `integrations.yml → jira.custom_fields` (`fr_reference`, `moscow_priority`, `story_points`, `acceptance_criteria`, `epic_name` — see `integrations.yml.example`) |

**Setup:** `sdd config init` (or copy `.specify/integrations.yml.example` to `.specify/integrations.yml` and fill in `jira:` — project key, issue types, custom field IDs). Credentials live in `~/.sdd/config.yml`, set up the same way.

**Usage** — bare shorthand or full flag syntax, run as your pipeline advances:
```
/jira-push epic          # after /specify-brd approval
/jira-push story         # after /specify-uc or /specify-srd approval
/jira-push task          # after /task approval
/jira-push chg CR-001    # after /change approval
/jira-push --level all --dry-run   # preview every level before pushing for real
```
Or directly: `sdd jira push --level epic`, etc. Keys created/updated are
tracked in `docs/jira/{feature}/keys.yml` — scoped per feature, same as
`.specify/features/{feature}/`, so two features' progressive Jira exports
never overwrite each other's locally-tracked keys. This file is a
human-readable summary only; it is never read back by `sdd jira push` — parent
links and idempotency are always re-derived live from Jira labels, so a level
can always be pushed on its own, in any order, and still link up correctly.

---

### Confluence — Push Documents

After generating a spec document:
```bash
sdd confluence push --doc brd    # push BRD to Confluence as a formatted page
sdd confluence push --doc srd    # push SRD
sdd confluence push --all        # push all documents listed in integrations.yml page_map
sdd confluence push --doc brd --summary   # push brd.summary.md to its own "... — Summary" page
```
Page titles come from `integrations.yml → confluence.page_map`. Re-running updates the existing page. `--summary` pushes the shorter `.summary.md` (if one exists) to a separate page — the full doc's own page is untouched, so you get both a detailed page and a quick-read one in Confluence.

`page_map` covers every generated doc type by default, not just the phase-gated ones — `qa-testcases`, `tasks`, `checklist`, and the living/service-level docs (`data-model`, `security-design`, `api-spec`, `component-library`) all have an entry, so `sdd confluence push --doc qa-testcases` (for example) works out of the box even though QA test cases have no Jira review gate.

**On a multi-feature project — living docs get ONE page, per-feature docs get one page each.** Living/service-level documents (`data-model`, `security-design`, `api-spec`, `component-library`) always resolve to a single shared page regardless of which feature is active — that's correct, since the underlying document itself is shared. Per-feature documents (`brd`, `use-cases`, `srd`, `design`/`arch`/`hld`/`adr`, `lld`, `validate`, `analyze`, `clarify`, `release`) need `{feature}` in their `page_map` title template to get a separate page per feature — the shipped `integrations.yml.example` already includes it. If your `integrations.yml` predates this and its titles don't have `{feature}`, every feature pushing the same doc type will silently overwrite the same page — add `{feature}` to those entries to fix it.

---

### Document Review Workflow

Reviews work in three modes — **Jira is optional**:

- **chat** (default, zero setup): the reviewer approves in chat; the agent flips
  the document's `Status:` header — the authoritative gate in every mode
- **local**: same, plus `sdd review approve --doc brd --local --by "Product Owner"`
  records an audit trail in `.specify/.local-approvals.yml` — and updates the
  document's existing Confluence page when a `confluence:` section is configured
- **jira**: the full workflow below (needs `jira:` + `confluence:` in
  `integrations.yml`)

See "Document Review Gates — Three Modes" in `CLAUDE.md` for details.

**jira mode** — after generating each spec document, submit it for stakeholder review:

```bash
sdd review submit --doc brd      # push to Confluence + create Jira review story
sdd review check  --doc brd      # poll: exit 0=APPROVED  1=NEEDS_REVISION  2=PENDING
sdd review apply  --doc brd      # re-push after addressing reviewer comments
sdd review status                # dashboard: all documents + their current review state
```

**The Confluence page shows the Jira link + status too.** `submit`/`check`/`apply` prepend a small panel to the top of the page — the ticket key (linked), its live status (Pending review / Needs Revision / Approved), and the assigned reviewer role — refreshed every time one of those commands runs, so a reviewer never has to leave Confluence to see where a document stands. Only shown for docs with a `document_reviews` entry; a doc pushed via `page_map` alone (no Jira gate) gets a plain page.

**`sdd review status` needs Jira configured.** For a status view that works
in **every** review mode (chat, local, or jira), run `sdd dashboard`
instead — a local web UI with pipeline progress, task status, and token
usage per feature, plus Approve/comment buttons that update the same
`Status:` header and `.local-approvals.yml` this section describes. See
`cli-python/README.md` → "sdd dashboard".

**Review sequence is enforced:** BRD must be approved before SRD can be submitted; SRD before design; etc.

**Handling a revision request:**
1. `sdd review check --doc brd` exits 1 (NEEDS_REVISION)
2. Run `/address-review --doc brd` — agent reads comments, proposes updates, you approve
3. `sdd review apply --doc brd` — re-pushes the updated page to Confluence
4. Reviewer re-approves → `sdd review check --doc brd` exits 0 (APPROVED)

**`sdd review apply` works with just one integration configured too** — Confluence-only (no `jira:` section) still re-pushes the page; Jira-only (no `confluence:` section) still posts the "please re-review" comment. It no longer hard-requires both.

Configure reviewers (Jira accountId per document) in `.specify/integrations.yml`. Run `sdd config init` to generate this file interactively, or copy `.specify/integrations.yml.example` and edit it.

**`/validate`, `/analyze`, and `/clarify` can go through this same jira-mode
flow — each is optional individually.** Add `document_reviews.validate`
(and/or `.analyze`, `.clarify`) to `integrations.yml` for whichever of the
three you want routed through Jira/Confluence — they form their own
`validate` phase (Validate → Analyze → Clarify), sequence-gated the same
way BRD → Use Cases → SRD is. Leave any of the three out and it stays
chat-only, no config change needed elsewhere.

**A document can collect answers via Jira/Confluence before it's even
submitted for review.** `validate.md` (and any doc with the same
`[NEEDS CLARIFICATION-NNN]` marker pattern) can be *blocked* on open
questions in its source docs — `/validate`'s own scan lists them. Rather
than waiting for a formal review round, push those specific questions out
now:
```bash
sdd review push-questions --doc validate   # push open items to Jira + Confluence
# reviewer replies as a comment, one line per item:
#   brd:NC-002: 90 days, per data retention policy DR-014
sdd review pull-answers --doc validate     # pull replies, patch the answered markers
```
`push-questions` creates (or updates, if one already exists) **one** Jira
ticket — reusing the same reviewer/ticket `sdd review submit` will use
once the document unblocks, so it evolves in place rather than duplicating.
`pull-answers` reads back replies matching `{doc}:NC-{NNN}: {answer}`,
patches each answered marker directly into its source document (bumping
that document's version), and — if `confluence:` is configured — re-pushes
that document's own Confluence page immediately so it never goes stale.
Safe to call `pull-answers` unconditionally (e.g. every time you re-run
`/validate`) — it's a no-op when there's nothing new.

`clarify.md`'s own open items (AMB/GAP/CON/ASM/OQ/R) work the same way, even though they're tracked by a STATUS TABLE row instead of a `[NEEDS CLARIFICATION-NNN]` marker:
```bash
sdd review push-questions --doc clarify   # push all OPEN items to Jira + Confluence
# reviewer replies as a comment, one line per item:
#   clarify:AMB-001: Intentional split — keep both fields
sdd review pull-answers --doc clarify     # fills {FILL...}, flips each STATUS
                                           # TABLE row (RESOLVED/CONFIRMED/DECIDED/
                                           # CORRECTED per item type), re-pushes Confluence
```

---

## Scope Presets

### Pilot — Demo / Proof of Concept
```yaml
scope: "pilot"
# /specify-doc: none (security-design §1 via /specify-srd)
# /checklist: optional
# /plan-lld: skipped
# /implement: code + tests only
```

### MVP — First Production Release
```yaml
scope: "mvp"
# /specify-doc: security-design §1-2, data-model
# /checklist: mandatory
# /plan-lld: included
# /implement: + QA cases, Runbook
```

### Full — Complete Production
```yaml
scope: "full"
# /specify-doc: security-design §1-4, data-model, resilience, investigation
# /checklist: mandatory
# /plan-lld: included
# /implement: + QA cases, Runbook, OpenAPI
```

---

## Constitution — How It Gets Filled

`/specify` reads your context and extracts these rows for the SPA tech stack (as a DRAFT — see GATE-1):

| Extracted | From your context section |
|---|---|
| Language + Framework | Tech stack (TypeScript/JavaScript + React/Vue/Angular/Svelte) |
| Build Tool | Derived from framework (Vite / webpack / Next / Nuxt) |
| State Management | Tech stack section |
| Component Library | Tech stack / UI section |
| Routing | Derived from framework |
| API Client | Integration section |
| Data Cache | Tech stack section |
| Config + Secrets | Infrastructure section (secrets never bundled) |
| Resilience | NFR section (error boundaries, retry) |
| Observability | NFR section (Sentry / RUM) |
| Logging | NFR / tech stack (structured console) |
| Testing + Coverage | NFR section (Jest / Vitest + Testing Library) |
| Linting/Formatting | Tech stack section (ESLint + Prettier) |
| Accessibility | NFR section (WCAG 2.1 AA by default) |
| CI/CD | Infrastructure section |
| Hosting/CDN | Infrastructure section |
| Core Principles | Component-First, Accessible, Performant (always) + domain |
| Domain Rules | UX and business rules |
| Never Do | Constraints + standard SPA rules (no API in components, no inline styles) |

**Tip: richer context = better constitution draft.**

---

## GATE-1 — Finalize Constitution Part 2 (manual, blocking)

After /specify, Part 2 is a DRAFT. Before /specify-brd can run:

1. Open `.specify/memory/constitution.md` → Part 2
2. Review every row — Tech Stack, Core Principles, Domain Rules, Never Do
3. Resolve any `[MISSING — ask user]` markers
4. Edit anything wrong directly — your edits are AUTHORITATIVE
5. Tell the agent: **"Constitution Part 2 finalized"**

A later `/specify` re-run must propose changes for review — it will
never silently overwrite a finalized Part 2.

---

## Review Gates

| Command | Reviewer (see roles.yml) | Before Next |
|---|---|---|
| GATE-1 | Tech lead (accountable) | /specify-brd |
| /specify-brd | Product owner | /specify-uc |
| /specify-uc | Business analyst + Product owner | /specify-srd |
| /specify-srd | Business analyst | /validate |
| /validate | Product owner + Business analyst | /analyze |
| /analyze | Tech lead (+ architect, security officer consulted) | /clarify |
| /clarify | Product owner (accountable), BA (consulted) | /plan-design |
| /plan-design | Tech lead + architect + stakeholders | /plan-lld or /task |
| /plan-lld | Senior developer | /task |
| /task | Product owner + dev team (+ QA lead consulted) | /implement |
| /implement | Assigned developer — per task PR | /release |
| /release | QA lead (responsible), product owner (accountable) | go-live |

---

## Reading Mode — Quality vs Token Economy

```yaml
reading_mode: "auto"    # auto | summary | full
```

- **auto** (default): use `.summary.md` if present; fall back to full doc + auto-generate summary
- **summary**: always use summary only; strict token economy
- **full**: always read full `.md`; maximum quality at higher token cost

Set `reading_mode: "full"` in `manifest.yml` for complex features where you want the agent to read every document completely.

---

## Summary Limits
Edit `.specify/memory/summary-rules.md`:
```
pilot: SUMMARY_MAX_LINES: 20
mvp:   SUMMARY_MAX_LINES: 25
full:  SUMMARY_MAX_LINES: 30
```
Tell agent: "Summary rules updated — re-read summary-rules.md"

---

## Token Usage Logging (optional — real when available, estimated otherwise)

**What:** A per-feature running log of token usage and cost, one row
appended after every command. Off by default.

**Enable it:** `cp .specify/memory/token-pricing.yml.example .specify/memory/token-pricing.yml`,
then fill in current $/million-token rates from your provider's own
pricing page (they ship as `null` — this framework has no way to fetch
live pricing). From the next command onward, the agent creates
`.specify/features/{feature}/token-usage.md` (from
`token-usage-template.md`) and appends a row each time.

**Real usage under Claude Code.** If you're running this pack in Claude
Code, `sdd token-log --command {name}` reads Claude Code's own local
session transcript (`~/.claude/projects/...` — real per-turn usage the
Anthropic API actually reported, not an approximation) and writes the
row itself, including creating the file and updating Running Totals.
Exit codes tell the agent what happened, so you'll never see a raw
traceback for the normal cases:
- `0` — logged successfully (or nothing new since the last log — also
  exit 0, no row added)
- `2` — `token-pricing.yml` doesn't exist yet (logging is off)
- `3` — no Claude Code session transcript found (not running under
  Claude Code, or this project hasn't been touched by one yet) — the
  agent falls back to the estimate below, silently

**Estimated fallback (every other AI tool, or if `sdd token-log` isn't
available):** the agent computes each row itself — command name, model,
estimated input tokens, estimated output tokens, estimated cost,
`Source: Estimated`, timestamp — plus updating the running-total table
at the top of the file itself.

**What each row contains:** command name, model, input tokens, output
tokens, cost, `Source` (`Real (Claude Code)` or `Estimated` — check this
before comparing two rows to each other), timestamp.

**Important limits — read before trusting the numbers:**
- **`Estimated` rows are not measured.** No AI tool this framework
  supports (Claude Code, Copilot, Cursor, Windsurf, or copy-paste "any
  AI") exposes an API for an agent to introspect its own exact token
  consumption from inside a prompt — this is what the estimate falls
  back to. Every number is approximated as `characters ÷ 4`, which
  ignores prompt-caching, tool overhead, and model-specific
  tokenization — real usage is typically higher.
- **Even `Real` rows aren't a substitute for your provider's own
  usage/billing dashboard** (e.g. Claude Code's `/cost` command or the
  Anthropic Console) — cache-creation and cache-read tokens are billed
  at their own rates this file's schema doesn't split out, folded into
  Input Tokens as one approximation.
- **Cost is only as current as your pricing file.** If a model has no row,
  or the row still has `null` rates, the cost column shows
  `token-pricing.yml`'s `unknown_model_fallback` text instead of a number.
- **Good for relative comparison** (which command or feature costs more
  than another), **not for reconciling against your actual invoice.**

**Disable it:** delete or rename `.specify/memory/token-pricing.yml` —
logging stops immediately; nothing else in the pipeline depends on it.

---

## Workflow Mode — GitHub or Local

```yaml
workflow_mode: "github"   # github | local   DEFAULT: github
```

**github** (default) — branch + PR flow. Despite the name, this works on
**GitHub, GitLab, Bitbucket, or Azure DevOps** — `sdd pr create` auto-detects
the host from `git remote get-url origin`:
- `/implement` ends each task with `"PR ready — {N} lines, {N} files"`
- `sdd pr create --task TASK-NNN` opens the PR on whichever host you're on
  (see cli-python/README.md "sdd pr create" for per-host setup)
- CI runs build/test/coverage/lint/secret-scan/SCA on every PR push — via
  `.github/workflows/quality-gate.yml` on GitHub, or the equivalent
  `bitbucket-pipelines.yml` / `.gitlab-ci.yml` / `azure-pipelines.yml` at the
  repo root on the other hosts (only the one matching your host ever runs)
- `/release` requires every task PR-approved and merged

**local** — no git hosting required:
- `/implement` runs build/test/coverage/lint locally, reports ✅/❌,
  ends with `"Task accepted — {N} lines, {N} files"`
- `/release` requires every task `"Task accepted"`

Switch modes any time by editing `manifest.yml`.

---

## PR Rules
```yaml
pr_rules:
  max_lines_per_pr: 400
  max_files_per_pr: 5
```

---

## Upgrading Scope

1. Edit `manifest.yml`: `scope: "pilot"` → `"mvp"` (or `"full"`)
2. Run `sdd review status` to see newly required documents
3. Generate new spec docs: `/specify-doc {name}` for each
4. Run `/plan-lld` if upgrading from pilot
5. Append `CHG-NNN` tasks to `tasks.md`

---

## File Ownership

| File | Owner | Changes |
|---|---|---|
| manifest.yml | You | Per project |
| contexts/{f}.md | You | Per feature |
| .specify/memory/roles.yml | You | RACI owners per project |
| constitution.md Part 1 | Framework | Never |
| constitution.md Part 2 | Agent (/specify) → You (GATE-1) | Generated draft, then finalized |
| summary-rules.md | You | When limit changes |
| All templates | Framework | Never |
| CLAUDE.md | Framework | Never |
