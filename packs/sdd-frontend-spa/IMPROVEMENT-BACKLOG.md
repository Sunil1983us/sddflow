# Improvement Backlog — Phase 3 (Deferred)
# Items identified during the framework review that are valuable but
# out of scope for the current fix pass. Pick these up as needed.

---

## OBS-1 — Visual Regression Testing
qa-testcases-template.md and component-spec.md cover functional
component tests but not visual regression (pixel/DOM-diff) testing.
Not yet covered: Chromatic/Percy (or Playwright snapshot) integration,
baseline approval workflow, and which components/states are
snapshot-tested. Add a `visual-regression-template.md` if this pack is
used for design-system-heavy projects.

## OPS-8 — Performance Budgets / Core Web Vitals SLOs
resilience.md (Frontend Resilience) and the constitution's "Performant"
core principle reference Core Web Vitals at a high level. Not yet
covered: formal performance budgets (LCP/CLS/INP/TTI thresholds per
route), Lighthouse CI wired into quality-gate.yml, and alerting when a
PR regresses the budget. Add a "Performance Budgets" section once
baseline measurements exist.

## SEC-8 — i18n / l10n Strategy
No template captures a localization strategy (supported locales,
string-extraction workflow, RTL layout testing, date/number/currency
formatting per locale, translation review gate). Add an
`i18n-template.md` for mvp+/full if the app ships in multiple markets.

## FW-9 — Design-Token / Theming Governance
component-spec-template.md references the Component Library/Design
System but does not capture design-token governance — token source of
truth (Figma/Style Dictionary), theming (light/dark, multi-brand), and
the process for proposing new tokens vs. reusing existing ones. Add a
`design-tokens-template.md` if the project owns its own design system
rather than consuming one.

## AI-9 — Feature-Flag Strategy
No template captures a feature-flag strategy — flag provider
(LaunchDarkly/Unleash/home-grown), naming convention, default states per
environment, and the cleanup process for stale flags (referenced from
release-template.md §3 "Enable feature flag / staged rollout"). Add a
`feature-flag-template.md` for mvp+/full once a provider is chosen.

## QA-2 — Mock Service Worker / Test-Data Strategy
data-model-template.md (Frontend State & Storage Model) and
qa-testcases-template.md define test cases but not a strategy for
mock-data management across environments — MSW handler organization,
fixture/factory conventions, and how mock data stays in sync with the
API contract in `design.md` §3 when the backend changes it. Consider a
`test-data-strategy.md` for mvp+/full.

## AI-10 — Bundle-Size Budget + Code-Splitting Audit
No template tracks JS bundle-size budgets per route/chunk or a
code-splitting audit (lazy-loaded routes/components per the
constitution's "Performant" principle). Consider adding a bundle
analyzer step to quality-gate.yml and a budget table once baseline
bundle sizes exist.

---
*This file is created once per pack. Add pack-specific deferred items
below this line as they are identified.*
