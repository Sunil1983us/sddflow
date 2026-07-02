# Context: habit-log
# Project: Habit Tracker Web

## What This Does
A single-page web app where a user defines daily habits, checks them off each
day, and watches streaks grow. Fully client-side: data lives in the browser
(localStorage) — no account, no backend, instant start.

## Actors
- Person building habits (the only human user)
- Browser notification scheduler (optional daily reminder)

## Key Flows
1. Create a habit (name, schedule: daily/weekdays, reminder time optional)
2. Daily check-in from the today view; streak updates immediately
3. Review streak history per habit (current streak, best streak, completion %)

## Integrations
None at pilot. Browser Notification API for reminders (permission-gated).

## Business Rules
- A habit can be checked at most once per calendar day (local timezone)
- Missing a scheduled day resets the current streak (best streak retained)
- Archived habits keep history but leave the today view

## Tech Stack
React 18 + TypeScript + Vite, Zustand for state, localStorage persistence,
Vitest + React Testing Library, ESLint + Prettier, GitHub Actions CI.

## Non-Functional Requirements
- First load < 2s on 3G; interaction under 100ms
- Works offline after first load
- All data stays on the device — no analytics, no network calls

## Out of Scope
Accounts, sync between devices, social features, mobile apps.

## Open Questions
- Should the week start Monday or Sunday for weekday schedules? (decide at clarify)
