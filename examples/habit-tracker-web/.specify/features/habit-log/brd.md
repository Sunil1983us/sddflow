# Business Requirements Document
## Feature: Habit Log
## Project: Habit Tracker Web | Scope: Pilot | Version: 1.0
> Version: 1.0 | Status: Approved | Date: 2026-06-28 | Author: Maya (BA)

---

## 1. Business Objectives

| ID | Objective | Success Metric | Target |
|---|---|---|---|
| BO-001 | Validate that a zero-signup, privacy-first habit tracker attracts organic users | Weekly active users (self-hosted counter, opt-in) | 500 WAU within 60 days |
| BO-002 | Prove daily habit check-in drives return visits | 7-day return rate | ≥ 40% |

## 2. Business Requirements

| ID | Requirement | Priority | Trace |
|---|---|---|---|
| BR-001 | Users MUST be able to create, check off, and archive daily habits | MUST | BO-001, BO-002 |
| BR-002 | Streaks MUST update instantly on check-in and reset when a scheduled day is missed | MUST | BO-002 |
| BR-003 | All data MUST stay on the user's device — no account, no server storage | MUST | BO-001 (privacy positioning) |
| BR-004 | The app SHOULD work offline after first load | SHOULD | BO-001 |
| BR-005 | Users COULD enable a daily browser reminder per habit | COULD | BO-002 |

## 3. Scope

**In scope:** habit CRUD, daily check-in, streak calculation, archive, offline use, optional reminders.
**Out of scope:** accounts, cross-device sync, social features, native apps.

## Approvals

| Role | Status | Date |
|---|---|---|
| Product Owner | Approved | 2026-06-28 |
