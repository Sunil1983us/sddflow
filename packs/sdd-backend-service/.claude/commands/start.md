---
description: Startup — read framework files and confirm project state (Step 0)
---

<!-- shared:start-command-body:start -->
Startup checklist for this session — these are the same files CLAUDE.md's
"Startup (every session)" section lists; if CLAUDE.md is already in your
context (e.g. auto-loaded by your tool), do not re-read it separately —
just work through this list:
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
<!-- shared:start-command-body:end -->

$ARGUMENTS
