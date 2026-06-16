# Summary Rules
SUMMARY_MAX_LINES: 20
READING_MODE: auto
# pilot:15-20 | mvp:20-25 | full:25-35
# READING_MODE: auto | summary | full   DEFAULT: auto
#   auto:    use .summary.md when present; fall back to full .md if missing,
#            then generate summary immediately (keeps AI-2 on track)
#   summary: always use .summary.md; warn if missing (strict token economy)
#   full:    always read full .md (deep debugging / initial migration only)
# Override per project via manifest.yml → reading_mode
# To change: edit these values, tell agent: "re-read summary-rules.md"

## AI-2 — Summary-First Rule (token economy, mandatory)
After /specify, every command reads `.summary.md` files for prior
documents. The exact behaviour depends on `reading_mode` (see below).
This keeps token usage roughly constant per command regardless of how many
documents exist (see docs/SUMMARY-GUIDE.md → "What Each Verb Reads").

Exception: /implement always reads `tasks.md` (current task only, in full)
+ `constitution.md` (in full) — both required for correct code generation
and never summarized — regardless of reading_mode.

## AI-2 — Reading Mode Decision Tree
Effective reading_mode = `manifest.yml → reading_mode` if set; else
`READING_MODE` at the top of this file.

**auto (default):**
1. `.summary.md` exists → read it. Done.
2. `.summary.md` missing → read full `.md` instead, then immediately
   generate and save `.summary.md`. State: "No summary found for {doc} —
   read full document and generated {doc}.summary.md." Continue.
3. Agent needs more detail than the summary contains → ask:
   "I have {doc}.summary.md but may need the full document to {reason}.
   Read it? (y/n)" — read only on 'y'; note any new detail found.

**summary:**
1. `.summary.md` exists → read it. Done.
2. `.summary.md` missing → warn: "WARNING: {doc}.summary.md not found —
   run the command that generates it first, or set reading_mode: auto
   in manifest.yml." Do NOT read the full doc without user approval.

**full:**
Always read the full `.md`. Log: "[reading_mode=full] reading {doc}.md".
Use only for deep debugging or migrating a project that has no summaries.

## .raw.md Files — Never Read (AI-2 exception)
`.specify/contexts/{feature}.raw.md`, if present, holds a user's original
unformatted notes saved by `/create-context`. It is reference-only — no
command (including /specify) ever reads it. Only `/create-context` reads
it, and only if the user re-runs that command to regenerate context.md.

## Required Fields Per Document (mandatory — completeness floor)
These items MUST appear in every summary regardless of line budget.
Rule: if lines are tight, compress narrative prose — never drop identifiers.
Section heading names are the canonical anchors — §N numbers are examples
and may shift if a template gains new sections.

### brd.summary.md
- All BO-NNN + success metric (Business Objectives)
- In Scope vs Out of Scope boundary (Business Context)
- All BR-NNN + priority (Business Requirements)
- Regulatory constraints that affect design (Regulatory and Compliance)
- Any unresolved [ASSUMPTION-NNN] (Assumptions)
- Success criteria

### srd.summary.md
- Every FR-NNN + priority (Functional Requirements) — list all, no grouping
- Every NFR-NNN + threshold value e.g. "NFR-001 P99 ≤ 500ms" (Non-Functional Requirements)
- All integrations + direction + mock/real phase (Integrations)
- All constraints (Constraints)

### validate.summary.md
- Outcome: "VALIDATE complete" or "INCOMPLETE — {N} items outstanding" (Outcome)
- Any BR-NNN where SRD reflection was marked No (Business Requirements Review)
- Any ASSUMPTION-NNN not confirmed by business owner (Assumptions Sign-Off)

### analyze.summary.md
- Overall complexity rating: LOW / MEDIUM / HIGH (Executive Summary)
- ALL R-NNN rated High or Critical: ID + impact + mitigation (Risk Register)
- All blocking dependencies: system + owner (Dependency Map)
- All feature areas rated HIGH complexity (Complexity Assessment)
- All NFR-NNN that force an architectural decision (NFR Impact Analysis)
- All U-NNN requiring spike work (Unknowns)
- /clarify items + tasks flagged for SPLIT (Recommendation)
- Count of CRITICAL CF-NNN consistency findings (Consistency Findings) — 0 means clean
- Any constitution conflicts found (CF-NNN rated CRITICAL)

### clarify.summary.md
- Status: "CLARIFY complete — all RESOLVED" or "INCOMPLETE — {N} OPEN"
- All R-NNN items: title + answer (or "OPEN")
- Item count by type (AMB / GAP / CON / ASM / OQ) + how many OPEN
- Spec docs updated as a result of answers

### arch.summary.md
- Architecture pattern chosen (Architecture Overview)
- All DEC-NNN: decision + one-line rationale (Key Design Decisions)
- All NFR-NNN → DEC-NNN mappings (NFR Architecture Decision Mapping)
- All layers named with folder/package (Layer Responsibilities)
- Cross-cutting concerns: auth + logging + error handling

### plan.summary.md
- Implementation phases in order (Implementation Order)
- Test framework per layer (Test Strategy)
- All delivery checklist items (Delivery Checklist)

### hld.summary.md
- All integrations: system + direction (System Context)
- All state machine states (Status / State Machine)
- All NFR targets: ID + threshold (Non-Functional Summary)
- Out of scope items

### lld.summary.md
- Full package / folder structure (Package Structure)
- All class/interface names per layer
- Key method signatures (use-case interface + service + adapters)

### adr.summary.md (one entry per ADR file)
- ADR-NNN title + status + linked DEC-NNN
- Chosen option + one-line rationale
- Key risks / consequences

### api-spec.summary.md
- All endpoints: HTTP method + path + auth requirement
- Request / response schema names
- All documented error codes + meanings

### data-model.summary.md
- All entity / table names + purpose
- Key relationships (foreign keys, ownership)
- Constraints affecting design (unique keys, audit fields)

### security-design.summary.md
- All THR-NNN rated Medium / High: description + mitigation
- Security controls applied by layer
- Any open gaps / deferred controls

### resilience.summary.md
- All retry strategies: target + backoff policy
- All circuit breaker thresholds
- Timeout values per integration
- Degraded-mode behaviour (graceful degradation vs hard fail)

### investigation.summary.md
- All alert names + thresholds that trigger an incident
- Key runbook triage steps (ordered)
- Key dashboards / metrics to check first

### stories.summary.md
- All STORY-NNN: title + story points + sprint assignment
- All acceptance criteria linked to FR-NNN per story

### tasks.summary.md
- All TASK-NNN: estimated lines + PR strategy (single / SPLIT A/B/C)
- Total estimated lines + count of SPLIT tasks

### qa-testcases.summary.md
- All TC-NNN identifiers grouped by category (Test Coverage Summary)
- Coverage count per category
- FR-NNN → TC-NNN traceability (which FRs are covered)

### Pack-specific spec documents
component-spec, screen-spec, ux-flow, and similar — all typed identifiers
must survive compression; compress prose only.
