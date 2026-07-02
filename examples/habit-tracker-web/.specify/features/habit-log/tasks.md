# Task Breakdown
## Feature: Habit Log | Run by: /task

---

## TASK-001 — Storage Port + Versioned Schema

**Story:** STORY-001 · **Satisfies:** FR-002 · **Estimate:** ~80 lines
`storage/localStore.ts`: load/save `habitlog.v1`, migration hook, quota error surfaced (EP-1-2).
**Acceptance:** [ ] round-trip test [ ] private-mode failure raises typed error (TC-S-005)

## TASK-002 — Domain: Schedule + Streak Engine

**Story:** STORY-002 · **Satisfies:** FR-003, FR-004, FR-005 · **Estimate:** ~150 lines
Pure functions in `domain/`: isScheduled(date), toggleCompletion, computeStreaks. Table-driven tests incl. DST + midnight cases (R-001, Q2/Q3 rules).
**Acceptance:** [ ] one completion per calendar day [ ] reset on missed scheduled day [ ] best streak retained

## TASK-003 — Habit Store + Create Flow

**Story:** STORY-001 · **Satisfies:** FR-001 · **Estimate:** ~120 lines
Zustand store wiring domain+storage; NewHabit form with validation (EP-1-1).
**Acceptance:** [ ] TC-S-001 passes [ ] TC-S-004 passes

## TASK-004 — Today View + Check-in Interaction

**Story:** STORY-002 · **Satisfies:** FR-003, FR-004 · **Estimate:** ~140 lines
Today list, check circle with optimistic update inside the 100ms budget (design §3.5).
**Acceptance:** [ ] TC-S-002 [ ] TC-S-003 [ ] render budget respected (React Profiler check)

## TASK-005 — Habit Detail + Streak Stats

**Story:** STORY-003 · **Satisfies:** FR-004 · **Estimate:** ~110 lines
Detail view: current/best streak, 30-day completion %, zero-state.
**Acceptance:** [ ] TC-S-006 [ ] TC-S-007

## TASK-006 — Archive / Unarchive

**Story:** STORY-004 · **Satisfies:** FR-006 · **Estimate:** ~70 lines
Archive flag, Archived section, unarchive restarts current streak at 0.
**Acceptance:** [ ] TC-S-008

## TASK-007 — Offline (Service Worker)

**Story:** STORY-004 · **Satisfies:** FR-008 · **Estimate:** ~90 lines
Vite PWA plugin, cache-first shell, no network dependency assertion (NFR-002).
**Acceptance:** [ ] TC-S-010 [ ] e2e asserts zero outbound requests with user data

## TASK-008 — Reminders

**Story:** STORY-005 · **Satisfies:** FR-007 · **Estimate:** ~100 lines
`reminders/scheduler.ts`; permission requested on reminder set only (TH-004).
**Acceptance:** [ ] TC-S-009 [ ] no prompt on first load
