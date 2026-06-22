# Getting Started — SDD Pack
# Steps to First Run

---

## Step 1 — Copy Pack (1 min)
```bash
unzip {pack}.zip -d my-project
cd my-project
git init && git add . && git commit -m "chore: SDD framework"
```

## Step 2 — Write Your Context (15-30 min)

Create `.specify/contexts/my-feature.md`.
Open `.specify/contexts/CONTEXT-GUIDE.md` — use it as your guide.

**Not confident writing this yourself?** Run `/create-context` instead —
paste any rough notes and the agent drafts `context.md` with you.

Must include a Tech Stack section:
```markdown
## Tech Stack
| Concern | Choice |
|---|---|
| Backend Language | TypeScript (Node.js) |
| Backend Framework | Express / NestJS |
| Frontend Framework | React |
| Database | PostgreSQL |
| CI/CD | GitHub Actions |
```

## Step 3 — Fill Manifest + Roles (3 min)

Edit `.specify/manifest.yml`:
```yaml
project:
  name: "Your App"
  scope: "pilot"        # pilot | mvp | full
  feature: "your-feature"
  context_file: "your-feature.md"

reading_mode: "auto"    # auto | summary | full
```

(Optional but recommended) Edit `.specify/memory/roles.yml` — fill in
names/teams for product_owner, tech_lead, qa_lead, etc.

## Step 4 — Open in Your AI Tool

```bash
claude    # Claude Code Desktop — type /start
```
OR open VS Code at project root + GitHub Copilot Chat

## Step 5 — Run the Commands in Order

### Pilot (shorter path)
```
/specify          → Constitution Part 2 (DRAFT only — spec docs are separate)
[GATE-1]          → YOU review + finalize constitution Part 2 (manual, blocking)
/specify-brd      → Business Requirements Document
/specify-uc       → Use Case Specification (Actors, MP/AP/EP)
/specify-srd      → Software Requirements Document
/checklist        → Spec quality gate (optional for pilot)
/validate         → Business sign-off on BRD + Use Cases + SRD
/analyze          → Risks + complexity + distributed systems check
/clarify          → You answer the ambiguities
/plan-design      → Architecture + Diagrams + API Design + ADRs
/task             → Feature → Story → Task + Jira export
/implement        → Code one task at a time
/release          → UAT + deployment plan + go-live gate
```

### MVP+ (full path — adds extended docs, LLD, QA cases)
```
/specify → [GATE-1] → /specify-brd → /specify-uc → /specify-srd
→ /specify-doc security → /specify-doc data-model
→ /checklist (mandatory) → /validate → /analyze → /clarify
→ /plan-design → /plan-lld → /task → /implement → /release
```

---

## What Happens at /specify

`/specify` generates **constitution Part 2 only** (DRAFT):
- Reads your context → fills Tech Stack (20 concerns) + Principles + Domain Rules + Never Do
- Lists any `[MISSING — ask user]` rows as Open Items for GATE-1

Spec documents are generated one at a time using sub-commands:
- `/specify-brd` → BRD (gate: GATE-1 passed)
- `/specify-uc` → Use Cases (gate: BRD approved)
- `/specify-srd` → SRD (gate: Use Cases approved)
- `/specify-doc {name}` → extended docs (gate: SRD approved)

## What Happens at GATE-1

Constitution Part 2 is a DRAFT until you:
1. Open `constitution.md`, review every row
2. Resolve any `[MISSING — ask user]` markers
3. Edit anything wrong — your edits are authoritative
4. Tell the agent "Constitution Part 2 finalized"

Nothing after `/specify` proceeds until this is done.

## What is /specify-uc?

`/specify-uc` generates a Use Case Specification with:
- **ACT-NNN** Actor Registry (Primary / Secondary / System actors)
- **UC-NNN** for each use case:
  - **Main Path (MP)** — numbered steps with Actor | Action | System Response
  - **Alternate Paths (AP-NNN-X)** — diverge at step N, resume at step M
  - **Exception Paths (EP-NNN-X)** — error at step N, system response, recovery
- Traceability: UC-NNN → BR-NNN (BRD) → FR-NNN (SRD)

The SRD derives every functional requirement from these use case paths.

---

## Read Next

| File | When |
|---|---|
| `README.md` | Full command reference |
| `.specify/contexts/CONTEXT-GUIDE.md` | Writing a good context file |
| `.specify/memory/roles.yml` | Fill in reviewer names for gates |
| `docs/SUMMARY-GUIDE.md` | How AI-2 reading mode works |
