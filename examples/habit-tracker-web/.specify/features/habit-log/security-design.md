# Security Design — Habit Log
# Feature: habit-log
> Version: 1.0 | Status: Approved | Date: 2026-06-29 | Author: Ava (Architect)
> Scope: pilot — §1 Threat Assessment only

---

## 1. Threat Assessment

| ID | Threat | Vector | Mitigation | Trace |
|---|---|---|---|---|
| TH-001 | Stored XSS via habit name | Habit name rendered into DOM | React's default escaping only — never dangerouslySetInnerHTML; 60-char limit | FR-001, EP-1-1 |
| TH-002 | Data exfiltration by third-party script | Any external script could read localStorage | Zero third-party scripts; CSP: default-src 'self'; no analytics | NFR-002, BR-003 |
| TH-003 | Data loss on schema change | Breaking localStorage shape between releases | Versioned state key + migration function (NFR-003); export-to-JSON escape hatch | NFR-003 |
| TH-004 | Notification permission abuse perception | Prompting on first load feels spammy | Permission requested only when the user sets a reminder time | UC-005, EP-5-1 |

## Approvals

| Role | Status | Date |
|---|---|---|
| Tech Lead | Approved | 2026-06-29 |
