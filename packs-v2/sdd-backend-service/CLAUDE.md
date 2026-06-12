# CLAUDE.md — Backend Service Pack
# REST APIs, microservices, databases, messaging
# 6-Verb: SPECIFY→ANALYZE→CLARIFY→PLAN→TASK→IMPLEMENT

## Startup
1. Read .specify/manifest.yml
2. Read .specify/memory/constitution.md
3. Read .specify/memory/summary-rules.md
4. Confirm: project.name, scope, feature, context_file
5. If constitution Part 2 not generated → remind user to run SPECIFY first

## SPECIFY — Two Actions in Order

Action 1 — Generate constitution.md Part 2 from context:
  Read context file → extract all tech decisions
  Fill Tech Stack table (Language, Framework, Build Tool,
  API Style, Messaging/Async, Serialisation, Schema,
  Data Store, Data Cache, DB Migration, Configuration,
  Secrets, Resilience, Observability, Logging, Testing,
  Coverage Gate, Quality/Security, Orchestration, CI/CD)
  Extract Core Principles from domain constraints
  Extract Domain Rules from business rules
  Extract Never Do from stated constraints
  Save updated constitution.md — Part 1 unchanged

Action 2 — Generate spec documents per scope:
  pilot:  brd, srd, analyze, hld, plan, tasks, stories, jira
  mvp:    + lld, adr, qa_cases, runbook
  full:   + resilience, investigation, security_design, openapi

## 6-Verb Gates
ANALYZE → CLARIFY → PLAN → TASK → IMPLEMENT
Each gate requires previous verb complete.

## PR Contract
Estimate before every task.
If > max_lines_per_pr → SPLIT A/B/C → confirm → one at a time.
After task: state files + lines + "PR ready" → wait for go.

## Summary
After every doc: write .summary.md (max SUMMARY_MAX_LINES).

## Never Do
Never start PLAN without clarify.summary.md
Never start IMPLEMENT without TASK approved
Never code before context.md updated
Never hardcode any value
Never skip paired test

## PLAN Sub-Commands

PLAN is split into 4 sub-commands — each has its own review gate:

/plan-arch  → Architecture decisions + plan.md
              Gate: clarify.summary.md must exist
              Review: tech lead approves arch + plan

/plan-hld   → HLD + all Mermaid diagrams
              Gate: arch.md reviewed
              Review: stakeholders + tech lead
              Pilot: always run | MVP+: always run

/plan-lld   → LLD + class/sequence diagrams
              Gate: hld.md reviewed
              Scope check: SKIP if pilot — state skip reason
              Review: senior developer

/plan-adr   → Architecture Decision Records
              Gate: arch.md reviewed
              Scope check: SKIP if pilot — state skip reason
              Review: architect

## Command Order
SPECIFY → ANALYZE → CLARIFY → PLAN-ARCH → PLAN-HLD
→ PLAN-LLD (mvp+) → PLAN-ADR (mvp+) → TASK → IMPLEMENT
