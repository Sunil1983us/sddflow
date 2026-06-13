# Change Rules
# Golden rule: context.md first — never code first
# Add CHANGELOG entry → run impact analysis → update affected docs → CHG-NNN tasks

## Document Dependency Chain
context.md → brd → srd → analyze → arch → plan → hld → lld → tasks

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
| Scope upgrade | manifest + newly enabled docs |
| Bug fix / refactor | code only (CHG task, no doc update) |

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
- All templates
- CLAUDE.md
- copilot-instructions.md
- Documents NOT in the impact chain
