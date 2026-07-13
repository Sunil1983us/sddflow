# SDD Pack Specification v2.0

> This document defines what constitutes a valid SDD pack.
> Follow this spec to build a community pack (e.g. `sdd-data-platform`,
> `sdd-embedded`, `sdd-saas`). Submit via PR to `examples/community-packs/`.

> **Exception — `sdd-micro`:** the official `packs/sdd-micro/` pack
> deliberately does not follow this spec. It targets tiny/personal
> projects (a script, a small tool) where the full 11-command SDLC and
> BO→BR→FR/NFR→UC→STORY→TASK traceability chain below are pure overhead
> — there's no BRD/Use Cases/SRD, no Validate/Analyze/Clarify/Design/
> Release, and no `assert-output.sh` conformance. It keeps only a
> constitution (GATE-1) and a flat task list. See
> `packs/sdd-micro/CLAUDE.md` and `WHY-SDD.md` for the reasoning. This is
> a one-off, intentional exception for this specific use case — new
> community packs should still follow the full spec below unless they
> have the same "no real stakeholders, no audit need" justification, in
> which case open an issue to discuss before diverging.

---

## What Is a Pack?

A pack is a self-contained directory that a team copies into their project
once. It provides an AI-driven 11-command SDLC workflow for a specific class
of project. Once copied, the pack governs itself — it never imports from or
calls back to this repository.

---

## Required Directory Structure

```
sdd-{name}/
  CLAUDE.md                          # REQUIRED — agent startup + 11-command flow
  README.md                          # REQUIRED — overview + quick start
  QUICKSTART.md                      # REQUIRED — 5-minute guide
  WHY-SDD.md                         # REQUIRED — philosophy doc
  setup.sh                           # REQUIRED — bash initializer
  setup.ps1                          # REQUIRED — PowerShell initializer
  .windsurfrules                     # REQUIRED — Windsurf adapter
  .specify/
    manifest.yml                     # REQUIRED — project config template
    memory/
      constitution.md                # REQUIRED — Part 1 (universal) + Part 2 template
      roles.yml                      # REQUIRED — RACI per gate
      summary-rules.md               # REQUIRED — AI-2 reading mode rules
      change-rules.md                # REQUIRED — constitution amendment rules
    templates/                       # REQUIRED — ≥ 15 document templates
    contexts/
      CONTEXT-GUIDE.md               # REQUIRED — guide for writing context.md
  .github/
    copilot-instructions.md          # REQUIRED — Copilot Chat entrypoint
    prompts/                         # REQUIRED — one .prompt.md per command
    instructions/                    # RECOMMENDED — coding standards per file glob
    workflows/
      quality-gate.yml               # RECOMMENDED — CI/CD gate (GitHub Actions)
  bitbucket-pipelines.yml            # OPTIONAL — same gate for Bitbucket repos
  .gitlab-ci.yml                     # OPTIONAL — same gate for GitLab repos
  azure-pipelines.yml                # OPTIONAL — same gate for Azure DevOps repos
  .claude/
    commands/                        # REQUIRED — one .md per command
  .cursor/
    rules/
      sdd-framework.mdc              # REQUIRED — Cursor adapter
```

---

## Required Commands (Prompt Files + Claude Commands)

Every pack must implement these commands as both `.github/prompts/{cmd}.prompt.md`
and `.claude/commands/{cmd}.md`:

| Command | Minimum behavior |
|---|---|
| `/specify` | Generate constitution Part 2 + pilot-scope spec docs (BRD, SRD) |
| `/validate` | Business sign-off gate on BRD + SRD |
| `/analyze` | Risk register + dependency map + CF-NNN consistency findings |
| `/clarify` | Surface and resolve open questions; update ASSUMPTION-NNN markers |
| `/plan-arch` | Architecture decisions + implementation plan |
| `/plan-hld` | HLD with at least one Mermaid diagram |
| `/task` | Generate stories.md (MoSCoW) + tasks.md (Satisfies: FR-NNN on every task) |
| `/implement` | Execute one task at a time with PR-size check |
| `/release` | UAT plan + Go/No-Go gate + BO closure |

Optional but recommended: `/plan-lld`, `/plan-adr`, `/checklist`, `/bug-assess`,
`/bug-fix`, `/taskstoissues`, `/create-context`.

---

## Required manifest.yml Fields

```yaml
project:
  name: ""            # filled by setup.sh
  scope: "pilot"      # pilot | mvp | full
  feature: ""         # filled by setup.sh
  context_file: ""    # filled by setup.sh

project_type: "auto"  # set during /specify or by setup.sh

sdd_version: "2.7.47"  # REQUIRED — pack version for upgrade tracking

pr_rules:
  max_lines_per_pr: 400
  max_files_per_pr: 5

workflow_mode: "github"  # github | local — despite the name, "github" mode's
                          # PR automation (sdd pr create) auto-detects and
                          # works on GitHub, GitLab, Bitbucket, or Azure DevOps
```

---

## Required Shared Block Markers

The following `<!-- shared:{id}:start/end -->` markers must be present in
`CLAUDE.md` and in the relevant prompt files, so that `sync-blocks.sh` can
keep them byte-identical with the canonical `_shared/blocks/` source:

| Block ID | Location |
|---|---|
| `command-gates` | `CLAUDE.md` — "11-Command Gates" section |
| `gate1-reminders` | `CLAUDE.md` — Startup steps 8–10 |
| `never-do-core` | `CLAUDE.md` — "Never Do" section |
| `pr-contract` | `CLAUDE.md` — "PR Contract" section |
| `review-gates` | `CLAUDE.md` — "Document Review Gates — Three Modes" section |
| `scope-reference` | `CLAUDE.md` — "Scope Reference" section |
| `startup-instructions` | `CLAUDE.md` — Startup step 7 (AI-7 rule) |
| `start-command-body` | `.claude/commands/start.md` |
| `team-routing` | `CLAUDE.md` — "Virtual Team" section |

Do NOT modify content inside these markers — edit `_shared/blocks/{id}.md`
and run `bash packs/_shared/sync-blocks.sh` instead.

---

## Traceability Requirements

The following traceability chain must be present in the generated documents:

```
BO-NNN (brd.md) → BR-NNN (brd.md) → FR-NNN / NFR-NNN (srd.md)
  → UC-NNN with Given/When/Then (srd.md)
  → STORY-NNN with Satisfies: FR-NNN (stories.md)
  → TASK-NNN with Satisfies: FR-NNN (tasks.md)
```

The regression harness at `packs/_shared/tests/assert-output.sh` validates
these invariants. Run it on your example output before submitting a pack.

---

## Naming Convention

- Official packs: `sdd-{project-type}` (e.g. `sdd-backend-service`)
- Community packs: `sdd-{domain}` (e.g. `sdd-data-platform`, `sdd-embedded`)
- Do not prefix with anything other than `sdd-`

---

## Submitting a Community Pack

1. Build your pack following this spec
2. Create a worked example under `examples/{your-pack-name}/`
3. Run `bash packs/_shared/tests/assert-output.sh examples/{your-pack-name}/...` — must pass
4. Open a PR adding your pack to `packs/CATALOG.md`
5. Include a brief description and the project class it targets
