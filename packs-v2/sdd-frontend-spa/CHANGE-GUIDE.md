# Change Management Guide
# How Changes Work in the SDD Framework

---

## The Fundamental Rule

> Never change code directly.
> Update context.md first.
> Let the pipeline propagate.

---

## The 3 Types of Change

### Type 1 — Additive (new field, new rule, new endpoint)
Something new added. Existing behaviour unchanged.
```
Example: Add new field to response
Example: Add new endpoint
Example: Add new status/state
```

### Type 2 — Modification (change existing behaviour)
Existing behaviour changes. May affect consumers.
```
Example: Change timeout value
Example: Change business rule logic
Example: Rename a status
```

### Type 3 — Scope Upgrade
New capability cluster added.
```
Example: pilot → mvp (add resilience, LLD, ADRs)
Example: Add investigation cases
Example: Add new integration
```

---

## The Change Workflow

```
C1  Update context.md + CHANGELOG entry
        ↓
C2  Impact analysis (which docs affected?)
        ↓
C3  Review gate — YOU approve impact list
        ↓
C4  Update ONLY affected documents
        ↓
C5  Append CHG-NNN tasks to tasks.md
        ↓
C6  Implement CHG tasks (same PR rules)
```

---

## C1 — Update Context First

```markdown
## CHANGELOG

### v1.1 — {date} — {author}
- Added: {new capability}
- Changed: {what changed and why}
- Removed: {what removed}
- Impact: {which documents need updating}
```

Also update the relevant section of context.md.

---

## C2 — Impact Analysis

### Claude Code
```
Read .specify/memory/change-rules.md
Read .specify/contexts/{feature}.md — focus on latest CHANGELOG

Perform impact analysis:
  List documents to UPDATE (with reason)
  List documents to SKIP
  List new CHG-NNN tasks needed
  Estimate total lines + PRs

Do NOT change anything yet — analysis only.
```

### Copilot
```
@workspace Read change-rules.md + contexts/{f}.md changelog
Impact analysis only — list update/skip/tasks.
```

**Example output:**
```
CHANGE: Add X-Priority header support
VERSION: v1.1

DOCS TO UPDATE:
  ✅ srd.md       — add FR-016
  ✅ api-spec.md  — add header to all endpoints
  ⏭ arch.md      — not affected
  ⏭ hld.md       — not affected
  ⏭ data-model   — not affected

NEW TASKS:
  CHG-001: Add X-Priority to request record — est 20 lines
  CHG-002: Update service to propagate header — est 40 lines
  CHG-003: Update integration tests — est 60 lines

TOTAL: 2 docs, 3 tasks, ~120 lines, 3 PRs
```

---

## C3 — Review Gate

Review impact list before agent touches anything:
- Right documents selected?
- Correct tasks identified?
- Estimate reasonable?

Type "go" to proceed. Type "adjust: {what}" to correct.

---

## C4 — Update Documents

### Claude Code
```
Read change-rules.md + contexts/{f}.md (v{N.N} changes only)
Update ONLY: {list from impact analysis}
Preserve all existing content
Mark each change: <!-- v{N.N} -->
Regenerate .summary.md for each updated doc
Show diff summary: "{doc}.md — {N} lines added in section {X}"
```

---

## C5 — Add Change Tasks

```
Read tasks.md
Append at bottom:

## Change Set: v{N.N} — {date} — {description}

### CHG-001: {title}
Satisfies: FR-{NNN} (updated)
Estimated lines: {N} | PR: single
Acceptance criteria:
  - [ ] {criterion}
```

---

## C6 — Implement CHG Tasks

Same as normal /implement — one task at a time.
PR rules enforced. Max 400 lines per PR.

---

## Which Commands to Re-Run Per Change Type

| Change | Re-run Commands |
|---|---|
| New field in request/response | /specify (api-spec only, mvp+) → /plan-arch (refine) → /task |
| New endpoint | /specify (srd + api-spec) → /plan-arch (refine + if structural) → /task |
| New status/state | /specify (srd + api-spec + data-model) → /plan-hld (update diagram) → /task |
| New business rule | /specify (srd) → /task |
| Architecture change | /specify + /plan-arch + /plan-hld → /task |
| New integration | /specify + /analyze (re-run) + /plan-arch → /task |
| New security control / regulation | /specify (security-design) → /plan-arch (refine) → /release (regulatory trace) |
| Scope upgrade | See scope upgrade section below |

AI-8 applies on re-runs too: if any updated doc gets a new
`[ASSUMPTION-NNN]`, run /clarify before /plan-arch.

---

## Scope Upgrade

```
Edit manifest.yml: scope: "pilot" → "mvp"

Tell agent:
"Scope upgraded to mvp. Re-read manifest.yml.
 Run /specify for newly enabled docs only: component-spec, ux-flow,
   api-spec, security-design (§2 additions)
 Run /plan-arch to refine the newly generated docs against arch.md
 Run /plan-lld (now enabled)
 Run /plan-adr (now enabled)
 Update /task with new tasks"
```

Scope upgrade to full additionally triggers /plan-arch refine of
component-spec, ux-flow, api-spec, data-model, resilience, investigation,
and security-design (§3-4) as applicable per scope.

Optional: if `.specify/contexts/{feature}.raw.md` exists (saved by an
earlier `/create-context` run) and the new scope needs information that
was previously marked `[MISSING — ask user]`, re-run `/create-context` —
it will re-read context.md + the raw notes and re-prompt only for the
gaps relevant to the new scope.

---

## Change Impact By Document

| Change Type | Update | Skip |
|---|---|---|
| New field | api-spec | srd, arch, hld, data-model |
| New endpoint | srd + api-spec + lld | arch, hld, data-model |
| New status | srd + api-spec + data-model + hld | arch, lld |
| New business rule | srd | all others |
| New DB table | data-model + arch + lld | srd, api-spec, hld |
| NFR change | srd + resilience | all others |
| New integration | srd + arch + api-spec + lld + analyze | hld, data-model |
| New security control / regulation | security-design + srd | arch, hld, data-model |
| Bug fix / refactor | none | all (code only) |

Every change above must also be reflected in /release §6 (Business
Objective Closure) if it affects a BO-NNN metric, and in /release §2
(UAT Plan) if it adds a new UC-NNN.

---

## Git Conventions for Changes

```bash
# Document updates
git commit -m "docs(v1.1): update srd + api-spec for X-Priority"

# Change implementation
git commit -m "feat(CHG-001): add X-Priority to request record"
git commit -m "feat(CHG-002): propagate X-Priority through service"
git commit -m "test(CHG-003): update integration tests for X-Priority"
```

---

## What NEVER Changes on a Change Request

- constitution.md Part 1
- All templates (including validate-template, release-template,
  runbook-template, security-design-template)
- CLAUDE.md + copilot-instructions.md
- roles.yml (unless reviewer/owner assignments change)
- Documents NOT in the impact chain
- Summary-rules.md (unless limit needs adjusting)
