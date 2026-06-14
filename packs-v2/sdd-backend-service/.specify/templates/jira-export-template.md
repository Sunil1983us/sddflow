# Jira Export
# Feature: {Feature Name}
> Input: stories.md + tasks.md

---

## Hierarchy

```
Feature: {Feature Name}
  │
  ├── Story: STORY-001 — {title}
  │     Task: TASK-001 — {title}
  │     Task: TASK-002 — {title}
  │
  ├── Story: STORY-002 — {title}
  │     Task: TASK-003 — {title}
  │     Task: TASK-004 — {title}
  │
  └── Story: STORY-003 — {title}
        Task: TASK-005 — {title}
        Task: TASK-006 — {title}
```

---

## Jira Import CSV

```csv
Issue Type,Summary,Feature Link,Parent,Sprint,Story Points,Priority,Labels,Acceptance Criteria
Feature,{Feature Name},,,,, High,{project},All stories delivered and tested
Story,{STORY-001 title},{Feature},{Feature},Sprint 1,3,High,{label},"{criterion 1}; {criterion 2}"
Task,{TASK-001 title},{Feature},STORY-001,Sprint 1,1,High,{label},"{criterion}"
Task,{TASK-002 title},{Feature},STORY-001,Sprint 1,1,High,{label},"{criterion}"
Story,{STORY-002 title},{Feature},{Feature},Sprint 1,5,High,{label},"{criterion}"
Task,{TASK-003 title},{Feature},STORY-002,Sprint 1,1,High,{label},"{criterion}"
Task,{TASK-004 title},{Feature},STORY-002,Sprint 1,2,High,{label},"{criterion}"
Story,{STORY-003 title},{Feature},{Feature},Sprint 2,3,High,{label},"{criterion}"
Task,{TASK-005 title},{Feature},STORY-003,Sprint 2,1,High,{label},"{criterion}"
Task,{TASK-006 title},{Feature},STORY-003,Sprint 2,1,High,{label},"{criterion}"
```

---

## Import Instructions

1. Jira → Projects → Import Issues → CSV
2. Upload jira-import.csv
3. Map columns:
   - Issue Type → Issue Type
   - Summary → Summary
   - Feature Link → Epic Link (substitute your project's top-level issue
     type if it isn't named "Feature")
   - Parent → Parent Issue
   - Sprint → Sprint
   - Story Points → Story Points
4. Review + Import

---

## Git → Jira Link

```bash
# Branch naming
git checkout -b feature/STORY-001-{story-slug}

# Commit naming — Jira auto-links TASK-NNN
git commit -m "feat(TASK-001): {description}"
git commit -m "test(TASK-001): {test description}"
```

---
*Generated from: stories.md + tasks.md*
