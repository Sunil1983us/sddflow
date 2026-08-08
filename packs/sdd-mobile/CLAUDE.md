# CLAUDE.md — Mobile Pack
# React Native / Flutter — iOS + Android
# Command flow:
# SPECIFY → [GATE-1: constitution finalized] → VALIDATE → ANALYZE → CLARIFY
# → PLAN-DESIGN → PLAN-LLD (mvp+) → TASK → IMPLEMENT → RELEASE

## CREATE-CONTEXT — Optional Pre-Phase (before SPECIFY)
If `.specify/contexts/{feature}.md` does not exist yet, or is empty/a
placeholder, offer `/create-context`: the user pastes informal notes (any
format), the agent drafts context.md against context-template.md
(including its Tech Stack section), lists a plain-language "Missing
Information" checklist, and iterates with the user until it's ready. If
the notes actually describe more than one independently-shippable
feature, the agent flags the split and asks whether to build them one at
a time (Step 1.5 — Feature Size Check). See
.github/prompts/create-context.prompt.md and
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
7. Confirm: project.name, scope, feature, context_file

<!-- shared:feature-name-convention:start -->
**`{Feature Name}` convention.** Every generated document's `{Feature Name}`
placeholder (`# Feature: {Feature Name}`, `# Use Case Specification —
{Feature Name}`, etc. — nearly every template header) resolves from
`manifest.yml`'s `project.name`, falling back to `project.feature` only if
`project.name` is empty. This matches the one place this was already
defined explicitly (the Jira Epic Summary rule in specify-brd.prompt.md) —
now it applies everywhere `{Feature Name}` appears.
Never substitute `context.md`'s own title/Service Name for this — that's
free text the user may phrase more descriptively than the manifest (e.g.
"NIPE Validation Service" vs. a manifest `name: Validation`), and using it
produces a document header that silently disagrees with `manifest.yml`,
Confluence page titles, and the Jira Epic summary.
<!-- shared:feature-name-convention:end -->

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
| `/specify-doc {name}` | Any extended doc (security, screen-spec, ux-flow, data-model, resilience, investigation) | SRD approved |

**`/specify` (constitution):**
  Read context file → extract all tech decisions
  Fill Tech Stack table (Language/Framework, Navigation,
  State Management, Local Storage/DB, API Client, Push
  Notifications, Crash/Analytics, Build Tool, Testing,
  Coverage Gate, Quality/Security, CI/CD, App Store Distribution)
  Extract Core Principles: Offline-First, Accessible, Cross-Platform, Performant
  + Specification First, Test Discipline, Traceability
  Extract Domain Rules from mobile UX/business rules
  Extract Never Do from stated constraints
  Save updated constitution.md — Part 1 unchanged, Part 2 is a DRAFT
  State: "Constitution Part 2 generated — DRAFT. Review and finalize
  every row (GATE-1), then run /specify-brd."

**`/specify-brd` → `brd.md`** — gate: GATE-1 passed
**`/specify-srd` → `srd.md`** — gate: BRD approved
**`/specify-doc screen-spec`** → `screen-spec.md` (mvp+) — gate: SRD approved
**`/specify-doc ux-flow`** → `ux-flow.md` (mvp+) — gate: SRD approved
**`/specify-doc data-model`** → `.specify/service/data-model.md` (mvp+, **living/app-level — not per-feature**, see "Living Documents" below) — gate: SRD approved
**`/specify-doc security`** → `.specify/service/security-design.md` (**living/app-level**, see below) — gate: SRD approved
**`/specify-doc resilience`** → `resilience.md` (full) — gate: SRD approved
**`/specify-doc investigation`** → `investigation.md` (full) — gate: SRD approved

## Living Documents — App-Level, Not Per-Feature

Two documents describe something singular for the whole app, not one
feature — they live at `.specify/service/` instead of
`.specify/features/{feature}/`, and are generated once then
**extended/amended by every later feature**, never regenerated from a
blank template:

| Document | Generated by | Lives at |
|---|---|---|
| Local Data & Cache Model | `/specify-doc data-model` | `.specify/service/data-model.md` |
| Security Design | `/specify-doc security` | `.specify/service/security-design.md` |

When one of these already exists, the generating command walks it —
SKIP / ADD-unit / UPDATE-unit, showing only the delta, one approval — the
same discipline `/change` already uses for document updates.

## GATE-1 — Constitution Part 2 Finalized (manual, blocking)
After Action 1, constitution.md Part 2 is a DRAFT.
STOP — the user reviews every row (Tech Stack, Core Principles, Domain
Rules, Never Do), resolves any `[MISSING — ask user]` markers, and may
edit directly. Manual edits are AUTHORITATIVE. The user then tells the
agent: "Constitution Part 2 finalized."
A later /specify re-run must propose changes for review — never silently
overwrite a finalized Part 2.
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

<!-- shared:token-usage-logging:start -->
## Token Usage Logging (opt-in — real when available, estimated otherwise)

Off by default. Turns on the moment `.specify/memory/token-pricing.yml`
exists (copy it from `token-pricing.yml.example` to enable — see
HOW-TO-USE.md). If that file doesn't exist, skip this section entirely —
do not create it yourself and do not log anything.

If it does exist, after every command that reads or writes a document
(`/create-context`, every `/specify-*`, `/plan-*`, `/task`, `/implement`,
`/release`, `/change`, `/checklist`, `/validate`, `/analyze`, `/clarify`):

1. **Try real usage first, if the `sdd` CLI is installed:**
   ```bash
   sdd token-log --command {this command's name, e.g. specify-brd}
   ```
   This reads Claude Code's own local session transcript for the turns
   spent on this command and writes an authoritative row itself —
   `.specify/features/{feature}/token-usage.md` is created from
   `token-usage-template.md` automatically if this is the first command
   logged for this feature; Running Totals are updated automatically too.
   Exit code 0 means it succeeded — you're done, skip step 2 entirely.
2. **Fall back to the estimate** whenever `sdd token-log` isn't
   available or exits non-zero (CLI not installed, not running under
   Claude Code, or nothing new since the last log — all normal, expected
   outcomes, not errors to report to the user): append one row to
   `.specify/features/{feature}/token-usage.md` yourself (create it from
   `token-usage-template.md` if this is the first command logged for
   this feature):
   - Input Tokens ≈ (total characters read this command, across every
     file touched — manifest, constitution, prior docs/summaries,
     templates) ÷ 4
   - Output Tokens ≈ (total characters written this command — the
     generated document plus your chat response) ÷ 4
   - Model: your own model identifier (e.g. `claude-sonnet-5`); write
     `unknown` if you cannot determine it
   - Cost: look up `{model}` in `token-pricing.yml`'s `models:` map and
     multiply its rates by the two estimates above; if the model has no
     row, or a row with `null` rates, write that file's
     `unknown_model_fallback` value instead of guessing a number
   - Source: `Estimated`
   - Timestamp: current date
   Then update the Running Totals table at the top of `token-usage.md`
   yourself (sum of every row logged so far for this feature).

These figures are for relative comparison only, `Real` rows included —
see `token-usage.md`'s own notes section for exactly what each `Source`
value does and doesn't measure.
<!-- shared:token-usage-logging:end -->

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
- Never make API calls directly in screens — service layer only
- Never assume connectivity — assume offline first, sync when connected
- Never request permissions on startup — request at point of use

## PLAN Sub-Commands

PLAN adapts to your `plan_mode` setting in `manifest.yml` (set during `setup.sh`).

**Unified mode (`plan_mode: unified`)** — one combined document, one review gate:
- **`/plan-design`** → `design.md`: Architecture + Screen Flow Diagrams + API Design + ADR entries
  - Gate: clarify.summary.md exists, all RESOLVED; no unresolved [ASSUMPTION-NNN] (AI-8)
  - Review: tech lead + ux lead + architect + stakeholders
  - Scope: all scopes (pilot, mvp, full)

**Separate mode (`plan_mode: separate`)** — three focused documents, reviewed individually:
- **`/plan-arch`** → `arch.md`: Architecture pattern, layers, key decisions — Step 1 of 3
  - Gate: clarify.summary.md exists, all RESOLVED; no unresolved [ASSUMPTION-NNN] (AI-8)
- **`/plan-hld`** → `hld.md`: Screen flow + sequence diagrams (C4 context, state machine) + API design — Step 2 of 3
  - Gate: arch.md approved
- **`/plan-adr`** → `adr.md`: Architecture Decision Records — Step 3 of 3 (mvp+ only; skipped at pilot)
  - Gate: hld.md approved

**Both modes:**
- **`/plan-lld`** → Detailed technical design: class/component + sequence diagrams (mvp+ only; SKIP if pilot)
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
| **local** | `pip install sddflow` | Same as chat, plus the agent records it: `sdd review approve --doc {doc} --local --by "{approver}" --note "{comment}"` | `.specify/.local-approvals.yml` |
| **jira** | CLI + `integrations.yml` (`jira:` + `confluence:`) | `sdd review submit / check / apply` — Confluence page + Jira review story per doc | Jira + Confluence |

**Confluence stays in sync in every mode.** When a `confluence:` section exists
in `.specify/integrations.yml`, `sdd review approve --local` also updates the
document's existing Confluence page after flipping the status — chat and local
approvals never leave Confluence stale. Manual re-push at any time:
`sdd confluence push --doc {doc}` (needs only the `confluence:` section, no Jira).

**Who approves** is defined per gate in `.specify/memory/roles.yml` (RACI —
the accountable role). When recording an approval, the agent resolves the
approver's name from `roles.yml`'s `roles:` map first (filled in once per
project) and only asks the user directly if that name is still empty —
either way, the resolved name is written into the document's own
`## Approvals` table (`Approver` column), not just the role label, so it's
visible who actually approved it without cross-referencing roles.yml.

**Governance guidance by scope:** chat mode is fine for `pilot`. For `mvp` use
local mode (named approver + audit file). For `full` scope prefer jira mode —
independent tracking of who approved what, when.

**Self-approval risk (chat mode).** Nothing in chat mode stops the same
conversation that drafted a document from also being the one that replies
"approved" to it — there is no independent reviewer identity check, only
the human typing the word. This is why the scope guidance above escalates:
`local` mode at least records a named approver in an audit file, and
`jira` mode requires the actual accountable person (from `roles.yml`) to
act in Jira, outside the drafting conversation entirely. If chat mode is
used past `pilot`, treat approvals as informal and know that the
mechanism doesn't verify who is typing "approved" — for a genuinely
independent gate, have a *different* conversation/session (or a human
outside the AI tool altogether) perform the approval, not the same
session that generated the document.

### jira mode commands

Sequences follow `plan_mode` (manifest.yml). Doc keys match the `.md`
filenames: `design` exists in unified mode; `arch`/`hld`/`adr` in separate mode.

| Phase | Sequence (unified) | Sequence (separate) | Reviewer |
|---|---|---|---|
| specify | BRD → Use Cases → SRD → Design | BRD → Use Cases → SRD | PO → BA → BA → Architect |
| validate | Validate → Analyze → Clarify | Validate → Analyze → Clarify | PO → Tech Lead → Architect |
| planning | LLD (mvp+) | Arch → HLD → ADR (mvp+) → LLD (mvp+) | Tech Lead / Architect |
| tasks | Tasks | Tasks | Scrum Master |
| release | Runbook → Release | Runbook → Release | DevOps → Release Manager |

```bash
sdd review submit --doc brd      # push to Confluence + create Jira review story
sdd review check  --doc brd      # poll: exit 0=approved 1=needs-revision 2=pending
sdd review apply  --doc brd      # re-push after addressing reviewer comments
sdd review status                # full dashboard for all documents
```

When `sdd review check` exits 1 (NEEDS REVISION): read reviewer comments, update
the document, then run `sdd review apply` and ask reviewer to re-review.
Configure reviewers in `.specify/integrations.yml` — see `integrations.yml.example`.

**What `sdd review apply` actually does to an already-Approved document.**
This is the command every revision-driven step calls (a reviewer's NEEDS
REVISION feedback being addressed, or `/clarify` patching a document that
was already Approved) — it never creates a second Jira ticket for the
same document; it always re-uses the one ticket found by that document's
persistent label, updating it in place. On every call it also:
1. **Reverts the document's own `Status:` header** from `Approved` back
   to `Draft` (or `Proposed` for `adr.md`) — this happens unconditionally,
   even in pure chat/local mode with no `jira:`/`confluence:` configured,
   since it's a local-file operation. A document still mid-review (never
   yet Approved) is left untouched — nothing to revert.
2. Posts a "please re-review" comment on the existing Jira ticket, if one
   exists for this doc.
3. **Nudges the ticket's Jira workflow status**, only if `reopen_status`
   is set in `integrations.yml` (unset by default — see
   `integrations.yml.example`). The CLI cannot guess a real status name
   for your workflow, so this is opt-in: without it, a ticket already
   moved to Done/Closed stays there and only gets the comment above —
   with it, `sdd review apply` attempts a transition to the configured
   status (e.g. `"In Review"`) so the re-review request doesn't sit
   unnoticed on a closed ticket. Silently a no-op if the ticket is
   already in that status or the workflow has no path to it from the
   current state — never blocks the rest of the command.

**The `validate` phase is optional per-document.** Unlike the `specify`/
`planning`/`tasks`/`release` phases, `validate`/`analyze`/`clarify` fall back
to chat approval individually if their own `document_reviews` entry is
missing — add `document_reviews.validate` (and/or `.analyze`, `.clarify`) to
`integrations.yml` only for the ones you want routed through Jira/Confluence;
the rest stay chat-only.

**Blocked documents can still collect answers via Jira/Confluence.** A
document like `validate.md` can be blocked on `[NEEDS CLARIFICATION-NNN]`
markers in its source docs before it's ever submitted for review — see
`validate.prompt.md`'s §3a. `sdd review push-questions --doc {doc}` pushes
the open items to a Jira ticket + Confluence page (reusing the same
reviewer/ticket `sdd review submit` will use once unblocked — the ticket
evolves in place, no duplicate). `sdd review pull-answers --doc {doc}`
reads reviewer replies (a comment starting with the item's ID, e.g.
`brd:NC-002: 90 days`) and patches the answered marker directly into its
source document, bumping that document's version, and re-pushes that
document's own Confluence page immediately so it never goes stale.

**`clarify.md`'s own items (AMB/GAP/CON/ASM/OQ/R) work the same way**, via
the same two commands and the same doc key (`--doc clarify`) — even though
they're tracked by a STATUS TABLE row rather than a bracketed marker.
Reviewer replies as `clarify:AMB-001: <answer>`; pulling answers fills the
item's `{FILL...}` placeholder and flips its STATUS TABLE row to the
correct terminal status for its type (RESOLVED / CONFIRMED / DECIDED /
CORRECTED), then re-pushes clarify.md's own Confluence page. See
`clarify.prompt.md`'s "Accepted reply forms."

**Every review-driven edit bumps the version.** Whichever mode surfaced the
feedback — a Jira comment, a dashboard comment, or direct chat feedback —
increment the document's `Version:` header and append a row to its
`## Version History` table before re-submitting (see each command's own
review-response step for the exact format). A pure approval with no content
change does not bump the version.
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
   - Works on GitHub, GitLab, Bitbucket, and Azure DevOps — same host
     auto-detection as PR creation (see cli-python/README.md "/address-review")
6. PR merged → task complete

## VALIDATE and RELEASE — Bookends

/validate   → Business sign-off on brd.md + srd.md
              Gate: GATE-1 (constitution Part 2 finalized)
              Review: product owner + business analyst
              Run after: /specify (Action 2) | Gate before: /analyze

/release    → UAT plan, store-release plan, go-live gate, BO closure
              Gate: all tasks complete — "PR ready" + merged (github mode)
              or "Task accepted" (local mode)
              Review: qa lead, product owner, tech lead, devops/sre
              Run after: /implement (all tasks) | Gate before: go-live

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
