# Flow, Roles & Gates — Full Reference

> Unified `plan_mode`, `mvp+` scope shown (the fullest path). Pilot scope
> skips some steps — see "Scope Reference" below. Separate `plan_mode`
> splits PLAN into three gated documents instead of one — see "Plan —
> Separate Mode" below. This mirrors [`CLAUDE.md`](CLAUDE.md) and
> [`.specify/memory/roles.yml`](.specify/memory/roles.yml) — if either
> changes, re-check this file too.

---

## Two Different "Who"s — Don't Conflate Them

The framework has two separate role systems that answer different questions.
Mixing them up is the most common source of confusion:

| | Virtual Team | `roles.yml` RACI |
|---|---|---|
| **Answers** | Who does the *writing*, in chat? | Who, as a real human, has to *approve*? |
| **Who** | Maya, Rex, Ava, Leo, Kai, Quinn, Riley, Morgan | Product Owner, Business Analyst, Tech Lead, Architect, Senior Developer, QA Lead, Security Officer, DevOps/SRE, UX Lead |
| **How it's used** | Address by name in chat (`Maya, create BRD`) — the AI runs the matching command | Filled in once per project with real names — referenced by every gate below |
| **Is it a real person?** | No — an AI persona / command shortcut | Yes |

---

## The Pipeline

Legend: `▶` = agent-run command · `⏸ GATE` = manual, blocks the next command until it passes.

```
▶ /create-context   (Maya, optional)
    Turns rough notes into context.md — skip if you already have one

▶ /specify   (Maya)
    Constitution Part 2 (DRAFT) — tech stack, principles, domain rules

⏸ GATE — Constitution Part 2 finalized  (you type "finalized")
    R/A: Tech Lead · C: Architect · I: Product Owner

▶ /specify-brd   (Maya)  →  brd.md — BO-NNN, BR-NNN
▶ /specify-uc    (Maya)  →  use-cases.md — UC-NNN with Main/Alt/Exception paths
▶ /specify-srd   (Rex)   →  srd.md — FR-NNN / NFR-NNN
▶ /specify-doc {name}  (Ava)  →  extended docs: security-design (living),
    data-model (living), plus this pack's extended docs — see CLAUDE.md SPECIFY section

⏸ GATE — security-design.md reviewed  (mvp+ only)
    R/A: Security Officer · C: Tech Lead · I: Product Owner

▶ /checklist   (Quinn — optional at pilot, mandatory mvp+)
    Spec-quality audit — catches vague NFRs, missing acceptance criteria

▶ /validate   (Maya)
    Business sign-off on BRD + SRD

⏸ GATE — Business sign-off
    R: Business Analyst · A: Product Owner · C: Tech Lead · I: QA Lead

▶ /analyze   (Ava)
    Risk register, complexity, dependency map — R-NNN

⏸ GATE — Risk review
    R/A: Tech Lead · C: Architect, Security Officer · I: Product Owner

▶ /clarify   (Rex)
    Resolves every open question — no unresolved [ASSUMPTION-NNN] past here (AI-8)

⏸ GATE — All items resolved
    R: Tech Lead · A: Product Owner · C: Business Analyst

── Plan — Unified Mode ──────────────────────────────────────────────
▶ /plan-design   (Ava)
    Architecture + diagrams + API design + ADRs — one document, one gate

── or — Plan — Separate Mode (three gates instead of one) ──────────
▶ /plan-arch   (Ava)  →  arch.md
⏸ GATE — /plan-arch reviewed
    R: Architect · A: Tech Lead · I: Product Owner

▶ /plan-hld    (Ava)  →  hld.md — C4 context, sequence, state diagrams
⏸ GATE — /plan-hld reviewed
    R/A: Tech Lead · C: UX Lead · I: Product Owner, QA Lead

▶ /plan-adr    (Ava, mvp+)  →  adr.md
⏸ GATE — /plan-adr reviewed  (mvp+)
    R/A: Architect · C: Tech Lead

── Both modes rejoin here ───────────────────────────────────────────
▶ /plan-lld   (Leo — mvp+, skipped at pilot)
    Class / sequence / package diagrams

⏸ GATE — /plan-lld reviewed  (mvp+)
    R: Senior Developer · A: Tech Lead

▶ /task   (Kai)
    QA test cases (mvp+) → stories.md (MoSCoW) → tasks.md

⏸ GATE — QA test cases reviewed  (mvp+)
    R/A: QA Lead · C: Tech Lead · I: Product Owner

⏸ GATE — Stories + tasks approved
    R: Tech Lead · A: Product Owner · C: QA Lead · I: DevOps/SRE

▶ /implement   (Leo)
    One TASK-NNN at a time — code + paired test, per PR

⏸ GATE — Per-task PR approval  (repeats for every task)
    R: Assigned Developer · A: Tech Lead

▶ /release   (Riley)
    UAT plan + deployment plan + smoke test + BO closure

⏸ GATE — UAT + go-live  (the final gate)
    R: QA Lead · A: Product Owner · C: Tech Lead, DevOps/SRE, Security Officer
    I: Business Analyst
```

**`/orchestrate` (Morgan)** runs this entire pipeline in one command,
pausing automatically at every gate above for your input — same steps,
same RACI, just driven end-to-end instead of one command at a time.

---

## Traceability Chain

Every requirement is supposed to be traceable end-to-end. `/release`'s
pre-release checklist checks this literally: every `FR-NNN` must have
≥ 1 passing `TC-NNN`.

```
BO-NNN (brd.md) → BR-NNN (brd.md) → FR-NNN / NFR-NNN (srd.md)
  → UC-NNN (use-cases.md, Given/When/Then)
  → STORY-NNN (stories.md, Satisfies: FR-NNN)
  → TASK-NNN (tasks.md, Satisfies: FR-NNN)
  → TC-NNN (qa-testcases.md, mvp+)
```

---

## Document Review — Three Modes

The `Status:` header inside each `.md` file is the authoritative gate in
**every** mode — Jira/Confluence are integrations on top of it, never a
prerequisite.

| Mode | Setup | How approval works | Audit trail |
|---|---|---|---|
| **chat** *(default)* | none | Reviewer reads the doc in chat, says "approved" → agent flips `Status: Draft → Approved` | Doc header + git history |
| **local** | `pip install sddflow` | Same, plus `sdd review approve --local` records who/when/why. Also usable from `sdd dashboard`'s Approve button | `.specify/.local-approvals.yml` |
| **jira** | `.specify/integrations.yml` | `sdd review submit / check / apply` — a real Confluence page + Jira review story per document | Jira + Confluence |

---

## Full RACI Matrix — All 13 Gates

| Gate | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| Constitution Part 2 finalized | Tech Lead | Tech Lead | Architect | Product Owner |
| security-design.md reviewed (mvp+) | Security Officer | Security Officer | Tech Lead | Product Owner |
| `/validate` — business sign-off | Business Analyst | Product Owner | Tech Lead | QA Lead |
| `/analyze` — risk review | Tech Lead | Tech Lead | Architect, Security Officer | Product Owner |
| `/clarify` — all items resolved | Tech Lead | Product Owner | Business Analyst | — |
| `/plan-arch` reviewed | Architect | Tech Lead | — | Product Owner |
| `/plan-hld` reviewed | Tech Lead | Tech Lead | UX Lead | Product Owner, QA Lead |
| `/plan-lld` reviewed (mvp+) | Senior Developer | Tech Lead | — | — |
| `/plan-adr` reviewed (mvp+) | Architect | Architect | Tech Lead | — |
| `/task` — QA test cases reviewed (mvp+) | QA Lead | QA Lead | Tech Lead | Product Owner |
| `/task` — stories + tasks approved | Tech Lead | Product Owner | QA Lead | DevOps/SRE |
| `/implement` — per-task PR approval | Assigned Developer | Tech Lead | — | — |
| `/release` — UAT + go-live | QA Lead | Product Owner | Tech Lead, DevOps/SRE, Security Officer | Business Analyst |

---

## Scope Reference — What pilot / mvp / full Each Produce

| Document / Command | pilot | mvp | full |
|---|---|---|---|
| BRD, Use Cases, SRD | ✅ | ✅ | ✅ |
| `/checklist` | optional | **mandatory** | **mandatory** |
| Security Design (living) | §1 | §1–2 | §1–4 |
| API Spec (provider services, living) | — | ✅ | ✅ |
| Data Model (living) | — | ✅ | ✅ |
| Resilience | — | — | ✅ |
| Investigation | — | — | ✅ |
| `/plan-lld` | skipped | ✅ | ✅ |
| QA Test Cases (full `qa-testcases.md`) | skipped | ✅ | ✅ |
| Smoke Tests (≤10 cases, replaces QA Test Cases) | ✅ | — | — |
| Runbook (living) | — | ✅ | ✅ |

---

## Too Much Ceremony for a Tiny Project?

If a project doesn't need any of the above — no BRD, no Use Cases, no
SRD, no RACI, no Jira/Confluence, no traceability chain — the SDD
Framework has a separate, deliberately minimal pack (`sdd-micro`) for
scripts and personal projects: just `/specify → [GATE-1] → /task →
/implement`. It's a different pack, not a mode of this one — see the SDD
Framework project (`sunil1983us/sddflow`) if that fits better.
