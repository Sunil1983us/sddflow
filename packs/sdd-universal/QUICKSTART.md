# SDD Framework — Quick Start
## Pack: Universal (any project type)

> **5 minutes to get set up.** `setup.sh` auto-detects your project type.
> Your first full feature spec takes longer — budget half a day for a
> first pass. For the full command reference, see [PROMPT-GUIDE.md](PROMPT-GUIDE.md).
> Supported types: `backend-service` · `frontend-spa` · `mobile` · `fullstack`
> · `cli` · `data-ml` · `serverless` · `library` · `iac` · `desktop`

> **Building something small, solo, or just prototyping?** This pack is
> enterprise SDLC rigor — BRD → Use Cases → SRD → validate → analyze →
> clarify → design → task → implement → release, even at `pilot` scope.
> If that's more process than you need, use
> [`sdd-micro`](https://github.com/sunil1983us/universalguide/tree/main/packs/sdd-micro) instead — 3 commands, no BRD/UC/SRD ceremony.

> **Token/cost footprint.** This is a document-heavy pipeline — expect
> one agent command per phase (specify, specify-brd, specify-uc,
> specify-srd, each extended doc, checklist, validate, analyze, clarify,
> plan-design, plan-lld, one `/implement` per task in `tasks.md`,
> release), each reading and writing at least one document. There's no
> live cost estimator; enable `.specify/memory/token-pricing.yml` (copy
> from the `.example`) to log real per-command cost as you go — see
> "Token Usage Logging" in `CLAUDE.md`.

---

## Step 0 — Copy the Pack (first time only)

```bash
unzip {pack}.zip -d my-project   # or: cp -r packs/sdd-universal/. my-project
cd my-project
git init && git add . && git commit -m "chore: SDD framework"
```

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

## Step 2 — Fill Your Context (15-30 min)

Open `.specify/contexts/{your-feature}.md` and describe your feature:
- What it does (2-3 sentences)
- Who uses it (actors)
- Key flows (what are the main journeys)
- Tech stack (language, framework, database — fill what you know)
- Non-functional requirements (performance, availability)

Must include a Tech Stack section, e.g.:
```markdown
## Tech Stack
| Concern | Choice |
|---|---|
| Language | {your language} |
| Framework | {your framework} |
| Database | {your DB} |
```

**Not sure what to write?** Run `/create-context` and paste your rough notes — the agent drafts the file with you, any format welcome.

(Optional but recommended) Edit `.specify/memory/roles.yml` — fill in names/teams for `product_owner`, `tech_lead`, `qa_lead`, etc., so review gates route to the right people.

Review gates work out of the box — **no Jira needed**: reviewers approve in
chat and the agent flips the document's `Status:` header. If you configure
Confluence/Jira later (`.specify/integrations.yml`), approvals automatically
update the matching Confluence page too. See "Document Review Gates — Three
Modes" in `CLAUDE.md`.

> **Know what chat-mode approval actually checks.** By default (through
> `pilot`), "approved" just means someone typed the word in the same
> conversation that wrote the doc — there's no independent identity
> check. Fine for solo/prototype use; for anything past `pilot`, read
> `CLAUDE.md`'s "Self-approval risk" section before relying on it.

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

## What Happens at /specify and GATE-1

`/specify` generates **constitution Part 2 only** (DRAFT) — it reads your context and fills in Tech Stack, Core Principles, Domain Rules, and Never Do, flagging anything missing as `[MISSING — ask user]`.

Nothing proceeds until **GATE-1**: open `constitution.md`, review every row, resolve any `[MISSING — ask user]` markers (your edits are authoritative), then tell the agent "Constitution Part 2 finalized".

Spec documents are then generated one at a time: `/specify-brd` → `/specify-uc` → `/specify-srd` → `/specify-doc {name}` — each gated on the previous one's approval. `/specify-uc` produces a full Use Case Specification (Actors + Main Path + Alternate Paths + Exception Paths); the SRD derives every requirement from it.

---

## The Command Flow

```
/specify      → constitution Part 2 (DRAFT) — then GATE-1 (you finalize it)
/specify-brd → /specify-uc → /specify-srd → /specify-doc {name}...
/checklist    → (mandatory mvp+, optional pilot) spec-quality check
/validate     → business sign-off on BRD + Use Cases + SRD
/analyze      → risk, complexity, cross-artifact consistency
/clarify      → surface and resolve all ambiguities

Then plan, depending on your manifest's plan_mode:
  unified (default):  /plan-design  → one combined architecture + diagram doc
  separate:            /plan-arch → /plan-hld → /plan-adr (mvp+ only)

/plan-lld     → low-level design (mvp+ only — skipped at pilot)
/task         → stories + tasks + Jira export
/implement    → code one task at a time, with PR rules
/release      → UAT plan + go-live gate

Or run everything at once:
/orchestrate  → full pipeline, auto-sequenced, pauses at every gate
```

Pick your scope in `manifest.yml`:
- **pilot** — runs: specify → validate → analyze → clarify → plan → task → implement → release; skips `/plan-lld`, ADRs, extended docs
- **mvp** — adds: `/plan-lld`, ADRs (separate mode), `api-spec.md` (living, if this project_type provides an API), `data-model.md` (living), QA test cases
- **full** — adds: `resilience.md`, `investigation.md`, full STRIDE security design

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
| `manifest.yml` | Project config (name, scope, feature, plan_mode, PR rules) |
| `constitution.md` | Universal + project-specific rules — **the law** |
| `PROMPT-GUIDE.md` | Full command reference with all prompts |
| `summary-rules.md` | Controls how documents are read (auto/summary/full) |
| `roles.yml` | Who approves each gate (RACI) |

---

## Troubleshooting

**"I don't know what to put in context.md"** → Run `/create-context` and paste informal notes — any format.

**"Constitution Part 2 not finalized"** → Open `constitution.md`, review Part 2, resolve `[MISSING — ask user]` markers, tell the agent "Constitution Part 2 finalized".

**"Where are the output documents?"** → Most live at `.specify/features/{your-feature}/` — one subfolder per feature. Exceptions: `data-model.md` and `security-design.md` are always living, shared across every feature in the service, at `.specify/service/` (and `api-spec.md` too, if this project_type provides an API).

**"The PR is too large"** → The agent will propose a SPLIT plan automatically. Confirm the split, then do sub-tasks one at a time.

---

## Read Next

| File | When |
|---|---|
| `README.md` | Full command reference and project overview |
| `PROMPT-GUIDE.md` | Full prompt text for every command |
| `.specify/contexts/CONTEXT-GUIDE.md` | Writing a good context file |
| `.specify/memory/roles.yml` | Fill in reviewer names for gates |
| `docs/SUMMARY-GUIDE.md` | How AI-2 summary-first reading works |
