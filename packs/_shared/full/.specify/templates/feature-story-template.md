# Feature and Story Breakdown
# Feature: {Feature Name}
> Version: 1.0 | Date: {date}

---

## References
| Source | Sections / IDs Used |
|---|---|
| srd.summary.md | {sections/IDs referenced} |
| design.summary.md | {sections/IDs referenced} |

## Feature Definition

### FEATURE-001: {Feature Name}
**Business Capability:** {what business capability this delivers}
**Scope:** {pilot | mvp | full}
**Priority:** Must Have
**Linked BRD Objectives:** BO-{NNN}

---

## Stories

> Stories are grouped by MoSCoW priority. The Scrum Master assigns each story to a priority bucket; all Must Have stories must be complete before Should Have stories begin.

## Must Have Stories

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

## Should Have Stories

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

## Could Have Stories

_(No Could Have stories defined yet — add as scope expands)_

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

## Sprint Velocity Notes

> Agent assigns stories to sprints based on:
> - Team velocity: {N} story points per sprint — set in manifest.yml or ask user
> - Dependencies: stories with upstream TASK dependencies must be in a later sprint
> - Risk: HIGH complexity stories should not share a sprint with other HIGH stories
> - Must Have stories always assigned before Should Have / Could Have

If team velocity is unknown: use 20 story points per sprint as a default estimate and note "VERIFY VELOCITY WITH TEAM" in stories.md.

---

## Traceability Matrix (QA-1)

| Story | UC Traces | FRs | Tasks | Test Cases (TC-NNN) | Risks (R-NNN) | Sprint |
|---|---|---|---|---|---|---|
| STORY-001 | UC-001 | FR-001, FR-002 | TASK-001 to 003 | TC-001, TC-002 | R-001 | 1 |
| STORY-002 | UC-001 | FR-003 | TASK-004, 005 | TC-003 | — | 1 |
| STORY-003 | UC-002 | FR-004, FR-005 | TASK-006 to 008 | TC-004, TC-005 | R-002 | 2 |

TC-NNN IDs come from qa-testcases.md (mvp+) — every FR must map to at
least one TC-NNN before /release. R-NNN IDs come from analyze.summary.md
§2 Risk Register. UC-NNN IDs from use-cases.md — every Story must trace
to at least one UC-NNN so the business flow is fully covered.

---

## Approvals
| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
