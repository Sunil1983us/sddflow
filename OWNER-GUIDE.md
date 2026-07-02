# SDD Framework — Owner's Guide
## What Was Built · How It Works · Where to Look When Things Break

---

## 1. What This Repository Is

This is the **maintainer repository** for the SDD (Spec-Driven Development) Framework.

You do not run SDD workflows here. This repo is where you:
- Author and maintain the packs
- Fix bugs in prompts or templates
- Add new features (new commands, new personas, new project types)
- Package packs for distribution

End-users copy one pack folder into their own project and work there.
They never touch this repo.

---

## 2. What Was Built — Full Inventory

### 2.1 The Five Packs

| Pack | Who uses it |
|---|---|
| `packs/sdd-universal` | Anyone unsure which pack to use — auto-detects project type |
| `packs/sdd-backend-service` | REST APIs, microservices, Spring Boot, Node, etc. |
| `packs/sdd-frontend-spa` | React, Vue, Angular single-page apps |
| `packs/sdd-fullstack` | Projects with both a backend and a frontend |
| `packs/sdd-mobile` | React Native / Flutter iOS + Android apps |

Each pack is **fully self-contained** — a user copies the whole folder and it works standalone. Packs share no runtime dependencies with each other or with `_shared/`.

### 2.2 Inside Every Pack

```
<pack>/
├── CLAUDE.md                         ← Agent startup instructions (the "brain" of the pack)
├── README.md                         ← User-facing overview and quick start
├── QUICKSTART.md                     ← Step-by-step first run guide
├── setup.sh / setup.ps1              ← One-command initializer (fills manifest.yml)
├── .vscode/extensions.json           ← Recommends Mermaid + YAML extensions
├── .windsurfrules                    ← Windsurf AI tool support
├── .github/
│   ├── copilot-instructions.md       ← GitHub Copilot entrypoint
│   ├── prompts/                      ← One .prompt.md per command (all AI tools)
│   └── instructions/                 ← Coding standards applied per file type
├── .claude/
│   └── commands/                     ← Claude Code native slash command wrappers
├── .cursor/
│   └── rules/sdd-framework.mdc       ← Cursor AI rules
└── .specify/
    ├── manifest.yml                  ← Project config (name, scope, feature, type)
    ├── memory/                       ← constitution.md, roles.yml, summary-rules.md
    ├── templates/                    ← 30+ document templates for all SDD outputs
    └── integrations.yml.example      ← Jira/Confluence config template
```

### 2.3 Commands Built (37 total)

**SPECIFY group** — generates specification documents:
| Command | Output | Who (persona) |
|---|---|---|
| `/specify` | Constitution Part 2 (tech stack + rules) | — |
| `/specify-brd` | Business Requirements Document | Maya |
| `/specify-uc` | Use Cases with Mermaid relationship diagram | Maya |
| `/specify-srd` | Software Requirements Document | Rex |
| `/specify-doc {name}` | Extended docs (security, api-spec, data-model, resilience…) | Ava |
| `/create-context` | Drafts context.md from rough notes | Maya |
| `/change` | Change request across all spec docs | Maya + Leo |

**PLAN group** — generates design documents:
| Command | Output |
|---|---|
| `/plan-design` | Architecture + Diagrams + API Design + ADRs (`plan_mode: unified`, default) |
| `/plan-arch` | Architecture pattern, layers, key decisions — Step 1 of 3 (`plan_mode: separate`) |
| `/plan-hld` | System diagrams: C4 context, sequence, state machine — Step 2 of 3 (`plan_mode: separate`) |
| `/plan-adr` | Architecture Decision Records — Step 3 of 3 (`plan_mode: separate`, mvp+ only) |
| `/plan-lld` | Detailed class/sequence design (mvp+ only) |

**VALIDATE / ANALYZE / CLARIFY** — review pipeline:
| Command | Purpose |
|---|---|
| `/validate` | Business sign-off on BRD + SRD |
| `/analyze` | Technical risk analysis |
| `/clarify` | Resolves assumptions before design |
| `/checklist` | Spec quality audit (mandatory mvp+) |

**TASK / IMPLEMENT / RELEASE** — delivery:
| Command | Purpose |
|---|---|
| `/task` | Generates stories + tasks + QA test cases (mvp+) |
| `/implement` | Code generation per task |
| `/pre-review` | AI self-review before PR |
| `/address-review` | Applies reviewer comments from PR |
| `/release` | UAT plan + go-live gate |

**REVIEW / BUG / UTILITY**:
| Command | Purpose |
|---|---|
| `/submit-review` | Pushes doc to Confluence + creates Jira task |
| `/check-review` | Polls Jira for reviewer approval |
| `/bug-assess` | Diagnoses a bug report |
| `/bug-fix` | Fixes an assessed bug |
| `/taskstoissues` | Exports tasks to Jira/GitHub Issues (CSV — manual import) |
| `/jira-push` | Pushes Epic/Story/Task to Jira progressively via API at each gate |
| `/orchestrate` | Runs the full pipeline end-to-end |
| `/start` | Session startup — reads framework files, confirms project state |

**Virtual Team (persona shortcuts)**:
| Command | Routes to |
|---|---|
| `/maya` | specify-brd, specify-uc, validate, create-context, change |
| `/rex` | specify-srd, clarify |
| `/ava` | analyze, plan-design, specify-doc |
| `/leo` | plan-lld, implement, pre-review, address-review, bug-fix |
| `/kai` | task, taskstoissues |
| `/quinn` | checklist |
| `/riley` | release |
| `/morgan` | orchestrate, jira-push |

### 2.4 Document Templates (31 files in `.specify/templates/`; 33 for `sdd-fullstack`)

Every SDD output is generated from a template. Templates live in `packs/_shared/full/.specify/templates/` and sync to all packs:

| Template file | Used by command |
|---|---|
| `use-cases-template.md` | `/specify-uc` — includes Mermaid §4 diagram |
| `srd-template.md` | `/specify-srd` |
| `design-template.md` | `/plan-design` |
| `lld-template.md` | `/plan-lld` |
| `validate-template.md` | `/validate` |
| `analyze-template.md` | `/analyze` |
| `clarify-template.md` | `/clarify` |
| `checklist-template.md` | `/checklist` |
| `qa-testcases-template.md` | `/task` (mvp+) |
| `plan-template.md` | `/task` (stories + tasks) |
| `feature-story-template.md` | `/task` |
| `adr-template.md` | `/plan-design` (ADR entries) |
| `changeset-template.md` | `/change` |
| `jira-export-template.md` | `/taskstoissues` |
| `jira-config-template.yml` | `/jira-push` (copy to `.specify/jira-config.yml`) |
| `constitution-amendment-template.md` | `/specify` (re-run) |

### 2.5 The Shared Sync System

`_shared/` is the single source of truth for all content that is identical across packs.

**Two sync mechanisms:**

**Blocks** (`_shared/blocks/*.md`) — sections of content inside otherwise pack-specific files.
Wrapped with markers:
```
<!-- shared:{id}:start -->
...content owned by _shared/blocks/{id}.md...
<!-- shared:{id}:end -->
```
Current blocks and where they appear:

| Block ID | What it is | Where used |
|---|---|---|
| `command-gates` | Gate sequence (SPECIFY→GATE-1→…) | All packs' `CLAUDE.md` |
| `gate1-reminders` | GATE-1 reminder text | All packs' `CLAUDE.md` |
| `never-do-core` | Universal Never Do rules | All packs' `CLAUDE.md` |
| `pr-contract` | PR estimate + split + "PR ready" rules | All packs' `CLAUDE.md` |
| `scope-reference` | Pilot/mvp/full feature table | All packs' `CLAUDE.md` |
| `startup-instructions` | Session startup checklist | All packs' `CLAUDE.md` |
| `review-gates` | Document review gates — three modes (chat/local/jira) | All packs' `CLAUDE.md` |
| `start-command-body` | `/start` command body | All packs' `.claude/commands/start.md` |
| `team-routing` | Virtual team roster + routing rule | All packs' `CLAUDE.md` |

**Full files** (`_shared/full/**`) — entire files identical across all packs.
All 8 persona prompt files, all 8 persona command wrappers, all shared command prompts, templates, `.windsurfrules`, `.vscode/extensions.json`, `CLAUDE.local.md`, `setup.sh` (base), `setup.ps1` (base).

> Exception: `sdd-universal`'s `setup.sh` and `setup.ps1` are NOT overwritten by sync — they have unique auto-detection logic.

**To run sync:**
```bash
bash packs/_shared/sync-blocks.sh
```

---

## 3. How It Works — Architecture

### 3.1 The User Flow (what happens when a user runs the pack)

```
User copies pack → fills manifest.yml → writes context.md
       ↓
Runs /specify  →  AI reads context → fills constitution Part 2 (DRAFT)
       ↓
User reviews constitution → says "Constitution Part 2 finalized" (GATE-1)
       ↓
/specify-brd → Maya generates BRD → user approves
       ↓
/specify-uc  → Maya generates Use Cases (with Mermaid §4 diagram) → user approves
       ↓
/specify-srd → Rex generates SRD → user approves
       ↓
/validate    → business sign-off
/analyze     → risk analysis
/clarify     → resolves assumptions
       ↓
/plan-design → Ava generates Architecture + Diagrams + ADRs
/plan-lld    → Leo generates detailed design (mvp+ only)
       ↓
/task        → Kai generates stories + tasks
       ↓
/implement   → Leo generates code task by task
/pre-review  → AI self-reviews before PR
/release     → Riley coordinates go-live
```

### 3.2 How a Command Works (the triplicity rule)

Every command exists in **three places simultaneously** — all three must be in sync:

| Location | File | Used by |
|---|---|---|
| `.claude/commands/{cmd}.md` | Thin wrapper: "Read and follow `.github/prompts/{cmd}.prompt.md`" | Claude Code `/cmd` slash commands |
| `.github/prompts/{cmd}.prompt.md` | The actual logic (frontmatter `mode: agent`, full instructions) | Copilot, Cursor, Windsurf, any AI |
| `.github/copilot-instructions.md` | Lists all commands with descriptions | Copilot Chat entrypoint |

The `.github/prompts/*.prompt.md` files are the **real source of truth** for what each command does. The `.claude/commands/` files simply delegate to them.

### 3.3 How Persona Routing Works

When a user says `"Maya, create the BRD"` or `/maya`:

1. AI reads `CLAUDE.md` → sees `team-routing` block with routing rule
2. Routing rule says: read `.github/prompts/maya.prompt.md`
3. `maya.prompt.md` detects intent from keywords (BRD, use case, change, validate…)
4. Checks pipeline state (does `brd.md` exist? does `use-cases.md` exist?)
5. Routes to the appropriate underlying command (`specify-brd.prompt.md`, etc.)
6. If unclear: shows a short menu (a) BRD  b) Use Cases  c) Validate…)

This works identically in Claude Code (via `/maya`), GitHub Copilot (via `/maya` using `mode: agent`), and any other AI tool (natural language routing via `CLAUDE.md` / `copilot-instructions.md`).

### 3.4 How scope controls what gets generated

`manifest.yml` `scope` field (`pilot` / `mvp` / `full`) gates which documents are produced:

- **pilot**: fastest path — no LLD, no QA test cases, no extended docs, checklist optional
- **mvp**: + API Spec, Data Model, Security §1-2, LLD, QA test cases, Runbook, checklist mandatory
- **full**: everything — + Resilience, Investigation, Security §1-4, OpenAPI

The `scope-reference` block in every `CLAUDE.md` is the at-a-glance table of this.

### 3.5 How project type detection works (sdd-universal only)

`sdd-universal` is the only pack that auto-detects project type. Two places must stay in sync:

1. `setup.sh` → `detect_project_type()` — bash execution
2. `specify.prompt.md` → Step 0 table — AI lookup

Detection order (critical — mobile must come before fullstack):
1. `pubspec.yaml` → flutter
2. `react-native` in package.json → react-native
3. `android/` + `ios/` → react-native (fallback)
4. Both `src/main/java` and `src/` with frontend files → fullstack
5. `src/main/java` or `pom.xml` → backend-service
6. `src/` with React/Vue/Angular → frontend-spa
7. `requirements.txt` / `setup.py` → data-ml
8. `serverless.yml` / `sam.yml` → serverless
9. `main.tf` / `*.tf` → iac
10. `Cargo.toml` / CLI indicators → cli
11. fallback → backend-service

### 3.6 How Mermaid diagrams work

The `use-cases-template.md` `## §4 Use Case Relationships` section generates a `graph LR` Mermaid diagram showing includes (solid `-->`) and extends (dashed `-.->`) relationships.

Renders automatically in:
- **GitHub** — built-in
- **Cursor** — native "Preview" link appears above any mermaid block
- **VS Code** — requires `bierner.markdown-mermaid` (`.vscode/extensions.json` recommends it)
- **Notion / Confluence** — paste code block, select Mermaid as language

---

## 4. Where to Look When Things Break

### 4.1 Command produces wrong output or skips a section

1. Open `.github/prompts/{command}.prompt.md` — this is the full logic
2. Check the `## Persona` section (has the name and role)
3. Check `## Actions` section (numbered steps the agent follows)
4. Check any `scope:` conditional — does it skip for pilot/mvp?
5. After fixing: run `bash packs/_shared/sync-blocks.sh` to propagate to all packs

### 4.2 A persona (/maya, /ava, etc.) routes to the wrong command

1. Open `.github/prompts/{name}.prompt.md` (e.g. `maya.prompt.md`)
2. Check `## Routing` → `Step 1` keyword list
3. Check `## Routing` → `Step 2` pipeline state checks (file existence logic)
4. Fix the keyword or condition in `_shared/full/.github/prompts/{name}.prompt.md`
5. Run sync script to propagate

### 4.3 A shared block (gates, never-do, PR contract, etc.) is wrong in one pack

1. Check `packs/_shared/blocks/{block-id}.md` — this is the canonical content
2. Check that the pack file has the markers `<!-- shared:{id}:start -->` and `<!-- shared:{id}:end -->`
3. If markers are missing: add them manually to the pack file at the right position
4. Run `bash packs/_shared/sync-blocks.sh` to push content into the markers

### 4.4 A new file was added to `_shared/full/` but didn't appear in packs

The sync script only updates files that **already exist** in the target pack — it never creates new files.

Fix:
```bash
cp packs/_shared/full/.github/prompts/newfile.prompt.md packs/sdd-backend-service/.github/prompts/
cp packs/_shared/full/.github/prompts/newfile.prompt.md packs/sdd-frontend-spa/.github/prompts/
# ... repeat for each pack
bash packs/_shared/sync-blocks.sh   # subsequent updates will now work
```

### 4.5 `setup.sh` fails or produces invalid YAML in manifest.yml

Run the smoke-test suite first — it covers injection-class names (apostrophes,
slashes, backslashes, spaces, unicode), all project types, and non-interactive
execution. CI runs it on every PR (`setup-smoke-tests` job in
`.github/workflows/ci.yml`):

```bash
bash packs/_shared/tests/test-setup.sh
```

To reproduce a single case by hand:
```bash
cd packs/sdd-universal
bash setup.sh --project "Test Project" --feature "auth" --scope pilot --type backend-service
python3 -c "import yaml; yaml.safe_load(open('.specify/manifest.yml'))" && echo "YAML valid"
# Clean up
rm -rf .specify/contexts/auth.md
git checkout .specify/manifest.yml
```

Setup scripts must never hang or crash when stdin is not a terminal (CI, piped
input): optional prompts fall back to defaults, required ones fail fast naming
the missing flag. Remember: the base `setup.sh`/`setup.ps1` are owned by
`_shared/full/` — edit there and sync; only `sdd-universal`'s variants are
edited in place.

### 4.6 Detection order is wrong (sdd-universal: mobile detected as fullstack)

Check both files must match:
1. `packs/sdd-universal/setup.sh` → `detect_project_type()` function
2. `packs/sdd-universal/.github/prompts/specify.prompt.md` → Step 0 table
3. `packs/sdd-universal/setup.ps1` → `Detect-ProjectType` function

Rule: mobile checks (`pubspec.yaml`, `react-native`) must appear **before** fullstack checks in all three files.

### 4.7 Mermaid diagram not showing in VS Code / Cursor

- **Cursor**: no extension needed — a "Preview" link appears at the top of any `.md` file. Click it.
- **VS Code**: install `bierner.markdown-mermaid` extension. The `.vscode/extensions.json` in every pack recommends it — VS Code will prompt automatically.
- **GitHub**: renders natively, no action needed.

### 4.8 Scope reference table is wrong in a pack

The table comes from `packs/_shared/blocks/scope-reference.md`.
1. Edit that file
2. Run `bash packs/_shared/sync-blocks.sh`
3. Verify the table updated in at least two packs' `CLAUDE.md`

### 4.9 A template produces a document missing a section

1. Open `packs/_shared/full/.specify/templates/{doc}-template.md`
2. Add the missing section
3. Run `bash packs/_shared/sync-blocks.sh` (templates are full-file synced)
4. Check the corresponding `.github/prompts/{cmd}.prompt.md` — if it explicitly lists which sections to generate, add the new section there too

### 4.10 Changes made directly in a pack were overwritten by sync

This is correct behaviour — `_shared/` owns the content.
- For **blocks**: edit `_shared/blocks/{id}.md`, not the pack file
- For **full files**: edit `_shared/full/{path}`, not the pack file
- For **pack-specific content** (e.g. `specify.prompt.md` tech stack rows): edit the pack file directly — these are NOT synced

---

## 5. How to Make Changes

### Change something in one command across all packs
```bash
# 1. Edit the canonical source
edit packs/_shared/full/.github/prompts/{cmd}.prompt.md
edit packs/_shared/full/.claude/commands/{cmd}.md   # if needed

# 2. Sync to all packs
bash packs/_shared/sync-blocks.sh
```

### Change a shared rule (gates, never-do, PR contract, scope table)
```bash
edit packs/_shared/blocks/{block-id}.md
bash packs/_shared/sync-blocks.sh
```

### Change something pack-specific (e.g. tech stack rows in specify.prompt.md)
Edit each pack's file individually — these are intentionally different per pack and not synced.

### Add a new command
1. Create `packs/_shared/full/.github/prompts/{cmd}.prompt.md` (the full logic)
2. Create `packs/_shared/full/.claude/commands/{cmd}.md` (thin wrapper)
3. Add to `packs/_shared/full/.github/copilot-instructions.md`
4. Seed the new files to all packs manually (`cp` to each)
5. Run `bash packs/_shared/sync-blocks.sh` (subsequent updates will be automatic)

### Add a new pack
1. Copy `packs/sdd-backend-service/` as a base
2. Adapt: tech stack rows in `specify.prompt.md`, `.github/instructions/`, constitution Part 1 domain rules
3. Leave all shared block markers intact — they sync automatically
4. Run `bash packs/_shared/sync-blocks.sh` to populate shared content

### Package a pack for distribution
```bash
bash packs/_shared/package.sh sdd-universal
# outputs zip/tarball ready for users
```

---

## 6. Key Files at a Glance

| File | What it is | Edit when… |
|---|---|---|
| `packs/_shared/sync-blocks.sh` | The sync engine | Never (unless adding a sync feature) |
| `packs/_shared/blocks/*.md` | Canonical shared rules | Changing gates, never-do, PR contract, team routing, scope table |
| `packs/_shared/full/.github/prompts/*.prompt.md` | Command logic | Fixing/improving a command |
| `packs/_shared/full/.specify/templates/*.md` | Document templates | Adding/fixing sections in generated docs |
| `packs/_shared/full/.github/prompts/{name}.prompt.md` | Persona routing | Fixing name-based routing logic |
| `packs/sdd-universal/setup.sh` | Auto-detection + initialization | Fixing project type detection |
| `packs/sdd-universal/.github/prompts/specify.prompt.md` | Universal tech stack tables | Adding a project type or fixing stack rows |
| `packs/{pack}/CLAUDE.md` | Agent startup checklist for that pack | Pack-specific startup rules (non-shared sections only) |
| `packs/{pack}/.github/prompts/specify.prompt.md` | Tech stack rows for that pack | Fixing/updating the pack's tech stack |

---

## 7. Git History — What Was Built When

| Commit | What was added |
|---|---|
| `6a76759` | Virtual team name routing (8 personas, natural language + slash command) |
| `099d250` | Named personas added to all agent prompt `## Persona` sections |
| `7eff29e` | `.vscode/extensions.json` for Mermaid rendering in Cursor/VS Code |
| `e7027f8` | Mermaid `graph LR` diagram in `## §4 Use Case Relationships` |
| `c466e88` | Scope reference table (pilot/mvp/full what's skipped) |
| `8690220` | Fix: clarify.md saved after resolution |
| `9a64ffc` | Fix: validate.prompt.md assumption correction tracking |
| `3751ff3` | Flexible approval signals (not just literal "approved") |
| `843f933` | Document Status updated on all approval paths |
| `8d3aecc` | FR-NNN back-fill + Version History across all templates |
| `6c6f479` | Confluence stakeholder review step in all /specify-* commands |
| `d0c22ab` | Pull Confluence comments into local file for AI processing |

---

## 8. Quick Diagnostic Checklist

When something doesn't work as expected, run through this:

- [ ] Did you edit the right file? (pack file vs `_shared/` source)
- [ ] Did you run `bash packs/_shared/sync-blocks.sh` after editing `_shared/`?
- [ ] Is the block marker present in the pack file? (`grep "shared:{id}:start" packs/sdd-*/CLAUDE.md`)
- [ ] Is the new file seeded to all packs? (`ls packs/sdd-*/path/to/file`)
- [ ] For sdd-universal detection: does `setup.sh` order match `specify.prompt.md` Step 0 order?
- [ ] For scope issues: check `packs/_shared/blocks/scope-reference.md`
- [ ] For persona routing: check `packs/_shared/full/.github/prompts/{name}.prompt.md` → `## Routing`
- [ ] Is the command also updated in `.claude/commands/` AND `.github/prompts/` AND `copilot-instructions.md`?
