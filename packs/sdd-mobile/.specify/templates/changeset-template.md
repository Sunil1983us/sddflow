# Change Request — CR-{NNN}
# Feature: {Feature Name}
> Raised at stage: {/specify-brd | /specify-uc | /specify-srd | /validate | /analyze | /clarify | /plan-design | /plan-lld | /task | /implement | post-release}
> Date: {date} | Raised by: {role}
> Type: {Business | Technical | Security | Data | UX | Performance | Operational | Defect}
> Status: OPEN → IN PROGRESS → COMPLETE

---

## 1. Change Description

{Plain-language description of what needs to change and why.}

| Dimension | Value |
|---|---|
| Primary type | {Business / Technical / Security / Data / UX / Performance / Operational / Defect} |
| Secondary type | {type — or —} |
| Trigger | {what caused this: BA discovery / stakeholder request / design finding / risk analysis / code review} |
| Urgency | {Blocks current stage / Can be deferred to next task / Non-blocking} |
| Scope of impact | {Minor — sections only / Moderate — new documents / Major — architecture or constitution change} |
| Feature renamed | {old-slug} → {new-slug} — or "No" |

---

## 2. Document Walk Results

> Agent reads each existing filled document in dependency order. Not-yet-created documents are marked INCORPORATE — the CR is built in when that document is generated.

| # | Document | Exists? | Action | Sections Affected | Approved |
|---|---|---|---|---|---|
| 1 | context.md (`.specify/contexts/`) | Yes / No | SKIP / ANNOTATE / UPDATE / RERUN / INCORPORATE | {sections or —} | [ ] / — |
| 2 | constitution.md (Part 2) | Yes / No | {action} | {sections or —} | [ ] / — |
| 3 | brd.md | Yes / No | {action} | {sections or —} | [ ] / — |
| 4 | use-cases.md | Yes / No | {action} | {sections or —} | [ ] / — |
| 5 | srd.md | Yes / No | {action} | {sections or —} | [ ] / — |
| 6 | security-design.md (living — `.specify/service/`) | Yes / No | {action} | {sections or —} | [ ] / — |
| 7 | api-spec.md (living — `.specify/service/`, if this pack provides an API) | Yes / No | {action} | {sections or —} | [ ] / — |
| 8 | data-model.md (living — `.specify/service/`) | Yes / No | {action} | {sections or —} | [ ] / — |
| 9 | validate.md | Yes / No | {action} | {sections or —} | [ ] / — |
| 10 | analyze.md | Yes / No | {action} | {sections or —} | [ ] / — |
| 11 | clarify.md | Yes / No | {action} | {sections or —} | [ ] / — |
| 12 | design.md | Yes / No | {action} | {sections or —} | [ ] / — |
| 13 | lld.md | Yes / No | {action} | {sections or —} | [ ] / — |
| 14 | qa-testcases.md | Yes / No | {action} | {sections or —} | [ ] / — |
| 15 | tasks.md | Yes / No | {action} | {sections or —} | [ ] / — |

**Action legend:**
- **SKIP** — CR has no impact on this document (reason stated per row)
- **ANNOTATE** — Upstream approved document: a CR reference note is added but the document is not revised
- **UPDATE** — Targeted section change applied; before/after recorded in §3
- **RERUN** — Document regenerated with CR incorporated; backup saved as `{doc}.pre-CR-{NNN}.md`
- **INCORPORATE** — Document not yet created; CR is automatically built in when that document is generated

**Ripple-Forward Rule:** Documents earlier in the chain that are already approved are ANNOTATED only (not re-approved unless the CR directly invalidates them). Documents later in the chain that are not yet created will INCORPORATE the CR automatically.

**Cross-feature impact (living documents only, rows 6–8):** if the unit
being changed in a living document was last touched by a *different*
feature than the one raising this CR, note it in that row's "Sections
Affected" cell, e.g. `§4 Endpoints (cross-feature: instant-payment)` — see
`change.prompt.md`'s living-document special handling.

---

## 3. Document Changes (before / after for every UPDATE or RERUN)

### {document name} — UPDATE

**Section:** {section heading — e.g. §3 UC-005, §2 FR-012}

**Before (existing content of section):**
```
{exact current text — copy from the live document}
```

**After (proposed change):**
```
{exact proposed new text — only this section, not the full document}
```

**Reason:** {why this specific section needs to change given the CR type and description}

**Approved by:** {role} on {date}

---

_(repeat §3 block for each document that receives UPDATE or RERUN action)_

---

## 4. CHG-NNN Implementation Tasks

> Populated after all affected spec documents are updated. Each CHG represents implementation work created by this CR.

| CHG-NNN | Description | Satisfies | Estimated Lines | PR | Status |
|---|---|---|---|---|---|
| CHG-{NNN} | {what to implement} | FR-{NNN} / NFR-{NNN} / CR-{NNN} | ~{N} | single / SPLIT | Pending |

> If tasks.md already exists: CHG-NNN rows are appended under `## Change Set: CR-{NNN} — {date}`.
> If tasks.md not yet created: these tasks are incorporated when `/task` runs.

---

## 5. Approvals

| Role | Decision | Date |
|---|---|---|
| {Raised by role} | CR accepted — walk approved to proceed | |
| {Accountable role per gate for each updated doc} | Document updates reviewed and signed off | |
| Tech Lead | CHG-NNN tasks scoped and approved | |
