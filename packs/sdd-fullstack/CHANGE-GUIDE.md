# Change Management Guide
# How Changes Work in the SDD Framework

---

## The Fundamental Rule

> A change request can be raised at ANY stage by ANY role.
> Run /change — the agent reads existing documents one by one,
> shows only what needs updating, and waits for your approval
> before touching the next document.

---

## The /change Command

```
/change "describe the change — what needs to change, why, and who is raising it"
```

Examples:
```
/change "BA discovered a missing retry requirement for payment gateway 402 errors"
/change "security team requires field-level encryption for card numbers — PCI finding"
/change "wrong response shape in UC-003 — payload has orderId not order_id"
/change "scope upgrade from pilot to mvp — add api-spec and data-model (both living, service-level)"
```

**On a multi-feature project — which feature does the CR target?**
By default, `/change` always targets whichever feature `.specify/manifest.yml → project.feature` currently names — it never asks you to pick, and it never scans other features to guess. If you need to raise a CR against a *different* feature without first editing `manifest.yml` (and remembering to switch it back), use:
```
/change --feature payments-dashboard "add a discount field to the Payment entity"
```
This targets `payments-dashboard` for this one CR only — `manifest.yml` is never read or written for feature selection in this mode, so every other command you run afterward is unaffected. If the named feature doesn't exist under `.specify/features/`, the agent stops and lists the features it actually found, rather than silently falling back to the manifest default. The registered-CR message always states which feature was targeted, so you can confirm it before the document walk starts.

The agent:
1. **Classifies** the CR type (one of 8 — see table below)
2. **Detects current stage** from documents that exist — most live at
   `.specify/features/{feature}/`, but `context.md` is always at
   `.specify/contexts/{feature}.md`, and `security-design.md`/`api-spec.md`/
   `data-model.md`/`component-library.md` are **living documents** shared
   across every feature in this service, at `.specify/service/{doc}.md` —
   see "Living Documents & Cross-Feature Impact" below
3. **Presents a walk plan** — which documents to check in dependency order
4. **Walks each document** one at a time — reads it, then decides:
   - **SKIP** — CR has no impact; states reason; moves on immediately
   - **ANNOTATE** — upstream approved document; adds CR reference note; moves on
   - **UPDATE** — shows BEFORE / AFTER diff for the affected section only; **STOPS and waits for your approval**
   - **RERUN** — major structural impact; explains why; saves backup; **STOPS and waits for confirmation**
   - **INCORPORATE** — document not yet created; CR built in automatically when generated
5. After all documents: proposes **CHG-NNN implementation tasks**
6. Saves changeset record: `.specify/features/{feature}/changesets/CR-NNN.md`

---

## CR Types

| Type | Raise when | Primary documents affected |
|---|---|---|
| Business | Missing requirement, wrong rule, scope change, new stakeholder | context → brd → use-cases → srd → validate |
| Technical | New integration, tech stack change, architecture decision | context → constitution → design → lld |
| Security | New regulation, vulnerability, compliance gap | context → brd §6 → srd (NFR) → security-design |
| Data | New field, new entity, schema change, payload change | context → data-model (living) → srd → api-spec (living) → design |
| UX | New screen, flow change, accessibility gap | context → use-cases → srd → design |
| Performance | New NFR, SLA change, load target | context → srd (NFR) → analyze → resilience |
| Operational | Deployment change, config change, runbook update | context → constitution → design → runbook |
| Defect | Wrong spec, contradiction, error in existing document | from defect location forward in chain |

---

## Ripple-Forward Rule

A CR only affects documents **downstream** from where it is raised.

- Documents **upstream** (already approved) → **ANNOTATE** only; never re-opened unless the CR directly invalidates them
- Documents **downstream** (already created) → walk and assess (UPDATE or SKIP)
- Documents **not yet created** → **INCORPORATE** automatically when generated

---

## Document Dependency Chain

```
context.md → brd → use-cases → srd → security-design → api-spec → data-model
→ validate → analyze → clarify → design → lld → qa-testcases → tasks → release
```

**Real file locations:** `context.md` is always at `.specify/contexts/{feature}.md`.
`security-design.md`, `api-spec.md`, `data-model.md`, and
`component-library.md` are **living documents** — shared across every
feature in this service, at `.specify/service/{doc}.md`, not one copy per
feature. Every other document in the chain above is per-feature, as
shown.

---

## Living Documents & Cross-Feature Impact

Because `security-design.md`, `api-spec.md`, `data-model.md`, and
`component-library.md` are shared, a CR raised against one feature can
change a unit (an endpoint, a table, a threat entry, a shared component)
that a **different** feature also depends on — and that other feature's
own `srd.md`/`design.md` are never read during a normal `/change` walk,
since the walk is scoped to the feature that raised the CR.

Before `/change` approves an UPDATE/RERUN to a living document, it checks
that document's `## Version History` table to see which feature last
touched the specific unit being changed. If it's a **different** feature
than the one raising this CR, the proposal includes a warning like:

```
⚠ Cross-feature impact: {unit} was added/last changed by {other-feature}.
This CR is raised against {current-feature}, but {other-feature}'s own
srd.md/design.md may depend on {unit}'s current shape. Check before
approving — that feature may need its own CR too.
```

This is **advisory, not a hard block** — you decide whether the sibling
feature needs its own CR. If the unit was last touched by the *same*
feature raising the CR, no warning appears; this only fires on genuine
cross-feature risk.

---

## The 3 Types of Change (what triggers a CR)

### Type 1 — Additive (new field, new rule, new endpoint, missing requirement)
Something new that was not in scope before. Existing behaviour unchanged.

### Type 2 — Modification (change existing behaviour)
Existing behaviour changes. May affect consumers, test cases, or API contracts.

### Type 3 — Scope Upgrade
New capability cluster added (e.g. pilot → mvp adds api-spec/data-model
— both living, at `.specify/service/` — component-spec, ux-flow, LLD).

For scope upgrades, update `manifest.yml` first, then run `/change "scope upgraded from pilot to mvp"`.

---

## What /change Produces

After the walk completes, you get:
- **Updated documents** — only the sections that needed changing, with your approval on each
- **CHG-NNN tasks** — implementation work created by the CR, appended to `tasks.md`
- **Changeset record** — `CR-NNN.md` in `.specify/features/{feature}/changesets/` with full walk log, BEFORE/AFTER diffs, and approvals

---

## Quality Check Options (at each UPDATE)

When the agent shows a BEFORE/AFTER diff, reply with one of:
- **`approved`** — apply this change and continue to the next document
- **`modify: {your text}`** — apply your version instead, then continue
- **`skip`** — leave this document unchanged and continue
- **`stop`** — pause the walk here (resume with `/change resume CR-NNN`)

---

## Which Documents Are Typically Affected

| Change | Primary documents to update |
|---|---|
| New field in request/response | api-spec (living — check cross-feature impact) |
| New endpoint | use-cases + srd + design + lld |
| New actor or use case | use-cases + srd |
| New status/state | srd + api-spec + data-model (both living — check cross-feature impact) |
| New business rule | srd |
| New DB table | data-model (living — check cross-feature impact) + design + lld |
| New shared component | component-spec + component-library (living — check cross-feature impact) |
| NFR change | srd + resilience |
| New integration | srd + design + api-spec (living) + lld + analyze |
| New security control / regulation | security-design (living — check cross-feature impact) + srd |
| Scope upgrade | manifest + newly enabled docs (INCORPORATE if new, EXTEND via walk-and-diff if a living doc already exists from a prior feature) |
| Bug fix / refactor | code only (CHG task, no doc update) |

> Rows marked "living" go through the cross-feature impact check described
> above — the agent checks Version History, not just this feature's own
> docs, before approving a change.

---

## After /change: Implement CHG Tasks

CHG-NNN tasks created by the CR are appended to `tasks.md` under:
```
## Change Set: CR-NNN — {date}
```

Implement them the same way as regular TASK work:
- One CHG task per PR (same line + file limits apply)
- Same PR rules: estimate → code → pre-review → PR → human review → merge

---

## Git Conventions for Changes

```bash
# Document updates (applied by /change)
git commit -m "docs(CR-001): update srd + api-spec for payment retry requirement"

# CHG task implementation
git commit -m "feat(CHG-001): add retry logic for 402 responses in payment gateway"
git commit -m "test(CHG-002): add integration tests for payment retry flow"
```

---

## Scope Upgrade Example

```
# 1. Edit manifest.yml
scope: "mvp"

# 2. Run /change
/change "scope upgraded from pilot to mvp — need api-spec, data-model, component-spec, ux-flow, LLD"

# 3. /change will:
#    - ANNOTATE upstream docs (context, brd, use-cases, srd, security §1)
#    - INCORPORATE api-spec, data-model, component-spec, ux-flow if this is
#      the first feature in the service to need them (or, if a prior
#      feature already created .specify/service/api-spec.md /
#      data-model.md / component-library.md, EXTEND them via the
#      SKIP/ADD-unit/UPDATE-unit walk instead — never re-INCORPORATE an
#      existing living document)
#    - UPDATE design.md to add LLD-scope sections
#    - INCORPORATE lld (not yet created)
#    - Propose CHG-NNN tasks for the new scope work
```

---

## What NEVER Changes on a Change Request

- `constitution.md` Part 1
- All templates (including security-design, runbook, validate, release, use-cases, openapi)
- `CLAUDE.md` + `copilot-instructions.md`
- `roles.yml` (unless reviewer/owner assignments change)
- `summary-rules.md`
- Documents **not** in the impact chain
