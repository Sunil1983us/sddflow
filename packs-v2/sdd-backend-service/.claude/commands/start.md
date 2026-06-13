---
description: Startup — read framework files and confirm project state (Step 0)
---

Read and follow the "Startup (every session)" steps in `CLAUDE.md`:
- `.specify/manifest.yml`
- `.specify/memory/constitution.md`
- `.specify/memory/summary-rules.md`
- `.specify/memory/change-rules.md`
- `.specify/memory/roles.yml`
- `.github/instructions/*.instructions.md` (apply each file's `applyTo` glob — AI-7)

Then confirm:
- Project name, scope (pilot/mvp/full), feature, context file
- Constitution Part 2: generated? finalized (GATE-1)?
- Commands available for this scope
- PR rules (max lines/files per PR)

State which command is ready to run next. If Part 2 is generated but not
finalized, remind the user to complete GATE-1 before `/validate`.

$ARGUMENTS
