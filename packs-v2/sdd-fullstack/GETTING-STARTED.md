# Getting Started — Fullstack Pack
# Backend + Frontend full system

## 5 Steps to First Run

### Step 1 — Copy Pack (1 min)
```bash
unzip sdd-fullstack-v2.zip -d my-project
cd my-project
git init && git add . && git commit -m "chore: SDD framework"
```

### Step 2 — Write Context (15-30 min)
Create `.specify/contexts/my-feature.md`
Use `.specify/contexts/CONTEXT-GUIDE.md` as your guide.
Include your tech stack — SPECIFY extracts it for constitution.

### Step 3 — Fill Manifest (2 min)
Edit `.specify/manifest.yml`:
```yaml
project:
  name: "Your Service Name"
  scope: "pilot"
  feature: "my-feature"
  context_file: "my-feature.md"
```

### Step 4 — Run
```bash
claude    # Claude Code Desktop
# OR open VS Code at project root + Copilot Chat
```

### Step 5 — Paste Step 0 from PROMPT-GUIDE.md
Follow the 6 verbs: SPECIFY → ANALYZE → CLARIFY → PLAN → TASK → IMPLEMENT

---

## What Happens at SPECIFY

Agent reads your context and automatically:
1. Fills constitution.md Part 2 (Tech Stack + Principles + Domain Rules)
2. Generates spec documents (BRD, SRD, HLD...)

You never manually fill the constitution.

---

## Read Next
| File | When |
|---|---|
| PROMPT-GUIDE.md | Running the pipeline |
| README.md | Full overview |
| CHANGE-GUIDE.md | Making changes later |
| docs/SUMMARY-GUIDE.md | How summaries work |
