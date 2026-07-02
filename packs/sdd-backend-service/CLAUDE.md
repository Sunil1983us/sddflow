# CLAUDE.md — Backend Service Pack
# REST APIs, microservices, databases, messaging
# Command flow:
# SPECIFY → [GATE-1: constitution finalized] → VALIDATE → ANALYZE → CLARIFY
# → PLAN-DESIGN → PLAN-LLD (mvp+) → TASK → IMPLEMENT → RELEASE

## CREATE-CONTEXT — Optional Pre-Phase (before SPECIFY)
If `.specify/contexts/{feature}.md` does not exist yet, or is empty/a
placeholder, offer `/create-context`: the user pastes informal notes (any
format), the agent drafts context.md against context-template.md, lists a
plain-language "Missing Information" checklist, and iterates with the user
until it's ready. See .github/prompts/create-context.prompt.md and
.specify/contexts/CONTEXT-GUIDE.md. Skip this entirely if the user already
has a structured context.md.

## Startup (every session)
1. Read .specify/manifest.yml
2. Read .specify/memory/constitution.md
3. Read .specify/memory/summary-rules.md
4. Read .specify/memory/change-rules.md
5. Read .specify/memory/roles.yml
<!-- shared:startup-instructions:start -->
6. Read .github/instructions/*.instructions.md — apply each file's
   `applyTo` glob to any file you create or edit that matches it,
   exactly as GitHub Copilot does (AI-7: Claude Code ≡ Copilot parity).
<!-- shared:startup-instructions:end -->
   These model the Java/Spring reference stack (constitution Part 2 →
   Language/Framework) — if your stack differs, apply each rule's
   intent using that language's idioms and conventions, don't skip it.
7. Confirm: project.name, scope, feature, context_file
<!-- shared:gate1-reminders:start -->
8. If constitution Part 2 not generated → remind user to run /specify first
9. If constitution Part 2 generated but NOT finalized (GATE-1 open) →
   remind user to review + finalize it before /validate can run
<!-- shared:gate1-reminders:end -->

## AI-2 — Summary-First Rule (token economy)
For every command AFTER /specify, read `.summary.md` files for prior
documents. Behaviour is governed by `reading_mode` (set in manifest.yml,
default `auto` from summary-rules.md):
- auto (default): use summary if present; fall back to full doc +
  auto-generate summary if missing
- summary: always use summary; warn if missing (strict token economy)
- full: always read full .md (debugging / initial migration only)
/implement always reads `tasks.md` (current task only) + `constitution.md`
in full regardless of reading_mode.
See .specify/memory/summary-rules.md → AI-2 Reading Mode Decision Tree.

## SPECIFY — Five Sub-Commands

`/specify` generates the constitution only. Spec documents are generated
**one at a time** using dedicated sub-commands — same pattern as `/plan-*`.

| Command | What it generates | Gate |
|---|---|---|
| `/specify` | Constitution Part 2 (DRAFT) | — |
| `/specify-brd` | Business Requirements Document | GATE-1 passed |
| `/specify-uc` | Use Case Specification (Actors + UC-NNN with MP/AP/EP) | BRD approved |
| `/specify-srd` | Software Requirements Document | Use Cases approved |
| `/specify-doc {name}` | Any extended doc (security, data-model, resilience, investigation) | SRD approved |

**`/specify` (constitution):**
- Read context file → extract all tech decisions
- Fill Tech Stack table (Language, Framework, Build Tool, API Style,
  Messaging/Async, Serialisation, Schema, Data Store, Data Cache, DB
  Migration, Configuration, Secrets, Resilience, Observability, Logging,
  Testing, Coverage Gate, Quality/Security, Orchestration, CI/CD)
- Extract Core Principles from domain constraints
- Extract Domain Rules from business rules
- Extract Never Do from stated constraints
- Set/bump Part 2 version line (v1.0 first run, v{X.Y+1} on amendment)
- Save updated constitution.md — Part 1 unchanged, Part 2 is a DRAFT
- List any remaining `[MISSING — ask user]` rows as Open Items for GATE-1
- State: "Constitution Part 2 generated — DRAFT. Review and finalize
  every row (GATE-1), then run /specify-brd."

**`/specify-brd` → `brd.md`** — gate: GATE-1 passed
**`/specify-srd` → `srd.md`** — gate: BRD approved
**`/specify-doc data-model`** → `data-model.md` (mvp+) — gate: SRD approved
**`/specify-doc security`** → `security-design.md` — gate: SRD approved
**`/specify-doc resilience`** → `resilience.md` (full) — gate: SRD approved
**`/specify-doc investigation`** → `investigation.md` (full) — gate: SRD approved

## GATE-1 — Constitution Part 2 Finalized (manual, blocking)
After Action 1, constitution.md Part 2 is a DRAFT.
STOP — the user reviews every row (Tech Stack, Core Principles, Domain
Rules, Never Do), resolves any `[MISSING — ask user]` markers, and may
edit directly. Manual edits are AUTHORITATIVE. The user then tells the
agent: "Constitution Part 2 finalized."
A later /specify re-run must propose changes for review — never silently
overwrite a finalized Part 2. Re-run produces a Constitution Amendment
Summary (row diffs + version bump + change-rules.md Change Impact Matrix
cross-reference) and WAITs for confirmation.
No /validate, /analyze, or any later command may run until this gate passes.

## Upgrading Scope

To upgrade `pilot → mvp` or `mvp → full` after initial delivery:
1. Update `manifest.yml` → `scope: mvp` (or `full`)
2. Run `sdd review status` to see newly required documents
3. Generate newly required spec docs: `/specify-doc {name}` for each (e.g. data-model, resilience)
4. Generate `/plan-lld` if upgrading from pilot (skipped previously)
5. Append new `CHG-NNN` tasks to `tasks.md` under a new Change Set heading
6. All new documents go through the same review gates as the original spec

Scope upgrade is a **Major amendment** to constitution Part 2 (version bump X.0).

<!-- shared:scope-reference:start -->
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
<!-- shared:scope-reference:end -->

<!-- shared:team-routing:start -->
## Virtual Team — Address by Name

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
<!-- shared:team-routing:end -->

## Command Gates
<!-- shared:command-gates:start -->
**Unified** (`plan_mode: unified`): SPECIFY → [GATE-1] → VALIDATE → ANALYZE → CLARIFY → /plan-design → /plan-lld (mvp+) → TASK → IMPLEMENT → RELEASE
**Separate** (`plan_mode: separate`): … → CLARIFY → /plan-arch → /plan-hld → /plan-adr (mvp+) → /plan-lld (mvp+) → TASK → IMPLEMENT → RELEASE
Each gate requires the previous step complete and reviewed.
<!-- shared:command-gates:end -->

## PR Contract
<!-- shared:pr-contract:start -->
- Estimate before every task.
- If > max_lines_per_pr → SPLIT A/B/C → confirm → one at a time.
- After task: state files + lines + "PR ready" → wait for go.
<!-- shared:pr-contract:end -->
- If `manifest.workflow_mode = local`: instead of "PR ready", run
  build/test/lint/coverage locally → report ✅/❌ per check → state
  files + lines + "Task accepted" → wait for go.

## Summary
After every doc: write .summary.md (max SUMMARY_MAX_LINES). See AI-2 above.

## Never Do
<!-- shared:never-do-core:start -->
- Never run /validate before constitution Part 2 finalized (GATE-1)
- Never run /analyze without validate.summary.md
- Never run /plan-design without clarify.summary.md (unified mode)
- Never run /plan-design while any spec doc has an unresolved
  `[ASSUMPTION-NNN]` marker (AI-8)
- Never run /plan-arch without clarify.summary.md and all items RESOLVED (separate mode)
- Never run /plan-hld without arch.md `Status: Approved`
- Never run /plan-adr without hld.md `Status: Approved` (mvp+ scope only)
- Never run /implement without TASK (stories.md + tasks.md) approved
- Never run /release before all tasks are "PR ready" and merged
- Never code before context.md updated
- Never hardcode any value
- Never skip paired test
<!-- shared:never-do-core:end -->
- Never run /release in local mode (`manifest.workflow_mode = local`)
  before all tasks show "Task accepted" — the local-mode equivalent of
  "PR ready" + merged

## PLAN Sub-Commands

PLAN adapts to your `plan_mode` setting in `manifest.yml` (set during `setup.sh`).

**Unified mode (`plan_mode: unified`)** — one combined document, one review gate:
- **`/plan-design`** → `design.md`: Architecture + Diagrams + API Design + ADR entries
  - Gate: clarify.summary.md exists, all RESOLVED; no unresolved [ASSUMPTION-NNN] (AI-8)
  - Review: tech lead + architect + stakeholders
  - Scope: all scopes (pilot, mvp, full)

**Separate mode (`plan_mode: separate`)** — three focused documents, reviewed individually:
- **`/plan-arch`** → `arch.md`: Architecture pattern, layers, key decisions — Step 1 of 3
  - Gate: clarify.summary.md exists, all RESOLVED; no unresolved [ASSUMPTION-NNN] (AI-8)
- **`/plan-hld`** → `hld.md`: System diagrams (C4 context, sequence, state machine) — Step 2 of 3
  - Gate: arch.md approved
- **`/plan-adr`** → `adr.md`: Architecture Decision Records — Step 3 of 3 (mvp+ only; skipped at pilot)
  - Gate: hld.md approved

**Both modes:**
- **`/plan-lld`** → Detailed technical design: class/sequence diagrams (mvp+ only; SKIP if pilot)
  - Unified gate: design.md approved
  - Separate gate: adr.md approved (mvp+) or hld.md approved (pilot)

## /checklist — Optional Spec-Quality Gate (after GATE-1, before /validate)

**Mandatory for `mvp` and `full` scope. Optional for `pilot`.**
Run `/checklist` after `/specify` + GATE-1 to catch spec quality issues
before the business sign-off:
- CRITICAL: unresolved [NEEDS CLARIFICATION], unmeasured NFRs, FRs without
  acceptance scenarios — these block /validate
- HIGH: vague adjectives (fast/scalable/secure without a number), UCs without
  Independent Test
- MEDIUM: terminology drift, missing Out of Scope items
Saves to: `.specify/features/{feature}/checklists/{feature}-spec-quality.md`
All CRITICAL items must be resolved before /validate can proceed.

<!-- shared:review-gates:start -->
## Document Review Gates — Three Modes

Each SDD document is gated: the next document in a phase cannot proceed until
the current one is approved. The `Status:` header inside the `.md` file is the
**authoritative gate** in every mode — Jira and Confluence are integrations on
top of it, never a prerequisite.

| Mode | Needs | Approval flow | Audit trail |
|---|---|---|---|
| **chat** (default) | nothing | Reviewer reads the doc; user replies "approved" in chat → agent flips `Status: Draft → Approved` + fills Approvals table | Doc header + Approvals table + git history |
| **local** | `pip install sddkit` | Same as chat, plus the agent records it: `sdd review approve --doc {doc} --local --by "{approver}" --note "{comment}"` | `.specify/.local-approvals.yml` |
| **jira** | CLI + `integrations.yml` (`jira:` + `confluence:`) | `sdd review submit / check / apply` — Confluence page + Jira review task per doc | Jira + Confluence |

**Confluence stays in sync in every mode.** When a `confluence:` section exists
in `.specify/integrations.yml`, `sdd review approve --local` also updates the
document's existing Confluence page after flipping the status — chat and local
approvals never leave Confluence stale. Manual re-push at any time:
`sdd confluence push --doc {doc}` (needs only the `confluence:` section, no Jira).

**Who approves** is defined per gate in `.specify/memory/roles.yml` (RACI —
the accountable role). When recording an approval, the agent asks once for the
approver name/role and an optional comment.

**Governance guidance by scope:** chat mode is fine for `pilot`. For `mvp` use
local mode (named approver + audit file). For `full` scope prefer jira mode —
independent tracking of who approved what, when.

### jira mode commands

Sequences follow `plan_mode` (manifest.yml). Doc keys match the `.md`
filenames: `design` exists in unified mode; `arch`/`hld`/`adr` in separate mode.

| Phase | Sequence (unified) | Sequence (separate) | Reviewer |
|---|---|---|---|
| specify | BRD → Use Cases → SRD → Design | BRD → Use Cases → SRD | PO → BA → BA → Architect |
| planning | LLD (mvp+) | Arch → HLD → ADR (mvp+) → LLD (mvp+) | Tech Lead / Architect |
| tasks | Tasks | Tasks | Scrum Master |
| release | Runbook → Release | Runbook → Release | DevOps → Release Manager |

```bash
sdd review submit --doc brd      # push to Confluence + create Jira review task
sdd review check  --doc brd      # poll: exit 0=approved 1=needs-revision 2=pending
sdd review apply  --doc brd      # re-push after addressing reviewer comments
sdd review status                # full dashboard for all documents
```

When `sdd review check` exits 1 (NEEDS REVISION): read reviewer comments, update
the document, then run `sdd review apply` and ask reviewer to re-review.
Configure reviewers in `.specify/integrations.yml` — see `integrations.yml.example`.
<!-- shared:review-gates:end -->
## IMPLEMENT — Code Review Gate

For each task in the `/implement` phase:

1. Write and commit the implementation
2. **Pre-review** (if `code_review.pre_review: true` in integrations.yml — default):
   - Run `/pre-review [TASK-ID]`
   - Agent analyses the diff (correctness, security, quality, performance)
   - Numbered checklist presented — pick which findings to fix
   - Agent applies selected fixes and commits
   - Pre-review summary saved to `.specify/features/{feature}/.pre-review-{task}.md`
3. **Create PR**: `sdd pr create --task TASK-ID`
   - Pre-review summary is included in the PR body automatically
   - If `code_review.pre_review: false`: PR is created directly without pre-review
4. **Human review**: reviewer approves or adds inline comments on the PR
5. **Address comments** (if reviewer requests changes):
   - Run `/address-review [PR-number]`
   - Agent shows unresolved comment threads as a numbered checklist
   - Pick which to fix — agent applies fixes, pushes, replies to threads, requests re-review
   - Repeat per review round until PR is approved
6. PR merged → task complete

## VALIDATE and RELEASE — Bookends

- **`/validate`** → Business sign-off on brd.md + srd.md
  - Gate: GATE-1 (constitution Part 2 finalized)
  - Review: product owner + business analyst
  - Run after: /specify (Action 2) | Gate before: /analyze

- **`/release`** → UAT plan, deployment plan, go-live gate, BO closure
  - Gate: all tasks complete — "PR ready" + merged (github
    mode) or "Task accepted" (local mode)
  - Review: qa lead, product owner, tech lead, devops/sre
  - Run after: /implement (all tasks) | Gate before: go-live

## /orchestrate — Full Pipeline (optional)
Run `/orchestrate` to drive the entire pipeline in one command.
Supports `--list` (status dashboard), `--from STEP` (resume), `--to STEP` (stop early).
Works in CLI (single-session) and multi-agent SDK modes.
See `.github/prompts/orchestrate.prompt.md` for full reference.

## Command Order
/orchestrate  ← runs everything below automatically

— or step by step —
/specify → [GATE-1] → /specify-brd → /specify-uc → /specify-srd → /specify-doc {name}... → /checklist (mandatory mvp+, optional pilot)
→ /validate → /analyze → /clarify
→ unified: /plan-design  |  separate: /plan-arch → /plan-hld → /plan-adr (mvp+)
→ /plan-lld (mvp+) → /task → /implement → /release
