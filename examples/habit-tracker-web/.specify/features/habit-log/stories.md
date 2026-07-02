# User Stories
## Feature: Habit Log | Run by: /task

---

## Must Have

### STORY-001 — Create a Habit
**As a** habit builder **I want to** define a habit with a name and schedule **So that** it shows up on the right days
**Acceptance Criteria:** AC-001-1 valid habit persists and renders (TC-S-001); AC-001-2 empty/long name rejected inline (TC-S-004)
**Story Points:** 2 · **Satisfies:** FR-001, FR-002

### STORY-002 — Daily Check-in with Streaks
**As a** habit builder **I want to** check off today and see my streak move **So that** momentum is visible
**Acceptance Criteria:** AC-002-1 check-in <100ms with streak +1 (TC-S-002); AC-002-2 same-day toggle undoes (TC-S-003); AC-002-3 missed scheduled day resets current streak at next load/midnight
**Story Points:** 5 · **Satisfies:** FR-003, FR-004, FR-005

### STORY-003 — Streak History View
**As a** habit builder **I want to** see current/best streak and 30-day completion **So that** I can review progress
**Acceptance Criteria:** AC-003-1 detail view renders three stats (TC-S-006); AC-003-2 zero-state for empty history (TC-S-007)
**Story Points:** 3 · **Satisfies:** FR-004

## Should Have

### STORY-004 — Archive and Offline
**As a** habit builder **I want to** archive finished habits and use the app offline **So that** the app stays tidy and reliable
**Acceptance Criteria:** AC-004-1 archive hides from today, keeps history (TC-S-008); AC-004-2 offline reload fully functional (TC-S-010)
**Story Points:** 3 · **Satisfies:** FR-006, FR-008

## Could Have

### STORY-005 — Daily Reminders
**As a** habit builder **I want** an optional browser reminder **So that** I don't forget
**Acceptance Criteria:** AC-005-1 permission asked only when a reminder is set; AC-005-2 denied permission degrades silently (TC-S-009)
**Story Points:** 2 · **Satisfies:** FR-007

## Won't Have (this release)
Accounts, sync, social features (BRD §3 Out of scope).
