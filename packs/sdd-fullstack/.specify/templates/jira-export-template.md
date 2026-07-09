# Jira Export
# Feature: {Feature Name}
> Input: stories.md + tasks.md
> Mode: {Full hierarchy (Epic → Story → Task) | Tasks only (Epic + Stories already in Jira)}

---

## Progressive Jira Creation

SDD creates Jira artifacts at the right stage — not all at once:

| Stage | What's Created | Command |
|---|---|---|
| After `/specify-brd` approval | Epic | `/jira-push --level epic` |
| After `/specify-uc` approval | Story drafts (no FR links yet) | `/jira-push --level story` |
| After `/specify-srd` approval | Stories refined (FR links + MoSCoW) | `/jira-push --level story` |
| After `/task` approval | Tasks linked to existing Stories | `/jira-push --level task` |
| After `/change` approval | CHG-NNN tasks under existing Stories | `/jira-push --level chg --cr CR-NNN` |

**Jira keys tracking:** `docs/jira/{Feature Name}/keys.yml` — updated by `/jira-push` after every push (scoped per feature, same as `.specify/features/{feature}/`).
**Field mapping:** `.specify/jira-config.yml` — copy from `.specify/templates/jira-config-template.yml`.

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

## Jira Import CSV — Full Hierarchy

> Use this when no Jira issues have been created yet (first-time export).

```csv
Issue Type,Summary,Parent,Sprint,Story Points,Priority,Labels,Acceptance Criteria,FR Reference,UC Reference
Epic,{Feature Name},,,, High,sdd-epic,All Must Have stories accepted by Product Owner,,
Story,{STORY-{NNN} title},{Feature Name},Sprint 1,3,High,sdd-story,"{criterion 1}; {criterion 2}",FR-{NNN}{,} FR-{NNN},UC-{NNN}
Task,{TASK-{NNN} title},STORY-{NNN} title,Sprint 1,,Medium,sdd-task,"{criterion}",FR-{NNN},
Task,{TASK-{NNN} title},STORY-{NNN} title,Sprint 1,,Medium,sdd-task,"{criterion}",FR-{NNN},
Story,{STORY-{NNN} title},{Feature Name},Sprint 1,5,High,sdd-story,"{criterion}",FR-{NNN},UC-{NNN}
Task,{TASK-{NNN} title},STORY-{NNN} title,Sprint 1,,Medium,sdd-task,"{criterion}",FR-{NNN},
Story,{STORY-{NNN} title},{Feature Name},Sprint 2,3,Medium,sdd-story,"{criterion}",FR-{NNN},UC-{NNN}
Task,{TASK-{NNN} title},STORY-{NNN} title,Sprint 2,,Medium,sdd-task,"{criterion}",FR-{NNN},
```

---

## Jira Import CSV — Tasks Only

> Use this when Epic and Stories already exist in Jira (pushed after BRD/SRD).
> Replace STORY-JIRA-KEY with the Jira issue key from `docs/jira/{Feature Name}/keys.yml`.

```csv
Issue Type,Summary,Parent,Sprint,Story Points,Priority,Labels,Acceptance Criteria,FR Reference
Task,{TASK-{NNN} title},{STORY-JIRA-KEY},Sprint 1,,Medium,sdd-task,"{criterion}",FR-{NNN}
Task,{TASK-{NNN} title},{STORY-JIRA-KEY},Sprint 1,,Medium,sdd-task,"{criterion}",FR-{NNN}
Task,{TASK-{NNN} title},{STORY-JIRA-KEY},Sprint 2,,Medium,sdd-task,"{criterion}",FR-{NNN}
```

---

## Manual Import Instructions

> Use only if `/jira-push` is not configured. Prefer `/jira-push` for automatic field mapping.

1. Jira → Projects → Import Issues → CSV
2. Upload `docs/jira/{Feature Name}/jira-import.csv`
3. Map columns to your Jira fields:
   - Issue Type → Issue Type
   - Summary → Summary
   - Parent → Parent Issue (or Epic Link for classic Jira)
   - Sprint → Sprint
   - Story Points → Story Points
   - Priority → Priority
   - Labels → Labels
   - Acceptance Criteria → your AC custom field
   - FR Reference → your FR traceability custom field (optional)
   - UC Reference → your UC traceability custom field (optional)
4. Review mapping → Import

---

## Git → Jira Link

```bash
# Branch naming — Jira auto-links by issue key
git checkout -b feature/STORY-{NNN}-{story-slug}

# Commit naming — Jira auto-links TASK-NNN
git commit -m "feat(TASK-{NNN}): {description}"
git commit -m "test(TASK-{NNN}): {test description}"
```

---

*Generated from: stories.md + tasks.md*
*Keys file: docs/jira/{Feature Name}/keys.yml*
*Config: .specify/jira-config.yml*
