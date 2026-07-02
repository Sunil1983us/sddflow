# Software Requirements Document
## Feature: Habit Log
## Project: Habit Tracker Web | Version: 1.0
> Version: 1.0 | Status: Approved | Date: 2026-06-29 | Author: Rex (Requirements)

---

## 1. Functional Requirements

| ID | Requirement | Priority | Trace |
|---|---|---|---|
| FR-001 | App shall create a habit with name (1–60 chars), schedule (daily/weekdays), optional reminder time | HIGH | UC-001, BR-001 |
| FR-002 | App shall persist all habit data to localStorage under a single versioned key | HIGH | UC-001, BR-003 |
| FR-003 | App shall record at most one completion per habit per local calendar day, toggleable | HIGH | UC-002, BR-002 |
| FR-004 | App shall compute current streak, best streak, and 30-day completion % on every check-in | HIGH | UC-002, UC-003, BR-002 |
| FR-005 | App shall reset the current streak when a scheduled day passes without completion (evaluated at load and at midnight tick) | HIGH | UC-002, BR-002 |
| FR-006 | App shall archive/unarchive habits, retaining history; unarchive restarts current streak at 0 | MEDIUM | UC-004, BR-001 |
| FR-007 | App shall schedule a browser notification per habit at its reminder time when permission is granted | LOW | UC-005, BR-005 |
| FR-008 | App shall function fully offline after first load (service worker, no network dependencies) | MEDIUM | BR-004 |

## 2. Non-Functional Requirements

| ID | Category | Target |
|---|---|---|
| NFR-001 | Performance | First contentful paint < 2s on simulated 3G; check-in interaction < 100ms |
| NFR-002 | Privacy | Zero network calls carrying user data; localStorage only (verified by e2e network assertion) |
| NFR-003 | Reliability | State schema versioned; migration function on version bump — no data loss on upgrade |

## Approvals

| Role | Status | Date |
|---|---|---|
| Business Analyst | Approved | 2026-06-29 |
