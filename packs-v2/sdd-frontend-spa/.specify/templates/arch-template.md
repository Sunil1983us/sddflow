# Architecture Design
# Feature: {Feature Name}
> Version: 1.0 | Date: {date} | Input: srd.summary.md

---

## 1. Architecture Overview
{One paragraph — component pattern chosen, state management approach, why.}

## 2. Component Diagram
```
[Route / Page]
      │
      ▼
[{Feature}Page]                 ← pages/ (route entry)
      │
      ▼
[{Feature}Container]            ← containers/ (state + side-effects)
      │
      ├──▶ [use{Feature}Store]   ← store/ (global state slice)
      │
      ├──▶ [use{Feature}Query]   ← hooks/ (data fetching)
      │         │
      │         ▼
      │    [{Feature}Service]    ← services/ (API client calls)
      │         │
      │         ▼
      │    [Mock{Feature}Service] ← mocks/ (MSW handler — dev/test)
      │    [Real{Feature}Service] ← services/ (real API — prod)
      │
      ▼
[{ComponentA}]                   ← components/ (presentational)
[{ComponentB}]                   ← components/ (presentational)
      └──▶ [{SharedComponent}]   ← components/shared/ or design system
```

## 3. Layer Responsibilities
| Layer | Folder | Responsibility |
|---|---|---|
| Page | pages/ | Route entry — composes containers, no logic |
| Container | containers/ | Owns state + side-effects, delegates to hooks/services |
| Hooks/Composables | hooks/ | Data fetching, derived state, reusable side-effect logic |
| Store | store/ | Global state slice (Redux/Zustand/Pinia/Context) |
| Service | services/ | API client calls + request/response transformation |
| Mock Service | mocks/ | MSW/mock handler — dev + test |
| Presentational Components | components/ | Render props/state only — zero business logic |
| Shared Components | components/shared/ | Design-system / cross-feature reusable components |
| Routing | routes/ | Route definitions, guards, lazy-loaded chunks |

## 4. Key Design Decisions
| ID | Decision | Rationale | ADR (mvp+) |
|---|---|---|---|
| DEC-001 | {decision} | {why} | ADR-001 (if mvp+, else "—") |
| DEC-002 | {decision} | {why} | ADR-002 (if mvp+, else "—") |

Pilot scope: use DEC-NNN only — no ADR column value (ADRs are mvp+ only,
generated at /plan-adr). MVP+: /plan-adr converts HIGH-impact DEC-NNN
rows into full ADR-NNN records — fill the ADR column once generated.

## 4a. NFR → Architecture Decision Mapping (AR-3)
| NFR-NNN | Requirement | Design Constraint | Decision (DEC-NNN) |
|---|---|---|---|
| NFR-{NNN} | {requirement, from analyze.md §5} | {what it forces} | DEC-{NNN} |

Every NFR flagged in analyze.md §5 NFR Impact Analysis must appear here
with the decision that satisfies it.

## 5. Flow — Happy Path
```
{Step 1: user navigates to route}
→ Page mounts → Container fires data-fetch hook
→ Loading state rendered
→ Service calls API (or mock service in dev/test)
→ Store updated with response
→ Container re-renders Presentational components with data
→ User interaction → Container dispatches action → Store updated
→ UI reflects new state
```

## 6. State & Component Architecture
| Slice/Component | Purpose |
|---|---|
| {storeSlice} | {what global state it holds} |
| {ComponentName} | {what it renders / owns} |

## 7. Cross-Cutting Concerns
| Concern | Approach |
|---|---|
| Auth | {approach — token storage, route guards} |
| Logging | Structured console + error tracking (Sentry/RUM) |
| Error Handling | Error boundaries + global API error handler |
| Offline/Resilience | {approach if applicable} |

---
*Generated from: srd.summary.md*
