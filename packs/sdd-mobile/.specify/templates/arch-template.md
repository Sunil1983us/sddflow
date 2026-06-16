# Architecture Design
# Feature: {Feature Name}
> Version: 1.0 | Date: {date}

---

## References
| Source | Sections / IDs Used |
|---|---|
| srd.summary.md | {sections/IDs referenced} |

## 1. Architecture Overview
{One paragraph — pattern chosen, key decisions, why.}

## 2. Component Diagram
```
[Caller / Actor]
      │
      ▼
[{Feature}Controller]          ← adapter/in/
      │
      ▼
[{Feature}UseCase]             ← port/in/ (interface)
      │
      ▼
[{Feature}Service]             ← service/
      │
      ├──▶ [{Integration}Port]  ← port/out/ (interface)
      │         │
      │         ▼
      │    [Mock{Integration}Adapter]  ← mock/ @Profile(mock)
      │    [Real{Integration}Adapter]  ← adapter/out/ @Profile(prod)
      │
      └──▶ [{Repository}Port]   ← port/out/
                │
                ▼
           [Jpa{Entity}Adapter] ← adapter/out/
```

## 3. Layer Responsibilities
| Layer | Package | Responsibility |
|---|---|---|
| Controller | controller/ | Receive request, delegate, return response |
| Inbound Port | port/in/ | Use case interface |
| Service | service/ | Business logic |
| Outbound Port | port/out/ | Integration interface |
| Mock Adapter | mock/ | @Profile("mock") test implementation |
| Real Adapter | adapter/out/ | @Profile("prod") real implementation |
| Domain | domain/ | Entities, value objects, enums |
| DTO | dto/ | Request/response records |

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
{Step 1: receive request}
→ persist initial state
→ call {integration 1}
→ persist updated state
→ call {integration 2}
→ persist final state
→ return response
```

## 6. Data Architecture
| Table/Collection | Purpose |
|---|---|
| {name} | {what it stores} |

## 7. Cross-Cutting Concerns
| Concern | Approach |
|---|---|
| Auth | {approach} |
| Logging | Structured JSON + trace ID on every line |
| Error Handling | Global handler + structured error response |
| Idempotency | {approach if applicable} |

---

## Approvals
| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
