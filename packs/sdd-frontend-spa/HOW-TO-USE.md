# How To Use — SDD Pack

---

## The 11 Commands

| Command | What It Does | Scope |
|---|---|---|
| `/specify` | Constitution Part 2 (DRAFT) + spec docs | Always |
| **GATE-1** | You review + finalize constitution Part 2 (manual) | Always |
| `/validate` | Business sign-off on BRD/SRD | Always |
| `/analyze` | Risks + complexity + unknowns | Always |
| `/clarify` | Questions → you answer → update spec | Always |
| `/plan-arch` | Component architecture + plan + refine scope docs | Always |
| `/plan-hld` | HLD + all Mermaid diagrams | Always |
| `/plan-lld` | LLD + component/class diagrams | MVP+ only |
| `/plan-adr` | Architecture Decision Records | MVP+ only |
| `/task` | Feature → Story → Task + Jira CSV | Always |
| `/implement` | Code one task at a time | Always |
| `/release` | UAT + deployment plan + go-live gate | Always |

---

## Command Flow

### Pilot
```
/specify → [GATE-1] → /validate → /analyze → /clarify
→ /plan-arch → /plan-hld → /task → /implement → /release
```

### MVP+
```
/specify → [GATE-1] → /validate → /analyze → /clarify
→ /plan-arch → /plan-hld → /plan-lld → /plan-adr
→ /task → /implement → /release
```

---

## Scope Presets

### Pilot — Demo / Proof of Concept
```yaml
scope: "pilot"
# Commands: 9 + GATE-1 (skip /plan-lld and /plan-adr)
# /specify docs: BRD, SRD, Security-Design (§1)
# /implement: code + tests only (no qa_cases/runbook)
```

### MVP — First Production Release
```yaml
scope: "mvp"
# Commands: 11 + GATE-1 (all)
# /specify docs: + Component-Spec, UX-Flow, Backend API Contract
#   (Consumer), Security-Design (§1-2)
# /implement: + QA cases, Runbook
```

### Full — Complete Production
```yaml
scope: "full"
# Commands: 11 + GATE-1 (all)
# /specify docs: + Frontend State & Storage Model, Frontend Resilience,
#   Production Debugging & Error Tracking, Security-Design (§1-4)
# /implement: + QA cases, Runbook
```

---

## Constitution — How It Gets Filled

/specify reads your context and extracts (as a DRAFT — see GATE-1):

| Extracted | From your context section |
|---|---|
| Language + Framework | Tech stack section |
| Build Tool | Derived from framework |
| State Management | Tech stack / architecture section |
| Component Library/Design System | Tech stack section |
| Routing | Tech stack section |
| API Client | Tech stack / integrations |
| Data Cache | Tech stack / NFR section |
| Configuration + Secrets | Infrastructure section |
| Resilience | NFR section |
| Observability + Logging | NFR / tech stack |
| Testing + Coverage Gate | NFR section |
| Linting/Formatting | Tech stack section |
| Accessibility | NFR / domain constraints |
| CI/CD + Hosting/CDN | Infrastructure |
| Core Principles | Domain + constraints |
| Domain Rules | Business rules |
| Never Do | Constraints |

**Tip: richer context = better constitution draft.**

---

## GATE-1 — Finalize Constitution Part 2 (manual, blocking)

After /specify Action 1, Part 2 is a DRAFT. Before /validate can run:

1. Open `.specify/memory/constitution.md` → Part 2
2. Review every row — Tech Stack, Core Principles, Domain Rules, Never Do
3. Resolve any `[MISSING — ask user]` markers
4. Edit anything wrong directly — your edits are AUTHORITATIVE
5. Tell the agent: **"Constitution Part 2 finalized"**

A later `/specify` re-run must propose changes for review — it will
never silently overwrite a finalized Part 2.

---

## Review Gates

| Command | Reviewer (see roles.yml) | Before Next |
|---|---|---|
| GATE-1 | Tech lead (accountable) | /validate |
| /validate | Product owner + Business analyst | /analyze |
| /analyze | Tech lead (+ architect, security officer consulted) | /clarify |
| /clarify | Product owner (accountable), Business analyst (consulted) | /plan-arch |
| /plan-arch | Tech lead (+ architect, UX lead consulted) | /plan-hld |
| /plan-hld | Stakeholders + tech lead (+ UX lead) | /plan-lld or /task |
| /plan-lld | Senior developer (frontend) | /plan-adr or /task |
| /plan-adr | Architect | /task |
| /task | Product owner + dev team (+ QA lead, UX lead consulted) | /implement |
| /implement | Assigned developer (responsible), tech lead (accountable) — per PR | /release |
| /release | QA lead (responsible), product owner (accountable) | go-live |

---

## Summary Limits
Edit `.specify/memory/summary-rules.md`:
```
pilot: SUMMARY_MAX_LINES: 20
mvp:   SUMMARY_MAX_LINES: 25
full:  SUMMARY_MAX_LINES: 30
```
Tell agent: "Summary rules updated — re-read summary-rules.md"

After /specify, every command reads only `.summary.md` files (AI-2) —
except /implement, which reads tasks.md + constitution.md in full.

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
| .specify/memory/roles.yml | You | RACI owners per project |
| constitution.md Part 1 | Framework | Never |
| constitution.md Part 2 | Agent (/specify) → You (GATE-1) | Generated draft, then finalized |
| summary-rules.md | You | When limit changes |
| All templates | Framework | Never |
| CLAUDE.md | Framework | Never |
