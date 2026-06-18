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
| `/plan-arch` | Screen/app architecture + plan + refine scope docs | Always |
| `/plan-hld` | HLD + all Mermaid diagrams (screen flow + navigation) | Always |
| `/plan-lld` | LLD + class/component diagrams | MVP+ only |
| `/plan-adr` | Architecture Decision Records | MVP+ only |
| `/task` | Feature → Story → Task + Jira CSV | Always |
| `/implement` | Code one task at a time | Always |
| `/release` | UAT + store-release plan + go-live gate | Always |

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
# /specify docs: brd, srd, security-design (§1)
# /implement: code + tests only (no qa_cases/runbook)
```

### MVP — First Production Release
```yaml
scope: "mvp"
# Commands: 11 + GATE-1 (all)
# /specify docs: + screen-spec, ux-flow, Backend API Contract
#   (Consumer), security-design (§1-2)
# /implement: + QA cases, Runbook
```

### Full — Complete Production
```yaml
scope: "full"
# Commands: 11 + GATE-1 (all)
# /specify docs: + Local Data & Cache Model, Mobile Resilience,
#   Crash & Incident Triage, security-design (§1-4)
# /implement: + QA cases, Runbook
```

---

## Document Inventory by Scope/Command (canonical)

| Command | Pilot | MVP | Full |
|---|---|---|---|
| /specify | brd, srd, security-design (§1) | + screen-spec, ux-flow, api-spec (Backend API Contract — Consumer), security-design (§1-2) | + data-model (Local Data & Cache Model), resilience (Mobile Resilience), investigation (Crash & Incident Triage), security-design (§1-4) |
| /validate | validate.md — all scopes |||
| /analyze | analyze.md — gated on validate.summary.md = "VALIDATE complete" |||
| /clarify | clarify.md — all scopes |||
| /plan-arch | arch.md + plan.md — gated on clarify RESOLVED + AI-8 (no unresolved [ASSUMPTION-NNN]); also refines screen-spec, ux-flow, api-spec (mvp+), and data-model, resilience, investigation, security-design (full) |||
| /plan-hld | hld.md — all scopes |||
| /plan-lld | ❌ | lld.md | lld.md |
| /plan-adr | ❌ | ADRs (also fills arch.md §4) | ADRs (also fills arch.md §4) |
| /task | stories.md, tasks.md, jira CSV — all scopes |||
| /implement | code + tests | + qa_cases, runbook | + qa_cases, runbook |
| /release | release.md — gated on all tasks merged |||

---

## Constitution — How It Gets Filled

/specify reads your context and extracts (as a DRAFT — see GATE-1):

| Extracted | From your context section |
|---|---|
| Language + Framework | Tech stack section |
| Navigation | Tech stack / architecture section |
| State Management | Tech stack / architecture section |
| Local Storage/DB | Tech stack section |
| API Client | Tech stack / integrations |
| Push Notifications | Tech stack / integrations |
| Crash/Analytics | Tech stack / NFR section |
| Build Tool | Derived from framework |
| Testing + Coverage Gate | NFR section |
| Quality/Security | NFR / domain constraints |
| CI/CD | Infrastructure |
| App Store Distribution | Infrastructure / release section |
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

No `/validate`, `/analyze`, or any later command may run until this gate
passes. A later `/specify` re-run must propose changes for review — it
will never silently overwrite a finalized Part 2.

---

## Review Gates

| Command | Reviewer (see roles.yml) | Before Next |
|---|---|---|
| GATE-1 | tech_lead (accountable), architect (consulted) | /validate |
| /validate | business_analyst (responsible), product_owner (accountable) | /analyze |
| /analyze | tech_lead (+ architect, security_officer consulted) | /clarify |
| /clarify | tech_lead (responsible), product_owner (accountable), business_analyst (consulted) | /plan-arch |
| /plan-arch | architect (responsible), tech_lead (accountable) | /plan-hld |
| /plan-hld | tech_lead (+ ux_lead consulted), product_owner + qa_lead informed | /plan-lld or /task |
| /plan-lld | senior_developer_mobile (responsible), tech_lead (accountable) | /plan-adr or /task |
| /plan-adr | architect (+ tech_lead consulted) | /task |
| /task | tech_lead (responsible), product_owner (accountable), qa_lead (consulted) | /implement |
| /implement | assigned developer (responsible), tech_lead (accountable) — per PR | /release |
| /release | qa_lead (responsible), product_owner (accountable), tech_lead + devops_sre + security_officer (consulted) | go-live |

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
