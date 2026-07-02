# Smoke Tests — Habit Log (pilot)
> Version: 1.0 | Status: Approved | Date: 2026-06-30 | Author: Kai (EM)
> Pilot-scope smoke list (≤10) — full qa-testcases.md arrives at mvp scope.

| ID | Scenario (Given / When / Then) | Source |
|---|---|---|
| TC-S-001 | Given a fresh app, when I create habit "Read" (daily), then it appears in today view and survives reload | UC-001 MP |
| TC-S-002 | Given "Read" unchecked today, when I tap its circle, then it shows checked and streak +1 within 100ms | UC-002 MP |
| TC-S-003 | Given "Read" checked today, when I tap again, then completion is removed and streak recalculates | AP-2-1 |
| TC-S-004 | Given an empty habit name, when I save, then an inline error shows and nothing is stored | EP-1-1 |
| TC-S-005 | Given localStorage is unavailable (private mode), when I save, then an error banner with retry appears | EP-1-2 |
| TC-S-006 | Given a habit with 3-day history, when I open detail, then current streak, best streak, 30-day % render | UC-003 MP |
| TC-S-007 | Given a habit with no history, when I open detail, then the zero-state copy renders (no chart) | EP-3-1 |
| TC-S-008 | Given an active habit, when I archive it, then it leaves today view and shows under Archived with history | UC-004 MP |
| TC-S-009 | Given notification permission denied, when reminder time passes, then no error surfaces and settings explains re-enabling | EP-5-1 |
| TC-S-010 | Given the app was loaded once, when I go offline and reload, then the today view works fully | FR-008 |
