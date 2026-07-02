# Clarification Log
## Feature: Habit Log | Run by: /clarify

| ID | Question | Answer | Status |
|---|---|---|---|
| Q1 | Week starts Monday or Sunday for weekday schedules? | Monday (ISO-8601), fixed — not configurable at pilot | RESOLVED |
| Q2 | Streak reset evaluated only at app load? | At load AND via a scheduled midnight recompute while the tab is open | RESOLVED |
| Q3 | Does undoing a check-in after midnight remove yesterday's completion? | No — toggling affects the calendar day of the tap only (EP-2-1) | RESOLVED |

All items RESOLVED — /plan-design may proceed.
