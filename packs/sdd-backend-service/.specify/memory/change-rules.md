# Change Rules
# Golden rule: context.md first — never code first
# A change request (/change) can be raised at ANY stage by ANY role.
# The agent reads existing filled documents one by one and classifies each.
# CR-NNN = mid-flow change (raised during spec/design/planning/implement)
# CHG-NNN = implementation task created by a CR (appended to tasks.md)

## Change Request Types

| Type | Raised when | Primary document impact |
|---|---|---|
| Business | Missing requirement, wrong business rule, scope change, new stakeholder | context → brd → use-cases → srd → validate |
| Technical | New integration, tech stack change, architecture decision, dependency | context → constitution → design → lld |
| Security | New regulation, vulnerability, compliance gap, new security control | context → brd §6 → srd (NFR) → security-design |
| Data | New field, new entity, schema change, payload change, migration | context → data-model → srd → api-spec → design |
| UX | New screen, flow change, component change, accessibility gap | context → use-cases → srd → design |
| Performance | New NFR, SLA change, load target change | context → srd (NFR) → analyze → resilience |
| Operational | Deployment change, config change, runbook update | context → constitution (config row) → design → runbook |
| Defect | Wrong spec, contradiction, error in existing document | from defect location forward in dependency chain |

## Document Walk Actions

When /change walks the dependency chain, each document receives one action:

| Action | Meaning |
|---|---|
| SKIP | CR has no impact — document unchanged, reason stated |
| ANNOTATE | Upstream approved document — CR reference note added, document not re-opened |
| UPDATE | Specific sections changed — agent shows BEFORE/AFTER diff, waits for QA approval |
| RERUN | Major structural impact — document regenerated with CR incorporated, backup saved |
| INCORPORATE | Document not yet created — CR built in automatically when generated |

## Ripple-Forward Rule

A CR only affects documents DOWNSTREAM from where it is raised.
- Documents already approved UPSTREAM → ANNOTATE only (never re-opened unless CR directly invalidates them)
- Documents already created DOWNSTREAM → walk and assess (UPDATE or SKIP)
- Documents not yet created → INCORPORATE (CR absorbed automatically)

## Document Dependency Chain
context.md → brd → use-cases → srd → security-design → api-spec → data-model
→ validate → analyze → clarify → design → lld → qa-testcases → tasks → release

## Change Impact Matrix (for impact pre-classification)

| Change Type | Documents to Update |
|---|---|
| New field in request/response | api-spec only |
| New endpoint | use-cases + srd + design (§3 API) + lld |
| New actor / use case | use-cases + srd |
| New status/state | srd + api-spec + data-model + hld |
| New business rule | srd + arch (if structural) |
| New DB table | data-model + arch + lld |
| NFR change | srd + resilience |
| New integration | srd + arch + api-spec + lld + analyze |
| New security control / regulation | security-design + srd |
| Scope upgrade | manifest + newly enabled docs |
| Bug fix / refactor | code only (CHG task, no doc update) |

## CR Naming and Storage

- CR-NNN: change request record — saved to `.specify/features/{feature}/changesets/CR-{NNN}.md`
- CHG-NNN: implementation task — appended to `tasks.md` under `## Change Set: CR-{NNN} — {date}`
- Constitution amendments: saved separately via `constitution-amendment-template.md` (for tech stack or core rule changes)

## Impact Analysis Output Format (for manual/non-command analysis)
- CHANGE: {description} | CR: {NNN} | TYPE: {type}
- DOCS TO UPDATE: {list with reason}
- DOCS TO SKIP: {list}
- NEW CHG TASKS: CHG-NNN: {description} — est {N} lines
- TOTAL: {N} docs, {N} tasks, ~{N} lines

## What Never Changes on a Change Request
- constitution.md Part 1
- All templates (including security-design, runbook, validate, release, use-cases,
  openapi templates)
- CLAUDE.md
- copilot-instructions.md
- roles.yml (unless reviewers/owners change)
- Documents NOT in the impact chain
