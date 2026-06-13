# Change Rules
# Golden rule: context.md first — never code first
# Add CHANGELOG entry → run impact analysis → update affected docs → CHG-NNN tasks

## Document Dependency Chain
context.md → brd → srd → validate → analyze → clarify → arch → plan
→ api-spec / data-model / security-design / resilience (refined post-arch)
→ hld → lld → tasks → release

## Change Impact Matrix
| Change Type | Documents to Update |
|---|---|
| New field in request/response | api-spec only |
| New endpoint | srd + api-spec + lld |
| New status/state | srd + api-spec + data-model + hld |
| New business rule | srd + arch (if structural) |
| New DB table | data-model + arch + lld |
| NFR change | srd + resilience |
| New integration | srd + arch + api-spec + lld + analyze |
| New security control / regulation | security-design + srd |
| Scope upgrade | manifest + newly enabled docs |
| Bug fix / refactor | code only (CHG task, no doc update) |

## AI-8 — No Unresolved Assumptions Before /plan-arch
Before /plan-arch can run, every `[ASSUMPTION-NNN]` marker left in brd.md,
srd.md, api-spec.md, data-model.md, or security-design.md must be resolved
via /clarify (status RESOLVED/CONFIRMED/DECIDED in clarify.md) and the
source doc updated with `<!-- Clarified: {ID} -->`. If any remain
unresolved, /plan-arch must STOP and point back to /clarify.

## Impact Analysis Output Format
CHANGE: {description} | VERSION: v{N.N}
DOCS TO UPDATE: {list with reason}
DOCS TO SKIP: {list}
NEW TASKS: CHG-NNN: {description} — est {N} lines
TOTAL: {N} docs, {N} tasks, ~{N} lines

## Change Task Naming
CHG-001: {description}
CHG-002: {description}
Append to tasks.md under: ## Change Set: v{N.N} — {date}

## What Never Changes on a Change Request
- constitution.md Part 1
- All templates (including security-design, runbook, validate, release,
  openapi templates)
- CLAUDE.md
- copilot-instructions.md
- roles.yml (unless reviewers/owners change)
- Documents NOT in the impact chain
