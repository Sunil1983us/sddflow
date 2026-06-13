# Getting Started — SDD Pack
# Steps to First Run

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

Must include a Tech Stack section:
```markdown
## Tech Stack
| Concern | Choice |
|---|---|
| Framework | React 18 |
| Build Tool | Vite |
| State Management | Redux Toolkit |
| Routing | React Router |
| Hosting/CDN | S3 + CloudFront |
...
```
SPECIFY reads this and fills the constitution automatically.

## Step 3 — Fill Manifest + Roles (3 min)
Edit `.specify/manifest.yml` — 4 fields:
```yaml
project:
  name: "Your App Name"
  scope: "pilot"
  feature: "your-feature"
  context_file: "your-feature.md"
```

(Optional but recommended) Edit `.specify/memory/roles.yml` — fill in
names/teams for product_owner, tech_lead, qa_lead, ux_lead,
senior_developer_frontend, etc. Every gate from /validate to /release
references these.

## Step 4 — Run
```bash
claude    # Claude Code Desktop
```
OR open VS Code at project root + GitHub Copilot Chat

## Step 5 — Run the Commands in Order

### Pilot (9 commands + GATE-1)
```
/specify    → fills constitution Part 2 (DRAFT) + generates spec docs
[GATE-1]    → YOU review + finalize constitution Part 2 (manual, blocking)
/validate   → business sign-off on BRD/SRD
/analyze    → risks + complexity
/clarify    → you answer the questions
/plan-arch  → component architecture + plan + refine scope docs
/plan-hld   → HLD diagrams
/task       → Feature → Story → Task + Jira
/implement  → code one task at a time
/release    → UAT + deployment plan + go-live gate
```

### MVP+ (11 commands + GATE-1 — add after /plan-hld)
```
/plan-lld   → LLD + component/class diagrams
/plan-adr   → Architecture Decision Records
```

---

## What Happens at /specify

Two actions automatically:
1. Reads your context → fills constitution.md Part 2 as a DRAFT
   (Tech Stack: Framework, State Management, Routing, API Client,
   Accessibility, Hosting/CDN, and more + Principles + Domain Rules)
2. Generates spec documents (BRD, SRD, Security-Design...)

## What Happens at GATE-1

Constitution Part 2 is a DRAFT until you:
1. Open constitution.md, review every row
2. Resolve any `[MISSING — ask user]` markers
3. Edit anything wrong — your edits are authoritative
4. Tell the agent "Constitution Part 2 finalized"

Nothing after /specify proceeds until this is done.

---

## Read Next
| File | When |
|---|---|
| PROMPT-GUIDE.md | All 11 commands — native `/specify` etc. in Claude Code & Copilot |
| README.md | Full overview |
| HOW-TO-USE.md | Scope presets + tips |
| CHANGE-GUIDE.md | Making changes later |
