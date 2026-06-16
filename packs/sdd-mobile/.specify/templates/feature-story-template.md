# Feature and Story Breakdown
# Feature: {Feature Name}
> Version: 1.0 | Date: {date}

---

## References
| Source | Sections / IDs Used |
|---|---|
| srd.summary.md | {sections/IDs referenced} |
| plan.summary.md | {sections/IDs referenced} |

## Feature Definition

### FEATURE-001: {Feature Name}
**Business Capability:** {what business capability this delivers}
**Scope:** {pilot | mvp | full}
**Priority:** Must Have
**Linked BRD Objectives:** BO-{NNN}

---

## Stories

### STORY-001: {Story Title}
**As** {actor}
**I want** {capability}
**So that** {business value}

**Linked FRs:** FR-{NNN}, FR-{NNN}
**Story Points:** {1|2|3|5|8} | **Sprint:** 1

**Acceptance Criteria:**
- [ ] {Given/When/Then criterion 1}
- [ ] {Given/When/Then criterion 2}

**Tasks:** TASK-001, TASK-002, TASK-003

---

### STORY-002: {Story Title}
**As** {actor}
**I want** {capability}
**So that** {business value}

**Linked FRs:** FR-{NNN}
**Story Points:** {N} | **Sprint:** 1

**Acceptance Criteria:**
- [ ] {criterion}

**Tasks:** TASK-004, TASK-005

---

### STORY-003: {Story Title}
**As** {actor}
**I want** {capability}
**So that** {business value}

**Linked FRs:** FR-{NNN}
**Story Points:** {N} | **Sprint:** 2

**Acceptance Criteria:**
- [ ] {criterion}

**Tasks:** TASK-006, TASK-007, TASK-008

---

## Story Map

```
FEATURE-001: {Feature Name}

Sprint 1:
  STORY-001: {title} [{N} pts]
    TASK-001, TASK-002, TASK-003
  STORY-002: {title} [{N} pts]
    TASK-004, TASK-005

Sprint 2:
  STORY-003: {title} [{N} pts]
    TASK-006, TASK-007, TASK-008
  STORY-004: {title} [{N} pts]
    TASK-009, TASK-010, TASK-011

Sprint 3:
  STORY-005: {title} [{N} pts]
    TASK-012, TASK-013
```

---

## Traceability Matrix (QA-1)

| Story | FRs | Tasks | Test Cases (TC-NNN) | Risks (R-NNN) | Sprint |
|---|---|---|---|---|---|
| STORY-001 | FR-001, FR-002 | TASK-001 to 003 | TC-001, TC-002 | R-001 | 1 |
| STORY-002 | FR-003 | TASK-004, 005 | TC-003 | — | 1 |
| STORY-003 | FR-004, FR-005 | TASK-006 to 008 | TC-004, TC-005 | R-002 | 2 |

TC-NNN IDs come from qa-testcases.md (mvp+) — every FR must map to at
least one TC-NNN before /release. R-NNN IDs come from analyze.summary.md
§2 Risk Register — link only risks relevant to that story.

---

## Approvals
| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
