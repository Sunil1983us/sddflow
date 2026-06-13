# How To Use — SDD Pack

---

No `.specify/contexts/{feature}.md` yet? Run `/create-context` first —
paste rough notes and the agent drafts context.md with you, instead of
writing it by hand. See `.specify/contexts/CONTEXT-GUIDE.md`.

## The 9 Commands

| Command | What It Does | Scope |
|---|---|---|
| `/specify` | Constitution Part 2 + spec docs | Always |
| `/analyze` | Risks + complexity + unknowns | Always |
| `/clarify` | Questions → you answer → update spec | Always |
| `/plan-arch` | Architecture + implementation plan | Always |
| `/plan-hld` | HLD + all Mermaid diagrams | Always |
| `/plan-lld` | LLD + class/sequence diagrams | MVP+ only |
| `/plan-adr` | Architecture Decision Records | MVP+ only |
| `/task` | Feature → Story → Task + Jira CSV | Always |
| `/implement` | Code one task at a time | Always |

---

## Command Flow

### Pilot
```
/specify → /analyze → /clarify → /plan-arch → /plan-hld → /task → /implement
```

### MVP+
```
/specify → /analyze → /clarify → /plan-arch → /plan-hld
→ /plan-lld → /plan-adr → /task → /implement
```

---

## Scope Presets

### Pilot — Demo / Proof of Concept
```yaml
scope: "pilot"
# Commands: 7 (skip /plan-lld and /plan-adr)
# Documents: BRD, SRD, Analyze, HLD, Plan, Tasks, Jira
```

### MVP — First Production Release
```yaml
scope: "mvp"
# Commands: 9 (all)
# Documents: + LLD, ADRs, QA cases, Runbook
```

### Full — Complete Production
```yaml
scope: "full"
# Commands: 9 (all)
# Documents: + Resilience, Security, Investigation
```

---

## Constitution — How It Gets Filled

/specify reads your context and extracts:

| Extracted | From your context section |
|---|---|
| Language + Framework | Tech stack section |
| Build Tool | Derived from language |
| API Style | Endpoint contracts |
| Messaging | Integration section |
| Database + Cache | Tech stack / integrations |
| DB Migration | Derived from framework |
| Config + Secrets | Infrastructure section |
| Resilience | NFR section |
| Observability + Logging | NFR / tech stack |
| Testing + Coverage | NFR section |
| CI/CD + Orchestration | Infrastructure |
| Core Principles | Domain + constraints |
| Domain Rules | Business rules |
| Never Do | Constraints |

**Tip: richer context = better constitution.**

---

## Review Gates

Each plan sub-command has a reviewer:

| Command | Reviewer | Before Next |
|---|---|---|
| /plan-arch | Tech lead | /plan-hld |
| /plan-hld | Stakeholders + tech lead | /plan-lld or /task |
| /plan-lld | Senior developer | /plan-adr or /task |
| /plan-adr | Architect | /task |
| /task | Product owner + dev team | /implement |

---

## Summary Limits
Edit `.specify/memory/summary-rules.md`:
```
pilot: SUMMARY_MAX_LINES: 20
mvp:   SUMMARY_MAX_LINES: 25
full:  SUMMARY_MAX_LINES: 30
```
Tell agent: "Summary rules updated — re-read summary-rules.md"

---

## PR Rules
```yaml
pr_rules:
  max_lines_per_pr: 400   # change if needed
  max_files_per_pr: 5
```
Agent enforces automatically — estimates before every task.

---

## Upgrading Scope
```
1. Edit manifest.yml: scope: "pilot" → "mvp"
2. Tell agent:
   "Scope upgraded to mvp. Run /plan-lld and /plan-adr.
    Then update /task with new tasks."
```

---

## File Ownership
| File | Owner | Changes |
|---|---|---|
| manifest.yml | You | Per project (4 fields) |
| contexts/{f}.md | You | Per feature |
| constitution.md Part 1 | Framework | Never |
| constitution.md Part 2 | Agent (/specify) | Generated |
| summary-rules.md | You | When limit changes |
| All templates | Framework | Never |
| CLAUDE.md | Framework | Never |
