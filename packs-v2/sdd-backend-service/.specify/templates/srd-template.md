# System Requirements Document (SRD)
# Feature: {Feature Name}
> Version: 1.0 | Date: {date}

---

## References

| Source | Sections / IDs Used |
|---|---|
| brd.summary.md | {sections/IDs referenced} |
| .specify/contexts/{feature}.md | {sections/IDs referenced} |

## 1. System Overview
{One paragraph — what this system does technically.}

## 2. Functional Requirements

| ID | Requirement | Source | Priority |
|---|---|---|---|
| FR-001 | {description} | BR-{NNN} | Must Have |
| FR-002 | {description} | BR-{NNN} | Should Have |

## 3. Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-001 | Performance | {e.g. P99 response ≤ 500ms} |
| NFR-002 | Availability | {e.g. 99.9% uptime} |
| NFR-003 | Throughput | {e.g. 100 TPS peak} |
| NFR-004 | Security | {e.g. all endpoints require auth} |
| NFR-005 | Data Retention | {e.g. 7 years} |

## 4. Use Cases

### UC-001: {Use Case Name} — Happy Path
- **Actor:** {who triggers this}
- **Trigger:** {what starts the flow}
- **Precondition:** {what must be true}
- **Steps:**
  1. {step}
  2. {step}
- **Outcome:** {successful result}

### UC-002: {Use Case Name} — Unhappy Path
- **Trigger:** {what causes this path}
- **Steps:** {what happens}
- **Outcome:** {error result + recovery}

## 5. Integrations

| System | Endpoint | Direction | Phase 1 |
|---|---|---|---|
| {name} | {path} | Inbound/Outbound | Mock/Real |

## 6. Data Requirements

| Entity | Description | New/Existing |
|---|---|---|
| {name} | {what it represents} | New |

## 7. Constraints
- {technical constraint}
- {regulatory constraint}
- {business constraint}

---

## Approvals

| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
