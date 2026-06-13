# Improvement Backlog — Phase 3 (Deferred)
# Items identified during the framework review that are valuable but
# out of scope for the current fix pass. Pick these up as needed.

---

## QA-2 — Device/OS Coverage Matrix + Farm Testing
qa-testcases-template.md does not yet capture a device/OS coverage
matrix (min/target/max OS versions, screen sizes, device tiers) or a
strategy for running E2E suites against a device farm (Firebase Test
Lab / BrowserStack App Automate). Add a `device-matrix-template.md` for
mvp+/full.

## OPS-8 — Performance Budgets as SLOs
resilience.md (Mobile Resilience) covers offline/retry behaviour but not
formal performance budgets — cold start time, sustained frame rate
(jank), and app binary size — as tracked SLOs with alerting thresholds.
Add a "Performance Budgets" section once baseline measurements exist.

## AI-9 — Accessibility Audit Template
No template currently captures an accessibility audit (screen reader
labels/VoiceOver/TalkBack, dynamic type / font scaling, color contrast
ratios, touch target sizes). Add an `accessibility-template.md` for
mvp+/full, referenced from screen-spec.md.

## FW-9 — Offline-First Sync Conflict Resolution Depth
resilience-template.md (Mobile Resilience) covers retry/backoff and
degraded-connectivity UX at a high level. A deeper conflict-resolution
strategy (last-write-wins vs merge vs user-prompted resolution, per
entity in data-model.md) is deferred — revisit once sync volume/patterns
are known.

## SEC-8 — App Store Compliance Checklist
security-design.md §4 traces regulatory requirements generically. A
dedicated app-store compliance checklist (privacy nutrition labels /
Data Safety section, permission-usage justification strings, export
compliance) is deferred to a future `compliance-template.md`.

## OBS-1 — Localization / i18n Strategy
No template captures a localization strategy (supported locales,
string-extraction workflow, RTL layout testing, date/number/currency
formatting per locale). Add an `i18n-template.md` if the app ships in
multiple markets.

---
*This file is created once per pack. Add pack-specific deferred items
below this line as they are identified.*
