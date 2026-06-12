# Feature and Story Breakdown — {Feature Name}
> Version: 1.0 | Date: {date}
> Input: srd.summary.md + analyze.summary.md + clarify.summary.md

---

## Feature Definition

### FEATURE-001: {Feature Name}
**Business Capability:** {what business capability this delivers}
**Scope:** {pilot | mvp | full}
**Priority:** Must Have | Should Have | Nice to Have
**Linked BRD Objectives:** BO-{NNN}, BO-{NNN}

---

## Story Breakdown

### STORY-001: {Story Title}
**As** {actor}
**I want** {capability}
**So that** {business value}

**Linked FRs:** FR-{NNN}, FR-{NNN}
**Priority:** Must Have | Should Have
**Story Points:** {1 | 2 | 3 | 5 | 8}
**Sprint:** {1 | 2 | 3}

**Acceptance Criteria:**
- [ ] {verifiable criterion 1 — Given/When/Then preferred}
- [ ] {verifiable criterion 2}
- [ ] {verifiable criterion 3}

**Tasks:**
| Task ID | Title | Est. Lines | PR Strategy |
|---|---|---|---|
| TASK-{NNN} | {title} | {N} | Single / SPLIT |

**Definition of Done:**
- [ ] All tasks complete and merged
- [ ] All acceptance criteria verified
- [ ] Tests passing
- [ ] Code reviewed
- [ ] No critical bugs open

---

### STORY-002: {Story Title}
**As** {actor}
**I want** {capability}
**So that** {business value}

**Linked FRs:** FR-{NNN}
**Priority:** Must Have
**Story Points:** {N}

**Acceptance Criteria:**
- [ ] {criterion}

**Tasks:**
| Task ID | Title | Est. Lines | PR Strategy |
|---|---|---|---|
| TASK-{NNN} | {title} | {N} | Single |

---

## Story Map

```
FEATURE-001: {Feature Name}
│
├── SPRINT 1
│   ├── STORY-001: {title} [{N} pts]
│   │     TASK-001, TASK-002, TASK-003
│   └── STORY-002: {title} [{N} pts]
│         TASK-004, TASK-005
│
├── SPRINT 2
│   ├── STORY-003: {title} [{N} pts]
│   │     TASK-006, TASK-007, TASK-008
│   └── STORY-004: {title} [{N} pts]
│         TASK-009, TASK-010
│
└── SPRINT 3
    └── STORY-005: {title} [{N} pts]
          TASK-011-A, TASK-011-B, TASK-012
```

---

## Traceability Matrix

| Story | FR | NFR | Tasks | PR Count |
|---|---|---|---|---|
| STORY-001 | FR-001, FR-002 | NFR-001 | TASK-001, TASK-003 | 2 |
| STORY-002 | FR-003 | — | TASK-008, TASK-011-A | 2 |

---

## Jira Import Summary

```csv
Issue Type,Summary,Story Points,Priority,Epic Link,Sprint,Acceptance Criteria
Epic,{Feature Name},,,,,
Story,{STORY-001 title},3,High,{Feature},"Sprint 1",{criteria}
Task,{TASK-001 title},1,High,{Feature},"Sprint 1",{criteria}
Story,{STORY-002 title},5,High,{Feature},"Sprint 1",{criteria}
```

---

## Summary
> Lines: {N} / {SUMMARY_MAX_LINES}

## What
{Feature delivers: list stories in one line each}

## Stories
{STORY-NNN}: {title} — {N} pts — Sprint {N}

## Traceability
{FR-NNN} → STORY-NNN → TASK-NNN

## Sprint Plan
Sprint 1: {N} pts | Sprint 2: {N} pts | Sprint 3: {N} pts
