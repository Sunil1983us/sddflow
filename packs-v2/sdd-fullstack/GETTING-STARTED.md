# Getting Started — SDD Pack
# 5 Steps to First Run

---

## Step 1 — Copy Pack (1 min)
```bash
unzip {pack}-v2.zip -d my-project
cd my-project
git init && git add . && git commit -m "chore: SDD framework"
```

## Step 2 — Write Your Context (15-30 min)
Create `.specify/contexts/my-feature.md`
Open `.specify/contexts/CONTEXT-GUIDE.md` — use it as your guide.

**Not confident writing this yourself?** Run `/create-context` instead —
paste any rough notes (an email, bullet points, half-formed thoughts —
backend, frontend, or both) and the agent drafts `context.md` with you,
asking a plain-language checklist for anything missing. See
PROMPT-GUIDE.md → "/create-context".

Must include a Tech Stack section covering BOTH layers (Backend, Frontend,
Shared):
```markdown
## Tech Stack

### Backend
| Concern | Choice |
|---|---|
| Language | Java 21 |
| Framework | Spring Boot 3.x |
| Database | PostgreSQL 15 |

### Frontend
| Concern | Choice |
|---|---|
| Language | TypeScript 5.x |
| Framework | React 18 |
| State Management | Redux Toolkit |

### Shared
| Concern | Choice |
|---|---|
| API Style | REST + OpenAPI |
| Deployment | Kubernetes |
| CI/CD | Jenkins |
...
```
SPECIFY reads this and fills the constitution automatically.

## Step 3 — Fill Manifest (2 min)
Edit `.specify/manifest.yml` — just 4 fields:
```yaml
project:
  name: "Your Service Name"
  scope: "pilot"
  feature: "your-feature"
  context_file: "your-feature.md"
```

## Step 4 — Run
```bash
claude    # Claude Code Desktop
```
OR open VS Code at project root + GitHub Copilot Chat

## Step 5 — Run the 9 Commands in Order

### Pilot (7 commands)
```
/specify    → fills constitution + generates spec docs
/analyze    → risks + complexity
/clarify    → you answer the questions
/plan-arch  → architecture + plan
/plan-hld   → HLD diagrams
/task       → Feature → Story → Task + Jira
/implement  → code one task at a time
```

### MVP+ (9 commands — add after /plan-hld)
```
/plan-lld   → LLD + class diagrams
/plan-adr   → Architecture Decision Records
```

---

## What Happens at /specify

Two actions automatically:
1. Reads your context → fills constitution.md Part 2
   (Tech Stack — Backend / Frontend / Shared + Principles + Domain Rules)
2. Generates spec documents (BRD, SRD, HLD...)

You never manually fill the constitution.

---

## Read Next
| File | When |
|---|---|
| PROMPT-GUIDE.md | All command prompts — native `/specify` etc. in Claude Code & Copilot |
| README.md | Full overview |
| HOW-TO-USE.md | Scope presets + tips |
| CHANGE-GUIDE.md | Making changes later |
