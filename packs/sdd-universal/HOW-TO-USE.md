# How To Use — SDD Pack

---

No `.specify/contexts/{feature}.md` yet? Run `/create-context` first —
paste rough notes and the agent drafts context.md with you, instead of
writing it by hand. See `.specify/contexts/CONTEXT-GUIDE.md`.

---

## Choosing the Right Pack

Five packs are available. Copy exactly one into your project.

| Pack | Best For | Auto-detect? |
|---|---|---|
| **sdd-universal** | Any project — not sure which to pick? Use this. | Yes — `setup.sh` detects project type from your files |
| **sdd-backend-service** | REST APIs, microservices, databases, messaging | No — you chose this pack manually |
| **sdd-frontend-spa** | React / Vue / Angular single-page applications | No — you chose this pack manually |
| **sdd-fullstack** | Frontend + backend in the same repository | No — you chose this pack manually |
| **sdd-mobile** | React Native or Flutter mobile apps | No — you chose this pack manually |

**Rule of thumb:** If you are unsure, use `sdd-universal`. Its `setup.sh` runs `detect_project_type()` which auto-detects your type from these signals (checked in this order):

| Signal detected | Resolved type |
|---|---|
| `pubspec.yaml` present | `mobile` (Flutter) |
| `react-native` in `package.json` | `mobile` (React Native) |
| `package.json` **and** `pom.xml` both present | `fullstack` |
| `pom.xml` present (no `package.json`) | `backend-service` |
| `package.json` present (no `pom.xml`) | `frontend-spa` |
| None of the above | `backend-service` (default) |

> Mobile checks intentionally appear before fullstack: a React Native project with a pom.xml (e.g. a monorepo) must resolve to `mobile`, not `fullstack`.

If you copy one of the type-specific packs directly, `manifest.yml` → `project_type` is already set for you — no auto-detection needed.

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
pip install sdd-init          # Python (any platform)
# OR
npm install -g sdd-init       # Node.js (any platform)
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
| mvp | `/specify-doc security` then `/specify-doc data-model` |
| full | `/specify-doc security` then `/specify-doc data-model` then `/specify-doc resilience` then `/specify-doc investigation` |

**When to run:** After SRD is approved, one at a time.

**Prerequisites:** SRD approval + `srd.summary.md` exists.

**Available document names:**
- `security` → `security-design.md` (STRIDE threat model, §1-2 for mvp, §1-4 for full)
- `data-model` → `data-model.md` (entities, relationships, PII handling)
- `resilience` → `resilience.md` (circuit breakers, retry, bulkhead, SLA budget allocation)
- `investigation` → `investigation.md` (spike / technical investigation for unknowns)

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

The `sdd` CLI adds Jira/Confluence integration on top of these slash commands:
```bash
sdd review submit --doc brd      # push to Confluence + create Jira review task
sdd review check  --doc brd      # poll: exit 0=approved 1=needs-revision 2=pending
sdd review apply  --doc brd      # re-push after addressing reviewer comments
sdd review status                # full dashboard for all documents
```
Configure reviewers in `.specify/integrations.yml` — see `integrations.yml.example`.
Without the CLI, share documents manually with reviewers and tell the agent the outcome.

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

/specify reads your context and extracts (as a DRAFT — see GATE-1):

| Extracted | From your context section |
|---|---|
| Language + Framework | Tech stack section |
| Build Tool | Derived from language |
| API Style | Endpoint contracts |
| Messaging | Integration section |
| Database + Cache | Tech stack / integrations |
| DB Migration | Derived from framework |
| Config + Secrets | Infrastructure section |
| Resilience | NFR section |
| Observability + Logging | NFR / tech stack |
| Testing + Coverage | NFR section |
| CI/CD + Orchestration | Infrastructure |
| Core Principles | Domain + constraints |
| Domain Rules | Business rules |
| Never Do | Constraints |

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

**github** (default) — branch + PR flow:
- `/implement` ends each task with `"PR ready — {N} lines, {N} files"`
- CI (`.github/workflows/quality-gate.yml`) runs build/test/coverage/
  lint/secret-scan/SCA on every PR push
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
