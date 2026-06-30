# SDD Pipeline Guide
## Every Step · What It Creates · Who Does It · What's Inside · Where to Change It

---

## How to Read This Guide

Each section below covers one step in the pipeline. For every step you'll see:
- **What you type** — the command
- **Who does the work** — the AI persona responsible
- **What gets created** — the output file
- **What's inside it** — plain English description of the document's content
- **Template file** — where the structure is defined (edit this to change the layout)
- **Prompt file** — where the instructions to the AI live (edit this to change what the AI does)

---

## The Full Pipeline at a Glance

```
SETUP          → fill manifest.yml + write context.md
/specify       → Constitution Part 2            [GATE-1: you review + approve]
/specify-brd   → Business Requirements (BRD)   [Maya]
/specify-uc    → Use Cases                      [Maya]
/specify-srd   → System Requirements (SRD)     [Rex]
/specify-doc   → Extended docs                  [Ava]
/checklist     → Spec Quality Audit             [Quinn]   ← mandatory mvp+
/validate      → Business Sign-Off              [Maya]
/analyze       → Technical Risk Report          [Ava]
/clarify       → Clarification Report           [Rex]
/plan-design   → Architecture + Design Doc      [Ava]
/plan-lld      → Low Level Design               [Leo]     ← mvp+ only
/task          → Stories + Tasks + QA Cases     [Kai]
/implement     → Code                           [Leo]
/pre-review    → AI Code Review                 [Leo]
/release       → Release Plan                   [Riley]
```

---

## Step 0 — SETUP (before any command)

**What you do manually:**
1. Fill `.specify/manifest.yml` with your project name, scope (pilot/mvp/full), and feature name
2. Write `.specify/contexts/{feature}.md` — your plain English description of what you are building

**What's in the context file?**
Your project in your own words — what it does, who uses it, what tech you are using, what the business goals are. Think of it as the brief you would hand to a new team member on day one.

**Where to change the template for context files:**
`.specify/contexts/CONTEXT-GUIDE.md` inside any pack

---

## Step 1 — `/specify`

| | |
|---|---|
| **Who** | No persona — the AI reads your context and fills in the blanks |
| **Output file** | `.specify/memory/constitution.md` (Part 2 only) |
| **Template** | No template — fills the existing `constitution.md` Part 2 section |
| **Prompt file** | `.github/prompts/specify.prompt.md` |

**What's inside constitution.md?**

Think of it as the **rulebook for the whole project**. It has two parts:

- **Part 1** (never change) — the universal principles of SDD (gates, never-do rules, quality standards)
- **Part 2** (you review and finalize) — everything specific to your project:
  - Your full tech stack (language, framework, database, testing tools, CI/CD, etc.)
  - Core principles your project must follow (e.g. API-first, offline-first, test discipline)
  - Domain rules (the business rules the system must always respect)
  - Never Do rules (things the AI must never do in your codebase)

**Why it matters:** Every other document generated after this point reads the constitution as its source of truth. If the constitution is wrong, everything built on top of it is wrong.

**GATE-1** — After `/specify` you must review every row of Part 2 and tell the AI "Constitution Part 2 finalized." Nothing else can run until you do this.

**Where to change it:**
- To change the format of Part 2: edit `constitution.md` directly in your project
- To change what the AI extracts from context: edit `.github/prompts/specify.prompt.md`

---

## Step 2 — `/specify-brd` → Business Requirements Document

| | |
|---|---|
| **Who** | **Maya** — Business Analyst |
| **Output file** | `.specify/features/{feature}/brd.md` |
| **Template** | No dedicated template — Maya generates to a standard BRD structure |
| **Prompt file** | `.github/prompts/specify-brd.prompt.md` |

**What's inside brd.md — in plain English?**

The BRD is the **"why we are building this"** document. It answers:

- **Business Objectives (BO-NNN)** — what business goals this project must achieve, each with a measurable success metric (e.g. "reduce checkout drop-off by 20%")
- **Stakeholders** — who is involved, their role, and what they expect
- **Scope** — what is in scope and what is explicitly out of scope
- **Assumptions** — things we are taking for granted that haven't been confirmed
- **Constraints** — budget, timeline, regulatory, or technical limits
- **Business Risks** — what could go wrong from a business perspective

Think of it as the document a business owner or product manager would sign off on.

**Where to change it:**
- Layout/sections: create a BRD template in `.specify/templates/` and reference it from the prompt
- What the AI generates: edit `.github/prompts/specify-brd.prompt.md`

---

## Step 3 — `/specify-uc` → Use Case Specification

| | |
|---|---|
| **Who** | **Maya** — Business Analyst |
| **Output file** | `.specify/features/{feature}/use-cases.md` |
| **Template** | `.specify/templates/use-cases-template.md` |
| **Prompt file** | `.github/prompts/specify-uc.prompt.md` |

**What's inside use-cases.md — in plain English?**

Use cases describe **how people (and systems) interact with your software**, step by step. The document has four sections:

- **§1 Actor Registry** — who uses the system. Each actor gets an ID (ACT-001, ACT-002). Can be a person (customer, admin) or an external system (payment gateway, email service).
- **§2 Use Cases (UC-NNN)** — each use case is one complete interaction. Every use case has:
  - **Main Path (MP)** — the happy path, step by step, when everything goes right
  - **Alternative Paths (AP)** — valid variations (e.g. user pays by card instead of PayPal)
  - **Exception Paths (EP)** — what happens when something goes wrong (e.g. card declined)
- **§3 Use Case Summary Table** — a quick-reference table of all UCs with their actors and priority
- **§4 Use Case Relationships** — a Mermaid diagram showing which use cases include others (mandatory sub-steps) and which extend others (optional behaviour)

Think of it as a screenplay — every scene (use case) has actors, a normal script, and what happens when things go off-script.

**Where to change it:**
- Document layout and sections: `.specify/templates/use-cases-template.md`  ← in `_shared/full/`, runs sync
- What the AI generates: `.github/prompts/specify-uc.prompt.md`

---

## Step 4 — `/specify-srd` → System Requirements Document

| | |
|---|---|
| **Who** | **Rex** — Requirements Engineer |
| **Output file** | `.specify/features/{feature}/srd.md` |
| **Template** | `.specify/templates/srd-template.md` |
| **Prompt file** | `.github/prompts/specify-srd.prompt.md` |

**What's inside srd.md — in plain English?**

The SRD is the **"what the system must do"** document — the technical translation of the BRD and Use Cases. It has:

- **System Overview** — one paragraph describing what the system does technically
- **Functional Requirements (FR-NNN)** — specific things the system must do ("The system must send a confirmation email within 30 seconds of payment"). Each FR links back to a use case and a business objective.
- **Non-Functional Requirements (NFR-NNN)** — quality standards the system must meet:
  - Performance (e.g. "API response time < 200ms at 1000 concurrent users")
  - Security (e.g. "All data encrypted at rest using AES-256")
  - Availability (e.g. "99.9% uptime")
  - Accessibility, scalability, compliance, etc.
- **Security Design §1** — threat assessment (what could go wrong security-wise)
- **Out of Scope** — explicit list of things this system will NOT do

Think of it as the contract between the business and the development team — a checklist that, if every item is ticked, the system is done.

**Where to change it:**
- Document layout: `.specify/templates/srd-template.md`  ← in `_shared/full/`, run sync
- What the AI generates: `.github/prompts/specify-srd.prompt.md`

---

## Step 5 — `/specify-doc` → Extended Documents (mvp+ only)

| | |
|---|---|
| **Who** | **Ava** — Software Architect |
| **Output files** | `api-spec.md`, `data-model.md`, `security-design.md`, `resilience.md`, `investigation.md` |
| **Template** | `.specify/templates/` — one per doc type |
| **Prompt file** | `.github/prompts/specify-doc.prompt.md` |

**What each extended doc contains — in plain English:**

| Document | What's inside |
|---|---|
| `api-spec.md` | Every API endpoint: URL, method (GET/POST), what you send, what you get back, error codes. The contract between frontend and backend. |
| `data-model.md` | Every database table or data structure: field names, types, relationships between tables, indexes. The blueprint of how data is stored. |
| `security-design.md` | OWASP threat analysis, STRIDE model, authentication design, authorization rules, data protection plan. §1 in pilot, §1-2 in mvp, §1-4 in full. |
| `resilience.md` | How the system handles failure: retry logic, circuit breakers, fallback behaviour, disaster recovery plan. Full scope only. |
| `investigation.md` | Deep-dive into a technical risk or unknown: research findings, proof-of-concept results, recommendation. Full scope only. |

**Where to change it:**
- Prompt file: `.github/prompts/specify-doc.prompt.md` ← covers all doc types via `{name}` parameter
- Templates: `.specify/templates/` — one file per doc type

---

## Step 6 — `/checklist` → Spec Quality Audit

| | |
|---|---|
| **Who** | **Quinn** — QA Lead |
| **Output file** | `.specify/features/{feature}/checklists/{feature}-spec-quality.md` |
| **Template** | `.specify/templates/checklist-template.md` |
| **Prompt file** | `.github/prompts/checklist.prompt.md` |
| **Scope** | Optional for pilot · **Mandatory for mvp and full** |

**What's inside the spec quality checklist — in plain English?**

Quinn reads all your specification documents (BRD, Use Cases, SRD) and raises issues before business sign-off. Issues are graded:

- **CRITICAL** — blocks `/validate` from running. Examples: a functional requirement with no acceptance criteria, an NFR with no measurable number ("the system must be fast" — how fast?), an unresolved [NEEDS CLARIFICATION] marker.
- **HIGH** — must be resolved but doesn't block immediately. Examples: vague words like "scalable" or "secure" with no number attached, a use case with no independent test.
- **MEDIUM** — quality improvements. Examples: terminology used inconsistently across documents, missing out-of-scope statement.
- **LOW** — minor polish items.

Think of it as a proofreader and quality inspector reviewing your spec before it goes to the client.

**Where to change it:**
- Checklist format: `.specify/templates/checklist-template.md`
- What Quinn checks: `.github/prompts/checklist.prompt.md`

---

## Step 7 — `/validate` → Business Sign-Off

| | |
|---|---|
| **Who** | **Maya** — Business Analyst (facilitates review by Product Owner) |
| **Output file** | `.specify/features/{feature}/validate.md` |
| **Template** | `.specify/templates/validate-template.md` |
| **Prompt file** | `.github/prompts/validate.prompt.md` |

**What's inside validate.md — in plain English?**

The validation report is the **formal business sign-off document**. It checks that:

- Every business objective (BO-NNN) from the BRD is addressed by at least one functional requirement
- Every use case has been confirmed by the business stakeholders
- Every NFR has a measurable target (no vague statements)
- All assumptions have been confirmed or escalated
- Open risks are acknowledged

Think of it as a sign-off meeting minutes — the record that the business reviewed and approved the specification before engineering began.

**Where to change it:**
- Layout: `.specify/templates/validate-template.md`
- Logic: `.github/prompts/validate.prompt.md`

---

## Step 8 — `/analyze` → Technical Risk Report

| | |
|---|---|
| **Who** | **Ava** — Software Architect |
| **Output file** | `.specify/features/{feature}/analyze.md` |
| **Template** | `.specify/templates/analyze-template.md` |
| **Prompt file** | `.github/prompts/analyze.prompt.md` |

**What's inside analyze.md — in plain English?**

The analysis report is the **architect's honest assessment** of the technical challenge. It covers:

- **Executive Summary** — overall complexity rating (LOW / MEDIUM / HIGH) and the single biggest risk
- **Complexity Breakdown** — each area (integrations, data, security, performance, team skills) rated separately
- **Risk Register** — every identified technical risk with: probability, impact, mitigation strategy
- **NFR Feasibility** — can the system actually achieve the stated non-functional requirements?
- **Open Questions** — things that need answering before design can begin

Think of it as the honest "here's what could go wrong and how hard this really is" conversation that happens before committing to a design.

**Where to change it:**
- Layout: `.specify/templates/analyze-template.md`
- Logic: `.github/prompts/analyze.prompt.md`

---

## Step 9 — `/clarify` → Clarification Report

| | |
|---|---|
| **Who** | **Rex** — Requirements Engineer |
| **Output file** | `.specify/features/{feature}/clarify.md` |
| **Template** | `.specify/templates/clarify-template.md` |
| **Prompt file** | `.github/prompts/clarify.prompt.md` |

**What's inside clarify.md — in plain English?**

The clarification report lists every **unanswered question and unresolved assumption** from all previous documents. For each one:

- **AMB-NNN** — Ambiguities: two valid ways to interpret something. Shows both options and asks you to pick.
- **ASSUMPTION-NNN** — Things the AI assumed to be true. You confirm or correct each one.
- **DECISION-NNN** — Design decisions that need a human call before the architect can proceed.

Nothing is left as "probably" or "we'll figure it out" — every item gets a firm answer before design begins. A gate (AI-8) blocks `/plan-design` if any ASSUMPTION is still unresolved.

Think of it as a pre-design Q&A session where all grey areas are turned black and white.

**Where to change it:**
- Layout: `.specify/templates/clarify-template.md`
- Logic: `.github/prompts/clarify.prompt.md`

---

## Step 10 — `/plan-design` → Architecture & Design Document

| | |
|---|---|
| **Who** | **Ava** — Software Architect |
| **Output file** | `.specify/features/{feature}/design.md` |
| **Template** | `.specify/templates/design-template.md` |
| **Prompt file** | `.github/prompts/plan-design.prompt.md` |

**What's inside design.md — in plain English?**

This is the **blueprint of how the system will be built**. It is the most technical document in the pipeline. It contains:

- **Architecture Overview** — the overall pattern chosen (microservice, monolith, event-driven, etc.) and why
- **Component Diagram** — a Mermaid diagram showing all the pieces of the system and how they connect
- **Sequence Diagrams** — step-by-step diagrams of how the main use cases flow through the system
- **API Design** — the full API contract: every endpoint, request/response structure, auth model
- **Data Model** — the database schema: tables, fields, relationships
- **Architecture Decision Records (ADRs)** — log of every major design decision, what alternatives were considered, and why this option was chosen
- **NFR Mapping** — how each non-functional requirement (performance, security, etc.) is addressed in the design

Think of it as the architect's drawings — before a single line of code is written, everyone can see exactly what will be built.

**Where to change it:**
- Layout: `.specify/templates/design-template.md`  ← `_shared/full/`, run sync
- Logic: `.github/prompts/plan-design.prompt.md`  ← `_shared/full/`, run sync

---

## Step 11 — `/plan-lld` → Low Level Design (mvp+ only)

| | |
|---|---|
| **Who** | **Leo** — Lead Developer |
| **Output file** | `.specify/features/{feature}/lld.md` |
| **Template** | `.specify/templates/lld-template.md` |
| **Prompt file** | `.github/prompts/plan-lld.prompt.md` |
| **Scope** | **SKIPPED for pilot** · Required for mvp and full |

**What's inside lld.md — in plain English?**

Where `design.md` shows the big picture, the LLD goes one level deeper — it shows exactly how each class/function/component will be written. It contains:

- **Package/Folder Structure** — the exact directory layout of the codebase
- **Class Diagrams** — every class or module, its properties, its methods, and how classes relate to each other
- **Sequence Diagrams (detailed)** — the code-level flow of each use case, showing exactly which method calls which
- **Interface Definitions** — the signatures of every public API within the code (not the HTTP API — the internal code interfaces)
- **Error Handling Strategy** — exactly how errors will be caught, logged, and returned at each layer

Think of it as the detailed engineering drawings — a developer can pick this up and write the code without making any architecture decisions themselves.

**Where to change it:**
- Layout: `.specify/templates/lld-template.md`
- Logic: `.github/prompts/plan-lld.prompt.md`

---

## Step 12 — `/task` → Stories, Tasks, QA Test Cases

| | |
|---|---|
| **Who** | **Kai** — Engineering Manager |
| **Output files** | `stories.md`, `tasks.md`, `qa-testcases.md` (mvp+) |
| **Templates** | `feature-story-template.md`, `plan-template.md`, `qa-testcases-template.md` |
| **Prompt file** | `.github/prompts/task.prompt.md` |

**What's inside each file — in plain English?**

**stories.md** — the work broken down from a user's perspective:
- FEATURE-NNN groups related stories
- STORY-NNN describes one user-facing capability ("As a customer, I can reset my password")
- Each story has acceptance criteria (what "done" looks like from the user's view)

**tasks.md** — the same work broken down from a developer's perspective:
- TASK-NNN is one unit of coding work, typically 2-4 hours
- Each task says which files to create/edit, what tests to write, what the done criteria are
- Tasks are ordered so each one builds on the previous

**qa-testcases.md** (mvp+ only) — the formal test plan:
- TC-NNN is one test case: input, expected output, pass/fail criteria
- Covers happy paths (everything works), unhappy paths (things go wrong), edge cases, security tests
- Marks which tests can be automated and which need manual testing

Think of stories as the "what" (from the user), tasks as the "how" (from the developer), and test cases as "how we know it works" (from QA).

**Where to change it:**
- Story layout: `.specify/templates/feature-story-template.md`
- Task layout: `.specify/templates/plan-template.md`
- QA layout: `.specify/templates/qa-testcases-template.md`
- Logic: `.github/prompts/task.prompt.md`

---

## Step 13 — `/implement` → Code

| | |
|---|---|
| **Who** | **Leo** — Lead Developer |
| **Output** | Actual source code files in your project |
| **Template** | No template — code is generated from `tasks.md` + `constitution.md` |
| **Prompt file** | `.github/prompts/implement.prompt.md` |

**What happens — in plain English?**

Leo picks up one task at a time from `tasks.md`, reads the design document and constitution, and writes the code exactly as specified. For each task:
- Creates or edits source files
- Writes unit tests alongside the code
- Follows the coding standards in `.github/instructions/*.instructions.md`
- Reports which files were changed and how many lines

**Where to change it:**
- Coding standards: `.github/instructions/*.instructions.md` in each pack
- What Leo does during implement: `.github/prompts/implement.prompt.md`

---

## Step 14 — `/pre-review` → AI Code Review

| | |
|---|---|
| **Who** | **Leo** — Lead Developer (self-review before human review) |
| **Output file** | `.specify/features/{feature}/.pre-review-{task}.md` |
| **Template** | No template |
| **Prompt file** | `.github/prompts/pre-review.prompt.md` |

**What happens — in plain English?**

Before creating a pull request, Leo reviews his own code and raises a numbered checklist of findings across four areas: correctness (does it do what the task says?), security (any vulnerabilities?), quality (is it readable, maintainable?), and performance (any obvious bottlenecks?). You pick which findings to fix, Leo applies them, then the PR is created.

---

## Step 15 — `/release` → Release Plan

| | |
|---|---|
| **Who** | **Riley** — Release Manager |
| **Output file** | `.specify/features/{feature}/release.md` |
| **Template** | No dedicated template |
| **Prompt file** | `.github/prompts/release.prompt.md` |

**What's inside release.md — in plain English?**

The release document covers everything needed to safely go live:

- **UAT Plan** — what needs to be tested by real users before release, with pass/fail criteria
- **Deployment Steps** — the exact sequence of actions to deploy: database migrations, config changes, feature flags, rollout order
- **Rollback Plan** — if something goes wrong after go-live, exactly what to do to undo it
- **Monitoring Plan** — what metrics to watch in the first 48 hours after release, and what alerts to set
- **Go-Live Gate** — a checklist: all tasks merged ✅, UAT passed ✅, runbook signed off ✅, stakeholder approval ✅

Think of it as the flight plan for launch day.

---

## Supporting Documents (generated alongside the main pipeline)

### Change Request — `/change`
| | |
|---|---|
| **Who** | **Maya** (business) + **Leo** (technical) working together |
| **Output** | `changesets/CR-{NNN}.md` |
| **Template** | `.specify/templates/changeset-template.md` |

**Plain English:** When something needs to change after a document is approved, a change request tracks what changes, why, which documents are affected, and what was re-generated. It's an audit trail so you always know what changed and when.

### Architecture Decision Record — `/plan-design` (generates inside design.md)
| | |
|---|---|
| **Template** | `.specify/templates/adr-template.md` |

**Plain English:** Every time a major architectural decision is made (e.g. "we chose PostgreSQL instead of MongoDB"), an ADR records the context, the options considered, and why this choice was made. Future developers can read it to understand why the system is built the way it is.

### Jira Export — `/taskstoissues`
| | |
|---|---|
| **Who** | **Kai** — Engineering Manager |
| **Template** | `.specify/templates/jira-export-template.md` |

**Plain English:** Takes `stories.md` and `tasks.md` and formats them as an Epic → Story → Task hierarchy ready to be imported directly into Jira or GitHub Issues.

### Jira API Push — `/jira-push`
| | |
|---|---|
| **Who** | **Morgan** — Delivery Manager |
| **Script** | `.specify/scripts/jira-push.py` (standalone — also runs from CI/CD, no AI session needed) |
| **Config** | `.specify/jira-config.yml` (copy from `.specify/templates/jira-config-template.yml`) |
| **Keys tracking** | `docs/jira/keys.yml` |

**Plain English:** Unlike `/taskstoissues` (which produces a CSV for manual import) or `sdd jira push` (which pushes Story+Task together, once, after `/task`), `/jira-push` calls the Jira REST API directly and progressively — Epic after BRD approval, Stories after Use Cases/SRD approval, Tasks after `/task` approval, CHG tasks after `/change` approval. Field mapping (custom field IDs, per-level project keys/issue types, parent-link strategy) lives in `jira-config.yml`. Bare shorthand works: `/jira-push epic`, `/jira-push story`, `/jira-push task`, or full flag syntax `/jira-push --level all --dry-run`.

---

## Where Everything Lives — Quick Reference

| To change… | Edit this file | Then run… |
|---|---|---|
| Any document's layout/sections | `.specify/templates/{name}-template.md` in `_shared/full/` | `bash packs/_shared/sync-blocks.sh` |
| What any command does | `.github/prompts/{cmd}.prompt.md` in `_shared/full/` | `bash packs/_shared/sync-blocks.sh` |
| Persona routing (Maya, Ava, etc.) | `.github/prompts/{name}.prompt.md` in `_shared/full/` | `bash packs/_shared/sync-blocks.sh` |
| Gate rules (what blocks what) | `packs/_shared/blocks/command-gates.md` | `bash packs/_shared/sync-blocks.sh` |
| Never Do rules | `packs/_shared/blocks/never-do-core.md` | `bash packs/_shared/sync-blocks.sh` |
| Scope table (pilot/mvp/full) | `packs/_shared/blocks/scope-reference.md` | `bash packs/_shared/sync-blocks.sh` |
| Virtual team roster | `packs/_shared/blocks/team-routing.md` | `bash packs/_shared/sync-blocks.sh` |
| Tech stack rows (per pack) | `.github/prompts/specify.prompt.md` inside each pack | No sync — edit each pack individually |
| Coding standards | `.github/instructions/*.instructions.md` inside each pack | No sync — pack-specific |
