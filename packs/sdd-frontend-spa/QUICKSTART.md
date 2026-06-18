# SDD Framework — Quick Start
## Pack: Frontend SPA (React / Vue / Angular)

> **5 minutes to your first spec.** This guide covers setup and first run.
> For the full command reference, see [PROMPT-GUIDE.md](PROMPT-GUIDE.md).

---

## Step 1 — Initialize (once per project)

**Mac / Linux:**
```bash
bash setup.sh
```

**Windows:**
```powershell
.\setup.ps1
```

The script fills in your project name, scope, and feature, and creates your first context file.

---

## Step 2 — Fill Your Context

Open `.specify/contexts/{your-feature}.md` and describe your feature:
- What it does (2-3 sentences)
- Who uses it (actors)
- Key flows (what are the main journeys)
- Tech stack (language, framework, database — fill what you know)
- Non-functional requirements (performance, availability)

**Not sure what to write?** Let your AI tool help — run `/create-context` and paste your rough notes.

---

## Step 3 — Run /specify

Choose your AI tool:

### Claude Code
```
/specify
```

### GitHub Copilot
```
/specify
```

### Cursor
In the Cursor chat panel:
```
Read and follow .github/prompts/specify.prompt.md exactly
```

### Windsurf
In the Windsurf chat:
```
Run specify
```

### Any Other AI (ChatGPT, Gemini, Claude.ai, etc.)
1. Open `.github/prompts/specify.prompt.md`
2. Copy the entire file contents
3. Paste into your AI chat
4. The AI will execute the command

---

## The 11-Command Flow

```
/specify      → generates constitution Part 2 (DRAFT) + all spec docs
[GATE-1]      → YOU review and finalize constitution Part 2
/checklist    → (optional) spec-quality check before business review
/validate     → business sign-off on BRD + SRD
/analyze      → risk, complexity, cross-artifact consistency
/clarify      → surface and resolve all ambiguities
/plan-arch    → architecture decisions + implementation plan
/plan-hld     → high-level design + Mermaid diagrams
/plan-lld     → low-level design (mvp+ only)
/plan-adr     → architecture decision records (mvp+ only)
/task         → stories + tasks + Jira CSV
/implement    → code one task at a time with PR rules
/release      → UAT plan + go-live gate
```

Pick your scope in `manifest.yml`:
- **pilot** — runs: specify → validate → analyze → clarify → plan-arch → plan-hld → task → implement → release
- **mvp** — adds: plan-lld, plan-adr, api-spec, data-model
- **full** — adds: resilience, investigation, security-design (full STRIDE)

---

## Tool Compatibility

| AI Tool | Native Commands | Setup |
|---|---|---|
| Claude Code | ✅ `/specify`, `/validate`, etc. | Auto-discovered from `.claude/commands/` |
| GitHub Copilot | ✅ `/specify`, `/validate`, etc. | Auto-discovered from `.github/prompts/` |
| Cursor | Chat: `Read and follow .github/prompts/specify.prompt.md` | `.cursor/rules/` auto-loaded |
| Windsurf | Chat: `Run specify` | `.windsurfrules` auto-loaded |
| Any AI | Copy-paste `.github/prompts/{command}.prompt.md` | No setup needed |

---

## Key Files to Know

| File | Purpose |
|---|---|
| `manifest.yml` | Project config (name, scope, feature, PR rules) |
| `constitution.md` | Universal + project-specific rules — **the law** |
| `PROMPT-GUIDE.md` | Full command reference with all prompts |
| `summary-rules.md` | Controls how documents are read (auto/summary/full) |
| `roles.yml` | Who approves each gate (RACI) |

---

## Troubleshooting

**"I don't know what to put in context.md"** → Run `/create-context` and paste informal notes — any format.

**"Constitution Part 2 not finalized"** → Open `constitution.md`, review Part 2, resolve `[MISSING — ask user]` markers, tell the agent "Constitution Part 2 finalized".

**"Where are the output documents?"** → `.specify/features/{your-feature}/` — one subfolder per feature.

**"The PR is too large"** → The agent will propose a SPLIT plan automatically. Confirm the split, then do sub-tasks one at a time.

See [PROMPT-GUIDE.md](PROMPT-GUIDE.md) for the full reference.
