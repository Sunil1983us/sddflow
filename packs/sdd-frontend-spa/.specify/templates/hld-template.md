# High Level Design (HLD)
# Feature: {Feature Name}
> Version: 1.0 | Status: Draft | Date: {date} | Author: {author}

---

## References
| Source | Sections / IDs Used |
|---|---|
| arch.summary.md | {sections/IDs referenced} |
| use-cases.summary.md | {UC-NNN flows used in sequence diagram} |
| srd.summary.md | {NFR-NNN targets used in Section 6} |

## 1. System Context (C4 Level 1)
```mermaid
graph TD
    Actor(["{Actor / User}"])
    Caller["{Upstream Service}"]
    ThisService["{This Service}"]
    IntA["{Integration A}"]
    IntB["{Integration B}"]
    DB[("{Database}")]

    Actor -->|"{action}"| Caller
    Caller -->|"{request}"| ThisService
    ThisService -->|"{call}"| IntA
    ThisService -->|"{call}"| IntB
    ThisService -->|"reads/writes"| DB
```

## 2. Container Diagram (C4 Level 2)
```mermaid
graph TD
    subgraph "{Environment}"
        App["{Service} App"]
        DB[("{Database}")]
        Cache[("{Cache}")]
        MQ["{Message Broker}"]
    end
    Caller -->|"{protocol}"| App
    App -->|"ORM"| DB
    App -->|"cache"| Cache
    App -->|"publish/subscribe"| MQ
```

## 3. Happy Path Sequence
```mermaid
sequenceDiagram
    participant C as {Caller}
    participant S as {This Service}
    participant I1 as {Integration 1}
    participant I2 as {Integration 2}
    participant DB as {Database}

    C->>S: {request}
    S->>DB: persist {initial state}
    S-->>C: {immediate response}

    S->>I1: {call}
    I1-->>S: {result}
    S->>DB: persist {updated state}

    S->>I2: {call}
    I2-->>S: {result}
    S->>DB: persist {final state}
```

## 4. State Machine
> Include if this feature has stateful entities (orders, payments, bookings, etc.).
> If no stateful entity exists, replace this section with: "No state machine — this feature has no stateful entity."

```mermaid
stateDiagram-v2
    [*] --> {STATE_1}
    {STATE_1} --> {STATE_2} : {trigger}
    {STATE_2} --> {STATE_3} : {trigger}
    {STATE_3} --> {TERMINAL_SUCCESS} : {trigger}
    {STATE_2} --> {TERMINAL_FAILURE} : {error}
    {TERMINAL_SUCCESS} --> [*]
    {TERMINAL_FAILURE} --> [*]
```

## 5. Technology Stack
| Layer | Technology | Version |
|---|---|---|
| Language | {from constitution Part 2} | {version} |
| Framework | {from constitution Part 2} | {version} |
| Database | {from constitution Part 2} | {version} |
| Cache | {from constitution Part 2} | {version} |
| Messaging | {from constitution Part 2} | {version} |
| Deployment | {from constitution Part 2} | |

## 6. NFR Summary
| NFR-NNN | Category | Target |
|---|---|---|
| NFR-{NNN} | Response time | {measurable target from srd.summary.md} |
| NFR-{NNN} | Availability | {e.g. 99.9% uptime} |
| NFR-{NNN} | Throughput | {e.g. 100 TPS} |

---
*All diagrams: Mermaid — renders in GitHub, VS Code, Claude. Paste into https://mermaid.live to verify before approving.*

## Approvals
| Role | Status | Date |
|---|---|---|
| Architect | Pending | |
| Tech Lead | Pending | |

## Version History
| Version | Date | Changed By | Summary | CHG-NNN |
|---|---|---|---|---|
| 1.0 | {date} | {author} | Initial draft | — |
