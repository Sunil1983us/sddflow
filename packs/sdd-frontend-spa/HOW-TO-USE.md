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
| Data Model | `/specify-doc data-model` | full only |
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

**What:** You paste informal notes (emails, Confluence pages, rough bullets); the agent drafts a structured `context.md` and lists a plain-language "Missing Information" checklist. You iterate until complete.

**When to run:** Before `/specify`, only if you do not already have a `.specify/contexts/{feature}.md`.

**Produces:** `.specify/contexts/{feature}.md`

**You do next:** Review the draft — correct any wrong tech choices, fill in any [MISSING] items, add NFRs and business rules the agent didn't catch. Then fill `manifest.yml` and run `/specify`.

**Skip if:** You already have a well-structured context file.

---

#### Initializing a project — `sdd init` (recommended) or `setup.sh`

**Option 1 — `sdd init` (recommended, requires the CLI):**

Install the CLI once:
```bash
pip install sddkit          # Python (any platform)
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

**What:** Writes the Use Case Specification. Identifies all actors (ACT-NNN), defines use cases (UC-NNN), and documents the Main Path, Alternative Paths (AP-NNN-X), and Exception Paths (EP-NNN-X) for each.

**When to run:** After BRD is approved.

**Prerequisite:** BRD approval + `brd.summary.md` exists.

**Produces:** `.specify/features/{feature}/use-cases.md` + `use-cases.summary.md`

**You do next:** Share with Business Analyst + Product Owner. When approved, tell the agent "Use Cases approved" to unlock `/specify-srd`.

**Reviewer:** Business Analyst + Product Owner

---

#### `/specify-srd` — Software Requirements Document

**What:** Writes the Software Requirements Document. Defines Functional Requirements (FR-NNN), Non-Functional Requirements (NFR-NNN), acceptance scenarios for every FR, and Security Design §1 (threat model basics).

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
| mvp | `/specify-doc security` → `/specify-doc component-spec` → `/specify-doc ux-flow` |
| full | `/specify-doc security` → `/specify-doc component-spec` → `/specify-doc ux-flow` → `/specify-doc data-model` → `/specify-doc resilience` → `/specify-doc investigation` |

**When to run:** After SRD is approved, one at a time.

**Prerequisites:** SRD approval + `srd.summary.md` exists.

**Available document names:**
- `security` → `security-design.md` (STRIDE threat model, §1-2 for mvp, §1-4 for full)
- `component-spec` → `component-spec.md` (component props, state, events, accessibility) — **mvp+**
- `ux-flow` → `ux-flow.md` (user journey flows, screen transitions) — **mvp+**
- `data-model` → `data-model.md` (client data structures, API response shapes) — **full only**
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

---

### Phase 5 — PLAN

#### `/plan-design` — Architecture + API Design + ADRs

**What:** Unified design document. Generates:
- System architecture (hexagonal / layered / event-driven — derived from context)
- Component / service decomposition
- Sequence diagrams for all critical flows (including exception paths)
- API design (endpoints, request/response schemas, error codes)
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

---

## Jira & Confluence Integration

The `sdd` CLI connects your spec documents and tasks directly to your Atlassian workspace. This is optional — without it, share documents manually and tell the agent the review outcome.

### One-Time Setup

**Step 1 — Configure credentials:**
```bash
sdd config init
```
This interactive wizard asks for your Atlassian base URL, auth mode, and env var names. Saves the profile to `~/.sdd/config.yml` (no secrets — only env var names). Optionally creates `.specify/integrations.yml` for this project.

**Step 2 — Export your API token:**
```bash
# Jira Cloud (basic auth — email + API token)
export JIRA_API_TOKEN=your-api-token

# Jira Server / Data Center (Personal Access Token)
export JIRA_PAT=your-personal-access-token
```
Get your API token: Atlassian account → Security → API tokens → Create API token.

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
Pushes are idempotent — re-running updates existing issues rather than creating duplicates (keyed on `sdd:STORY-001` labels).

---

### Jira — Progressive Push (`/jira-push`)

`sdd jira push` above pushes Story+Task together, once, after `/task`. If you
want Jira issues created earlier — Epic right after BRD approval, Stories
after Use Cases/SRD approval — use the agent's `/jira-push` slash command
instead. It calls a standalone script (`.specify/scripts/jira-push.py`) that
also runs unattended from CI/CD.

| | `sdd jira push` (CLI) | `/jira-push` (slash command) |
|---|---|---|
| Config | `.specify/integrations.yml` + `~/.sdd/config.yml` | `.specify/jira-config.yml` (copy from `jira-config-template.yml`) |
| Timing | Once, after `/task` | Progressive: Epic → BRD, Story → Use Cases/SRD, Task → `/task`, CHG → `/change` |
| Hierarchy | Story + Task only | Full Epic → Story → Task → CHG |
| Field mapping | `integrations.yml → jira.custom_fields` | `jira-config.yml → field_mappings` (per-level project keys, issue types, `customfield_NNNNN` IDs) |

**Setup:**
```bash
cp .specify/templates/jira-config-template.yml .specify/jira-config.yml
# edit jira-config.yml: project keys, issue types, custom field IDs
export JIRA_EMAIL=you@company.com
export JIRA_API_TOKEN=your-api-token
```

**Usage** — bare shorthand or full flag syntax, run as your pipeline advances:
```
/jira-push epic          # after /specify-brd approval
/jira-push story         # after /specify-uc or /specify-srd approval
/jira-push task          # after /task approval
/jira-push chg CR-001    # after /change approval
/jira-push --level all --dry-run   # preview every level before pushing for real
```
Keys created/updated are tracked in `docs/jira/keys.yml`.

---

### Confluence — Push Documents

After generating a spec document:
```bash
sdd confluence push --doc brd    # push BRD to Confluence as a formatted page
sdd confluence push --doc srd    # push SRD
sdd confluence push --all        # push all documents listed in integrations.yml page_map
```
Page titles come from `integrations.yml → confluence.page_map`. Re-running updates the existing page.

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
sdd review submit --doc brd      # push to Confluence + create Jira review task
sdd review check  --doc brd      # poll: exit 0=APPROVED  1=NEEDS_REVISION  2=PENDING
sdd review apply  --doc brd      # re-push after addressing reviewer comments
sdd review status                # dashboard: all documents + their current review state
```

**Review sequence is enforced:** BRD must be approved before SRD can be submitted; SRD before design; etc.

**Handling a revision request:**
1. `sdd review check --doc brd` exits 1 (NEEDS_REVISION)
2. Run `/address-review --doc brd` — agent reads comments, proposes updates, you approve
3. `sdd review apply --doc brd` — re-pushes the updated page to Confluence
4. Reviewer re-approves → `sdd review check --doc brd` exits 0 (APPROVED)

Configure reviewers (Jira accountId per document) in `.specify/integrations.yml`. Run `sdd config init` to generate this file interactively, or copy `.specify/integrations.yml.example` and edit it.

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
