# Feature and Story Breakdown
# Feature: {Feature Name}
> Version: 1.0 | Status: Draft | Date: {date} | Author: {author}

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

### STORY-{NNN}: {Story Title}
**As** {actor}
**I want** {capability}
**So that** {business value}

**Linked FRs:** FR-{NNN}, FR-{NNN}
**Story Points:** {1|2|3|5|8} | **Sprint:** 1

**Acceptance Criteria:**
- [ ] {Given/When/Then criterion 1}
- [ ] {Given/When/Then criterion 2}

**Tasks:** TASK-{NNN}, TASK-{NNN}, TASK-{NNN}

---

### STORY-{NNN}: {Story Title}
**As** {actor}
**I want** {capability}
**So that** {business value}

**Linked FRs:** FR-{NNN}
**Story Points:** {N} | **Sprint:** 1

**Acceptance Criteria:**
- [ ] {criterion}

**Tasks:** TASK-{NNN}, TASK-{NNN}

---

## Should Have Stories

### STORY-{NNN}: {Story Title}
**As** {actor}
**I want** {capability}
**So that** {business value}

**Linked FRs:** FR-{NNN}
**Story Points:** {N} | **Sprint:** 2

**Acceptance Criteria:**
- [ ] {criterion}

**Tasks:** TASK-{NNN}, TASK-{NNN}, TASK-{NNN}

---

## Could Have Stories

_(No Could Have stories defined yet — add as scope expands)_

---

## Story Map

```
FEATURE-001: {Feature Name}

Sprint 1:
  STORY-{NNN}: {title} [{N} pts]
    TASK-{NNN}, TASK-{NNN}, TASK-{NNN}
  STORY-{NNN}: {title} [{N} pts]
    TASK-{NNN}, TASK-{NNN}

Sprint 2:
  STORY-{NNN}: {title} [{N} pts]
    TASK-{NNN}, TASK-{NNN}, TASK-{NNN}
  STORY-{NNN}: {title} [{N} pts]
    TASK-{NNN}, TASK-{NNN}, TASK-{NNN}

Sprint 3:
  STORY-{NNN}: {title} [{N} pts]
    TASK-{NNN}, TASK-{NNN}
```

---

## Sprint Velocity Notes

> Agent assigns stories to sprints based on:
> - Team velocity: {N} story points per sprint — set in manifest.yml or ask user
> - Dependencies: stories with upstream TASK dependencies must be in a later sprint
> - Risk: HIGH complexity stories should not share a sprint with other HIGH stories
> - Must Have stories always assigned before Should Have / Could Have

If team velocity is unknown: use 20 story points per sprint as a default estimate and note "VERIFY VELOCITY WITH TEAM" in stories.md.

### BUFFER — Sprint {last sprint N}
**Story Points:** {ceil(total SP × 0.10)} — 10% buffer for rework from review cycles
**Purpose:** Absorbs review feedback, unexpected complexity, and sprint 1–N spillover.
**Rule:** Reduce buffer only if team has ≥ 3 sprints of proven velocity data showing < 5% spillover.

---

## Cross-Sprint Dependencies

> Stories that cannot start until another story in a prior sprint is complete. Generated from TASK `Dependencies:` fields.

| Blocked Story | Depends On Story | Reason | Earliest Sprint Start |
|---|---|---|---|
| STORY-{N} | STORY-{M} (Sprint {X}) | {TASK-NNN depends on TASK-MMM output} | Sprint {X+1} |

**Risk:** If a blocking story slips, all dependent stories shift by at least 1 sprint. Flag to Scrum Master immediately on any blocker slip.

---

## Traceability Matrix (QA-1)

| Story | UC Traces | FRs | Tasks | Test Cases (TC-NNN) | Risks (R-NNN) | Sprint |
|---|---|---|---|---|---|---|
| STORY-{NNN} | UC-{NNN} | FR-{NNN}, FR-{NNN} | TASK-{NNN} to {NNN} | TC-{NNN}, TC-{NNN} | R-{NNN} | 1 |
| STORY-{NNN} | UC-{NNN} | FR-{NNN} | TASK-{NNN}, {NNN} | TC-{NNN} | — | 1 |
| STORY-{NNN} | UC-{NNN} | FR-{NNN}, FR-{NNN} | TASK-{NNN} to {NNN} | TC-{NNN}, TC-{NNN} | R-{NNN} | 2 |

TC-NNN IDs come from qa-testcases.md (mvp+) — every FR must map to at
least one TC-NNN before /release. R-NNN IDs come from analyze.summary.md
§2 Risk Register. UC-NNN IDs from use-cases.md — every Story must trace
to at least one UC-NNN so the business flow is fully covered.

---

## Approvals
| Role | Status | Date |
|---|---|---|
| Product Owner (accountable — stories + scope approved) | Pending | |
| Tech Lead (responsible — task accuracy + dependency review) | Pending | |
| QA Lead (consulted — test case mapping confirmed, mvp+) | Pending | |

## Version History

| Version | Date | Changed By | Summary of Changes | CHG-NNN |
|---|---|---|---|---|
| 1.0 | {date} | {author} | Initial draft | — |
