# SDD Framework — Spec-Driven Development

A collection of self-contained packs that bring a structured, AI-assisted SDLC
into any project. Copy one pack, run one command, get a full specification
pipeline from business requirements through to release notes.

---

## Packs

| Pack | Use when |
|---|---|
| [`sdd-universal`](packs/sdd-universal/) | You want auto-detection — supports all 10 project types |
| [`sdd-backend-service`](packs/sdd-backend-service/) | REST API, microservice, or server application |
| [`sdd-frontend-spa`](packs/sdd-frontend-spa/) | React, Vue, Angular, Svelte, Next.js, Nuxt |
| [`sdd-mobile`](packs/sdd-mobile/) | React Native, Expo, or Flutter |
| [`sdd-fullstack`](packs/sdd-fullstack/) | Monorepo with a JS frontend + separate backend |

Not sure which to use? See [`packs/CATALOG.md`](packs/CATALOG.md) for a decision tree.

---

## CLI Tools

Two CLIs are provided, both built around the same `sdd init` / `sdd upgrade`
core — but they are **not at feature parity**. The Python CLI is the
full-featured implementation (Jira, Confluence, review gates, PR automation);
the Node.js CLI currently covers scaffolding only (`init` / `upgrade`). Pick
Python if you need Jira/Confluence integration; either works for basic
pack scaffolding.

### Python CLI — `sdd-init`

```bash
pip install sdd-init
sdd init
```

Includes:
- `sdd init` / `sdd upgrade`
- `sdd config init` / `sdd config test` / `sdd config fields`
- `sdd jira push` / `sdd jira sync`
- `sdd confluence push`
- `sdd review submit` / `sdd review check` / `sdd review apply` / `sdd review status`
- `sdd pr create`

Reviews don't require Jira: document approval works in chat out of the box (the
`Status:` header in each `.md` is the authoritative gate). With only a
`confluence:` section configured, `sdd review approve --local` also updates the
document's existing Confluence page — chat approvals never leave Confluence
stale. See "Document Review Gates — Three Modes" in any pack's `CLAUDE.md`.

Agent commands (Claude Code / Copilot):
- `/pre-review` — one-time code review before PR creation; developer picks which findings to fix
- `/address-review` — address human PR review comments; replies to threads, requests re-review
- `/jira-push` — progressive Jira push (Epic after BRD, Stories after Use Cases/SRD, Tasks after `/task`, CHG after `/change`) via a standalone script (`.specify/scripts/jira-push.py`), config in `.specify/jira-config.yml`. Complements `sdd jira push`, which pushes Story+Task together in one shot after `/task`.

→ Full reference: [`cli-python/README.md`](cli-python/README.md)

### Node.js CLI — `sdd-init`

```bash
npm install -g sdd-init
sdd init
```

Includes:
- `sdd init` / `sdd upgrade`

→ Full reference: [`cli/README.md`](cli/README.md)

### Alternative: setup scripts (no install needed)

The shell scripts in each pack do exactly what `sdd init` does — use them if you
prefer not to install the CLI:

```bash
bash setup.sh          # Mac / Linux
.\setup.ps1            # Windows PowerShell
```

---

## Quick start

```bash
# 1. Copy a pack into your project
cp -r packs/sdd-universal/. your-project/

# 2. Initialize (choose one)
cd your-project
bash setup.sh                 # Mac / Linux — no install needed
.\setup.ps1                   # Windows PowerShell — no install needed

# Python CLI
pip install sdd-init && sdd init

# Node.js CLI
npm install -g sdd-init && sdd init

# 3. Open in your AI tool and run /specify
```

See the pack's own `QUICKSTART.md` for the full walkthrough.

---

## Repository layout

```
packs/
  _shared/            # Canonical source for shared blocks and full files
  sdd-universal/      # Meta-pack: auto-detects 10 project types
  sdd-backend-service/
  sdd-frontend-spa/
  sdd-mobile/
  sdd-fullstack/
cli/                  # Node.js CLI (npx sdd-init)
cli-python/           # Python CLI (pip install sdd-init)
examples/
  todo-api/           # Complete worked example (TypeScript/Express/PostgreSQL)
PACK-SPEC.md          # Specification for building community packs
CHANGELOG.md          # Version history
```

---

## What's in each pack

| File | Purpose |
|---|---|
| `CLAUDE.md` | Agent startup checklist + full command flow |
| `.specify/manifest.yml` | Project config: name, scope, feature, reading_mode |
| `.specify/templates/` | 30+ document templates for all SDD outputs |
| `.specify/memory/constitution.md` | Universal rules (Part 1) + tech stack DRAFT (Part 2) |
| `.github/prompts/` | One prompt file per command (works in any AI tool) |
| `.claude/commands/` | Claude Code native slash command wrappers |
| `setup.sh` / `setup.ps1` | One-command initializer |

---

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md) for full version history.
