# Jira Export
# Feature: {Feature Name}
> Input: stories.md + tasks.md

---

## Hierarchy

```
Epic: {Feature Name}
  │
  ├── Story: STORY-{NNN} — {title}
  │     Task: TASK-{NNN} — {title}
  │     Task: TASK-{NNN} — {title}
  │
  ├── Story: STORY-{NNN} — {title}
  │     Task: TASK-{NNN} — {title}
  │     Task: TASK-{NNN} — {title}
  │
  └── Story: STORY-{NNN} — {title}
        Task: TASK-{NNN} — {title}
        Task: TASK-{NNN} — {title}
```

---

## Jira Import CSV

```csv
Issue Type,Summary,Epic Link,Parent,Sprint,Story Points,Priority,Labels,Acceptance Criteria
Epic,{Feature Name},,,,, High,{project},All stories delivered and tested
Story,{STORY-{NNN} title},{Feature},{Feature},Sprint 1,3,High,{label},"{criterion 1}; {criterion 2}"
Task,{TASK-{NNN} title},{Feature},STORY-{NNN},Sprint 1,1,High,{label},"{criterion}"
Task,{TASK-{NNN} title},{Feature},STORY-{NNN},Sprint 1,1,High,{label},"{criterion}"
Story,{STORY-{NNN} title},{Feature},{Feature},Sprint 1,5,High,{label},"{criterion}"
Task,{TASK-{NNN} title},{Feature},STORY-{NNN},Sprint 1,1,High,{label},"{criterion}"
Task,{TASK-{NNN} title},{Feature},STORY-{NNN},Sprint 1,2,High,{label},"{criterion}"
Story,{STORY-{NNN} title},{Feature},{Feature},Sprint 2,3,High,{label},"{criterion}"
Task,{TASK-{NNN} title},{Feature},STORY-{NNN},Sprint 2,1,High,{label},"{criterion}"
Task,{TASK-{NNN} title},{Feature},STORY-{NNN},Sprint 2,1,High,{label},"{criterion}"
```

---

## Import Instructions

1. Jira → Projects → Import Issues → CSV
2. Upload jira-import.csv
3. Map columns:
   - Issue Type → Issue Type
   - Summary → Summary
   - Epic Link → Epic Link
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
