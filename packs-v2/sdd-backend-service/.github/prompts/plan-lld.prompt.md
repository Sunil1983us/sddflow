---
mode: agent
description: PLAN-LLD — Low Level Design with class and sequence diagrams
---

## Before Starting
- Read .specify/manifest.yml
- Read .specify/memory/constitution.md
- Read .specify/memory/summary-rules.md
- Read .specify/features/{manifest.project.feature}/plan.summary.md
- Read .specify/features/{manifest.project.feature}/arch.summary.md
- Read .specify/templates/lld-template.md

## Scope Check
If manifest.scope = pilot → STOP.
State: "PLAN-LLD skipped — pilot scope. Proceed to PLAN-ADR or TASK."

## Verify Gate
arch.md + hld.md must exist and be reviewed.
If missing — STOP. Run PLAN-ARCH and PLAN-HLD first.

## Your Task
Generate LLD with detailed technical diagrams in Mermaid.

### Package / Folder Structure
Full directory tree — every package/folder and its purpose

### Class Diagram (backend)
All classes + interfaces + relationships — classDiagram
Include: fields, key methods, implements/extends

### Component Diagram (frontend/mobile)
All components + props + events — graph TD or classDiagram

### Detailed Sequence Diagrams
One per key flow (happy path + key unhappy paths)
Controller → Service → Port → Adapter — sequenceDiagram
Include: error handling paths

### ERD (if database)
All tables + columns + relationships — erDiagram

### Key Method Signatures
Per layer — exact method names and types

### DTO/Record Definitions
All request/response structures

Save: docs/lld/lld.md
Save: docs/lld/lld.summary.md (max SUMMARY_MAX_LINES)

State: "PLAN-LLD complete — review lld.md before PLAN-ADR"
Wait for review.
