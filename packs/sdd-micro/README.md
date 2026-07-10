# SDD Micro Pack
## Tiny / Personal Projects · 3 Commands · Any AI Tool

---

## What Is This?

The other SDD packs (`sdd-universal`, `sdd-backend-service`, etc.) run a
full 11-command SDLC — BRD, Use Cases, SRD, Validate, Analyze, Clarify,
Design, Tasks, Implement, Release. That's the right amount of ceremony
for a real service with stakeholders. It's way too much for a "print
hello world" script, a small CLI utility, or a weekend project.

`sdd-micro` is the same idea — a constitution keeps the agent honest
about your tech stack and ground rules, and every change is still
task-by-task and verified — with almost none of the paperwork:

```
/specify → [GATE-1: confirmed] → /task → /implement
```

That's the whole flow. No BRD, no Use Cases, no SRD, no Jira, no formal
review gates — just enough structure to safely go from "I want to build
X" to working, verified code.

> This pack intentionally does not follow `PACK-SPEC.md` (the full-SDLC
> pack spec) — see `CLAUDE.md` for why, and "Outgrowing sdd-micro" below
> for when to move to a bigger pack.

---

## Quick Start

```bash
# Recommended: use the CLI
pip install sddflow
sdd init --pack sdd-micro     # copies this pack into the current directory

# OR: manual setup
unzip sdd-micro.zip -d my-project
cd my-project
git init
# Fill .specify/manifest.yml (3 fields)

# Then start your AI tool
claude                  # Claude Code: type /specify
# OR open VS Code + GitHub Copilot Chat: type /specify
```

You can also just describe what you want in chat — you don't need to
write `context.md` by hand:

```
/specify
I want a small Python script that prints "Hello, world!" and takes an
optional --name flag to greet someone by name.
```

---

## Setup — 1 File

### manifest.yml — 3 required fields
```yaml
project:
  name: "hello-world"
  feature: "greeter"
  context_file: "greeter.md"    # optional — /specify works from chat too
```

Everything else (`pr_rules`, `workflow_mode`) already has a sane default
for a small local project — edit only if you want something different.

---

## Command Flow

| Command | What it does | Gate |
|---|---|---|
| `/create-context` *(optional)* | Turn rough notes into a short context.md | — |
| `/specify` | Constitution Part 2 (DRAFT) — tech stack + ground rules | — |
| — GATE-1 — | You review Part 2 and say "confirmed" | manual |
| `/task` | Flat, numbered task list (no stories, no Jira) | GATE-1 |
| `/implement` | One task at a time, verified as you go | tasks.md reviewed |

Want a quick visual on task progress instead of reading `tasks.md`
directly? `sdd dashboard` (from the `sddflow` CLI) works here too — it
reads this pack's `tasks.md` format the same as the full packs'. See
`cli-python/README.md` → "sdd dashboard".

---

## Outgrowing sdd-micro

Move to `sdd-universal` (or a type-specific pack) when the project starts
having any of:
- More than one contributor, or an external stakeholder who needs sign-off
- A production deployment with real users or compliance requirements
- A need to track requirements formally (audits, tickets, traceability)

To migrate: scaffold `sdd-universal` alongside this pack (`sdd init --pack
sdd-universal` in a fresh copy), and use this project's `constitution.md`
Part 2 and `tasks.md` as the seed for a proper `/create-context` →
`/specify` pass — the bigger pack's docs build on top of that, they don't
require starting from nothing.

---

## Read Next

| File | Purpose |
|---|---|
| `QUICKSTART.md` | Steps to first run |
| `CLAUDE.md` | Full command reference + Never Do rules |
| `.specify/memory/constitution.md` | Universal rules + your tech stack |
| `.specify/contexts/CONTEXT-GUIDE.md` | How to write (or skip) a context file |
| `WHY-SDD.md` | Why even a tiny project benefits from a constitution |
