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

Two CLIs are provided — identical behaviour, different runtimes. Both include
Jira and Confluence integration.

### Python CLI — `sdd-init`

```bash
pip install sdd-init          # or: pipx install sdd-init
sdd init
```

Includes:
- `sdd init` / `sdd upgrade`
- `sdd config init` / `sdd config test` / `sdd config fields`
- `sdd jira push` / `sdd jira sync`
- `sdd confluence push`
- `sdd review submit` / `sdd review check` / `sdd review apply` / `sdd review status`
- `sdd pr create`

Agent commands (Claude Code / Copilot):
- `/pre-review` — one-time code review before PR creation; developer picks which findings to fix
- `/address-review` — address human PR review comments; replies to threads, requests re-review

→ Full reference: [`cli-python/README.md`](cli-python/README.md)

### Node.js CLI — `sdd-init`

```bash
npx sdd-init init             # no install required
```

Includes:
- `sdd init` / `sdd upgrade`

→ Full reference: [`cli/README.md`](cli/README.md)

---

## Quick start

```bash
# 1. Copy a pack into your project
cp -r packs/sdd-universal/. your-project/

# 2. Initialize
cd your-project
sdd init                      # Python CLI
# or
npx sdd-init init             # Node.js CLI

# 3. Open in your AI tool and run /specify
```

See the pack's own `GETTING-STARTED.md` for the full walkthrough.

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
