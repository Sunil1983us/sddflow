# Summary Rules
SUMMARY_MAX_LINES: 20
# pilot:15-20 | mvp:20-25 | full:25-35
# Format: What → Key Decisions → Key Artifacts → Constraints → Out of Scope
# To change: edit SUMMARY_MAX_LINES, tell agent: "re-read summary-rules.md"

## AI-2 — Summary-First Rule (token economy, mandatory)
After /specify, every command reads ONLY `.summary.md` files for prior
documents — never the full `.md`. This keeps token usage roughly constant
per command regardless of how many documents exist (see
docs/SUMMARY-GUIDE.md → "What Each Verb Reads").

Exception: /implement reads `tasks.md` (current task only, in full) +
`constitution.md` (in full) — both are required for correct code
generation and are not summarized.

If a command needs detail beyond a summary, it should ask the user
whether to read the full document rather than reading it by default.

## .raw.md Files — Never Read (AI-2 exception)
`.specify/contexts/{feature}.raw.md`, if present, holds a user's original
unformatted notes saved by `/create-context`. It is reference-only — no
command (including /specify) ever reads it. Only `/create-context` reads
it, and only if the user re-runs that command to regenerate context.md.

## Required Fields Per Document (mandatory — completeness floor)
These items MUST appear in every summary regardless of line budget.
Rule: if lines are tight, compress narrative prose — never drop identifiers.

### brd.summary.md
- All BO-NNN + success metric (§2)
- In Scope vs Out of Scope boundary (§4)
- All BR-NNN + priority (§5)
- Regulatory constraints that affect design (§6)
- Any unresolved [ASSUMPTION-NNN] (§7)
- Success criteria (§8)

### srd.summary.md
- Every FR-NNN + priority (§2) — list all, no grouping
- Every NFR-NNN + threshold value (§3) e.g. "NFR-001 P99 ≤ 500ms"
- All integrations + direction + mock/real phase (§5)
- All constraints (§7)

### validate.summary.md
- Outcome statement: "VALIDATE complete" or "INCOMPLETE — {N} items" (§6)
- Any BR-NNN where SRD reflection was marked No (§2)
- Any ASSUMPTION-NNN not confirmed by business owner (§3)

### analyze.summary.md
- Overall complexity rating: LOW / MEDIUM / HIGH (§1)
- ALL R-NNN rated High or Critical: ID + impact + mitigation (§2)
- All blocking dependencies: system + owner (§3)
- All feature areas rated HIGH complexity (§4)
- All NFR-NNN that force an architectural decision (§5)
- All U-NNN requiring spike work (§6)
- /clarify items + tasks flagged for SPLIT (§7)

### clarify.summary.md
- Status: "CLARIFY complete — all RESOLVED" or "INCOMPLETE — {N} OPEN"
- All R-NNN items: title + answer (or "OPEN")
- Item count by type (AMB / GAP / CON / ASM / OQ) + how many OPEN
- Spec docs updated as a result of answers

### arch.summary.md
- Architecture pattern chosen (§1)
- All DEC-NNN: decision + one-line rationale (§4)
- All NFR-NNN → DEC-NNN mappings (§4a)
- All layers named with folder/package (§3)
- Cross-cutting concerns: auth + logging + error handling

### plan.summary.md
- Implementation phases in order (§2)
- Test framework per layer (§3)
- All delivery checklist items (§6)

### hld.summary.md
- All integrations: system + direction (§1-2)
- All state machine states (§4)
- All NFR targets: ID + threshold (§7)
- Out of scope items (§8)

### stories.summary.md
- All STORY-NNN: title + story points + sprint assignment
- All acceptance criteria linked to FR-NNN per story

### tasks.summary.md
- All TASK-NNN: estimated lines + PR strategy (single / SPLIT A/B/C)
- Total estimated lines + count of SPLIT tasks

### qa-testcases.summary.md
- All TC-NNN identifiers grouped by category (§2–§6)
- Coverage count per category (§1 table)
- FR-NNN → TC-NNN traceability (which FRs are covered)
