# Use Case Specification — Habit Log
# Feature: habit-log
> Version: 1.0 | Status: Approved | Date: 2026-06-28 | Author: Maya (BA)

---

## 1. Actors

| ID | Actor | Type | Description |
|---|---|---|---|
| ACT-001 | Habit Builder | Human (browser) | The person creating and checking off habits |
| ACT-002 | Reminder Scheduler | System (browser Notification API) | Fires the optional daily reminder per habit |

## 2. Use Cases

### UC-001 — Create Habit

**Actor:** ACT-001 · **Trace:** BR-001

**Main Path (MP):**
1. User opens "New habit", enters name (1–60 chars), picks schedule (daily / weekdays), optional reminder time
2. App validates and saves the habit to localStorage
3. Habit appears in the today view when scheduled

**Alternate Paths:**
- AP-1-1: No reminder time → habit created without notification

**Exception Paths:**
- EP-1-1: Empty or >60-char name → inline error, nothing saved
- EP-1-2: localStorage full/unavailable → visible error banner with retry

**Independent Test:** Create "Read 20 min" daily; verify it renders in today view and survives a page reload.

### UC-002 — Daily Check-in

**Actor:** ACT-001 · **Trace:** BR-001, BR-002

**Main Path (MP):**
1. User taps the habit's check circle in the today view
2. App records completion for today's local date and increments the current streak
3. UI updates in under 100ms with streak count and celebratory state

**Alternate Paths:**
- AP-2-1: Tap again the same day → check-in is undone (toggle), streak recalculated

**Exception Paths:**
- EP-2-1: A second check-in attempt after undo/redo across midnight → app uses the calendar day at tap time; only one completion per day is stored

**Independent Test:** Check a habit, reload, verify checked state and streak = previous + 1.

### UC-003 — View Streaks

**Actor:** ACT-001 · **Trace:** BR-002

**Main Path (MP):**
1. User opens a habit's detail view
2. App shows current streak, best streak, and completion % over the last 30 days

**Exception Paths:**
- EP-3-1: Habit with no history → zero-state copy, no chart

### UC-004 — Archive Habit

**Actor:** ACT-001 · **Trace:** BR-001

**Main Path (MP):**
1. User archives a habit from its detail view
2. Habit leaves the today view; history is retained and visible under "Archived"

**Alternate Paths:**
- AP-4-1: Unarchive → habit returns to today view; streak restarts from 0 (best streak kept)

### UC-005 — Daily Reminder

**Actor:** ACT-002 · **Trace:** BR-005

**Main Path (MP):**
1. At the habit's reminder time, the scheduler fires a browser notification
2. Clicking it opens the today view

**Exception Paths:**
- EP-5-1: Notification permission denied → reminders silently disabled; settings shows how to re-enable

## Approvals

| Role | Status | Date |
|---|---|---|
| Business Analyst | Approved | 2026-06-28 |
| Product Owner | Approved | 2026-06-28 |
