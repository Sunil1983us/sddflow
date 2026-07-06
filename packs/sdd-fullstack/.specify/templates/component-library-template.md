# Component Library
# Service: {Service Name}
> Version: 1.0 | Date: {date}
>
> **Living document** — catalogs shared/reusable frontend components used
> across multiple features, not one feature's own page-specific
> components. Lives at `.specify/service/component-library.md`. Every
> feature that introduces a new reusable component, or changes an
> existing shared component's props/behavior, extends this file (see the
> living-doc-update shared block in `specify-doc.prompt.md`) — it is
> never regenerated from a blank template. Page-specific/container
> components stay in each feature's own `component-spec.md`.

---

## References
| Source | Sections / IDs Used |
|---|---|
| component-spec.summary.md (per feature) | {sections/IDs referenced} |

## Shared Components

### {ComponentName} (e.g. `Button`)
| Property | Value |
|---|---|
| Type | Presentational (shared) |
| Location | {library/local path, e.g. `src/components/ui/Button.tsx`} |
| Props | {list typed props} |
| Events | {list emitted events} |
| Accessibility | {axe-core notes, ARIA role, keyboard behavior} |
| Used By | {FEAT-001, FEAT-003, ...} |
| Tests | {list test scenarios} |

---

## Version History
| Version | Date | Feature | Change |
|---|---|---|---|
| 1.0 | {date} | {feature} | Initial component(s) added |

## Approvals
| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
