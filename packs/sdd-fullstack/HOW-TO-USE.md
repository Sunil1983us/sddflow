# How To Use — SDD Pack

---

No `.specify/contexts/{feature}.md` yet? Run `/create-context` first —
paste rough notes (backend, frontend, or both) and the agent drafts
context.md with you. See `.specify/contexts/CONTEXT-GUIDE.md`.

## The 11 Commands

| Command | What It Does | Scope |
|---|---|---|
| `/specify` | Constitution Part 2 (DRAFT, both layers) + spec docs | Always |
| **GATE-1** | You review + finalize constitution Part 2 (manual) | Always |
| `/validate` | Business sign-off on BRD/SRD | Always |
| `/analyze` | Risks + complexity + unknowns | Always |
| `/clarify` | Questions → you answer → update spec | Always |
| `/plan-arch` | Architecture + plan + refine scope docs (both layers) | Always |
| `/plan-hld` | HLD + all Mermaid diagrams | Always |
| `/plan-lld` | LLD + class/component diagrams | MVP+ only |
| `/plan-adr` | Architecture Decision Records | MVP+ only |
| `/task` | Feature → Story → Task + Jira CSV | Always |
| `/implement` | Code one task at a time, PR rules enforced (both layers) | Always |
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
# /implement: code + tests + openapi.yaml (no qa_cases/runbook)
```

### MVP — First Production Release
```yaml
scope: "mvp"
# Commands: 11 + GATE-1 (all)
# /specify docs: + API Spec (Shared API Contract), Component-Spec,
#   UX-Flow, Data Model (Backend Schema & Persistence Model),
#   Security-Design (§1-2)
# /implement: + QA cases, Runbook
```

### Full — Complete Production
```yaml
scope: "full"
# Commands: 11 + GATE-1 (all)
# /specify docs: + Resilience, Investigation, Security-Design (§1-4)
# /implement: + QA cases, Runbook
```

---

## Constitution — How It Gets Filled

/specify reads your context and extracts (as a DRAFT — see GATE-1),
split across Backend, Frontend, and Shared:

### Backend
| Extracted | From your context section |
|---|---|
| Language + Framework | Backend Tech Stack section |
| Build Tool | Derived from framework |
| Messaging/Async | Integration section |
| Schema | API/data section |
| Data Store + Data Cache | Tech stack / integrations |
| DB Migration | Derived from framework |
| Resilience | NFR section |
| Testing + Coverage Gate | NFR section |

### Frontend
| Extracted | From your context section |
|---|---|
| Language + Framework | Frontend Tech Stack section |
| Build Tool | Derived from framework |
| State Management | Tech stack / architecture section |
| Component Library/Design System | Tech stack section |
| Routing | Tech stack section |
| API Client | Tech stack / integrations |
| Data Cache | Tech stack / NFR section |
| Testing + Coverage Gate | NFR section |
| Accessibility | NFR / domain constraints |

### Shared
| Extracted | From your context section |
|---|---|
| API Style + Serialisation | Endpoint contracts / API section |
| Configuration + Secrets | Infrastructure section |
| Observability + Logging | NFR / tech stack |
| Quality/Security | NFR / constraints |
| Orchestration + CI/CD | Infrastructure |
| Core Principles | Domain + constraints |
| Domain Rules | Business rules (both layers) |
| Never Do | Constraints |

**Tip: richer context = better constitution draft.**

---

## GATE-1 — Finalize Constitution Part 2 (manual, blocking)

After /specify Action 1, Part 2 is a DRAFT. Before /validate can run:

1. Open `.specify/memory/constitution.md` → Part 2
2. Review every row — Backend Tech Stack, Frontend Tech Stack, Shared
   Tech Stack, Core Principles, Domain Rules, Never Do
3. Resolve any `[MISSING — ask user]` markers
4. Edit anything wrong directly — your edits are AUTHORITATIVE
5. Tell the agent: **"Constitution Part 2 finalized"**

A later `/specify` re-run must propose changes for review — it will
never silently overwrite a finalized Part 2.

---

## Review Gates

| Command | Reviewer (see roles.yml) | Before Next |
|---|---|---|
| GATE-1 | Tech lead (responsible + accountable; architect consulted) | /validate |
| /validate | Business analyst (responsible), product owner (accountable) | /analyze |
| /analyze | Tech lead (+ architect, security officer consulted) | /clarify |
| /clarify | Tech lead (responsible), product owner (accountable) + business analyst consulted | /plan-arch |
| /plan-arch | Architect (responsible), tech lead (accountable) | /plan-hld |
| /plan-hld | Tech lead (+ UX lead consulted, stakeholders informed) | /plan-lld or /task |
| /plan-lld | Senior developer (backend + frontend), tech lead (accountable) | /plan-adr or /task |
| /plan-adr | Architect (+ tech lead consulted) | /task |
| /task | Tech lead (responsible), product owner (accountable) + QA lead consulted | /implement |
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
