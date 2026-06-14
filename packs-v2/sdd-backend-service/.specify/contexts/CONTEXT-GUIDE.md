# How to Write Your Context
# This is the ONLY input the agent needs.
# Constitution Part 2 is generated FROM this file.

## Don't Want to Write This Yourself? Use /create-context

Not everyone can fill out a structured context file from scratch — and
that's fine. Run `/create-context` instead:

1. Paste whatever you have — rough notes, an email, a requirements doc,
   even half-formed bullet points. Any format.
2. The agent maps it onto the sections below, fills in what it can, and
   gives you a plain-language checklist of what's still missing.
3. Answer what you can (partial answers OK, "not sure" is fine for
   technical questions — the architect decides later at /plan-arch).
4. The agent saves the finished `.specify/contexts/{feature}.md` — the
   same file /specify reads either way.

Your original raw notes can optionally be kept as
`.specify/contexts/{feature}.raw.md` (reference only — not read by any
other command) so you can re-run `/create-context` later with more detail
(e.g. when scope upgrades from pilot to mvp/full).

If you're comfortable writing the structured file directly, skip
`/create-context` and follow the template below.

## What to Include

### 1. What This Service Does
2-3 sentences. What problem does it solve? What does it process?
Example: "Processes inbound payment instructions from partner banks,
validates them against compliance rules, and forwards approved
instructions to the settlement engine."

### 2. Actors
Who uses or calls it — humans and systems, with their role.
Example: `Ops Analyst | Human | Reviews flagged payments`,
`Settlement Engine | System | Receives approved instructions`.

### 3. Key Flows
Step by step, happy path + key unhappy paths.
Example happy path: "Step 1: Partner bank submits payment via API.
Step 2: System validates against compliance rules — passes.
Step 3: System forwards to settlement engine, returns 202 Accepted."
Example unhappy path: "Trigger: compliance check fails. Steps: payment
flagged for manual review, ops analyst notified, payment held."

### 4. Endpoints
The API surface this service exposes — method, path, purpose, caller,
request/response types.
Example: `POST | /api/v1/payments | Submit a payment instruction |
Partner Bank | PaymentRequest | PaymentAccepted`.

### 5. Integrations
What external systems are involved, direction, purpose, and whether
Phase 1 uses a mock or the real integration.
Example: `Settlement Engine | Outbound | Forward approved payments |
Real`, `Fraud Service | Outbound | Real-time risk score | Mock`.

### 6. Business Rules
Specific, verifiable rules the system must enforce.
Example: "A payment over $10,000 must be flagged for manual review
before forwarding."

### 7. Non-Functional Requirements
Performance, availability, throughput, data retention targets.
Example: `Performance | P99 < 300ms`, `Availability | 99.9%`,
`Throughput | 500 TPS peak`, `Data Retention | 7 years`.

### 8. Constraints
Technical and regulatory constraints that shape the design.
Example: "Must run on existing Kubernetes cluster — no new
infrastructure." / "Must comply with PCI-DSS for card data."

### 9. Out of Scope
What is explicitly excluded from this version.
Example: "Multi-currency support — Phase 2." / "Batch payment uploads —
not in this release."

### 10. Open Questions
Things that still need an answer, with an owner and due date — these
get resolved before or during /clarify.
Example: `OQ-001 | Which team owns the fraud service SLA? |
Architect | 2026-06-20`.

### 11. Tech Stack
What technologies you are using — drives constitution.md Part 2 (Tech
Stack table) at /specify Action 1. Fill what you know — leave
`[MISSING — ask user]` for the rest; GATE-1 is where any remaining gaps
get finalized.
Example: `Language | Java 21`, `Framework | Spring Boot 3.x`,
`Data Store | PostgreSQL 15`.

## What the Agent Extracts for Constitution

From your tech stack section:
  Language, Framework, Build Tool, API Style, Messaging/Async,
  Serialisation, Schema, Data Store, Data Cache, DB Migration,
  Configuration, Secrets, Resilience, Observability, Logging, Testing,
  Coverage Gate, Quality/Security, Orchestration, CI/CD → fills Tech
  Stack table

From your constraints section:
  Business rules → Domain Rules
  "never do" items → Never Do list
  Compliance requirements → Core Principles

## Template

# System Context — {Service Name}
# Version: {version} | Scope: {pilot | mvp | full}
# Date: {date} | Author: {author}

## 1. What This Service Does
{2-3 sentences. What problem does it solve? What does it process?}

## 2. Actors

| Actor | Type | Role |
|---|---|---|
| {name} | Human / System | {role} |

## 3. Key Flows

### Flow 1: {Name} — Happy Path
Step 1: {who does what}
Step 2: {system calls downstream → result}
Step 3: {outcome}

### Flow 2: {Name} — Unhappy Path (if in scope)
Trigger: {what causes this}
Steps: {what happens + resolution}

## 4. Endpoints

| Method | Path | Purpose | Caller | Request | Response |
|---|---|---|---|---|---|
| POST | /api/v1/{resource} | {purpose} | {caller} | {type} | {type} |

## 5. Integrations

| System | Direction | Purpose | Phase 1 |
|---|---|---|---|
| {name} | Inbound/Outbound | {purpose} | Mock/Real |

## 6. Business Rules
- {Rule 1 — specific and verifiable}
- {Rule 2}

## 7. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Performance | {P99 response target} |
| Availability | {uptime target} |
| Throughput | {TPS peak} |
| Data Retention | {years} |

## 8. Constraints
- {Technical constraint}
- {Regulatory constraint}

## 9. Out of Scope
- {Excluded item 1}
- {Excluded item 2}

## 10. Open Questions

| ID | Question | Owner | Due |
|---|---|---|---|
| OQ-001 | {question} | {owner} | {date} |

## 11. Tech Stack

| Concern | Choice |
|---|---|
| Language | {e.g. Java 21} |
| Framework | {e.g. Spring Boot 3.x} |
| Build Tool | {e.g. Maven} |
| API Style | {e.g. REST + OpenAPI} |
| Messaging/Async | {e.g. Kafka / RabbitMQ / none} |
| Serialisation | {e.g. JSON / Avro / Protobuf} |
| Schema | {e.g. Flyway-managed SQL} |
| Data Store | {e.g. PostgreSQL 15} |
| Data Cache | {e.g. Redis / none} |
| DB Migration | {e.g. Flyway / Liquibase} |
| Configuration | {e.g. Spring Config / env vars} |
| Secrets | {e.g. Vault / cloud secrets manager} |
| Resilience | {e.g. Resilience4j — retry/circuit breaker} |
| Observability | {e.g. OpenTelemetry + Grafana} |
| Logging | {e.g. structured JSON logs} |
| Testing | {e.g. JUnit 5 + Testcontainers} |
| Coverage Gate | {e.g. 80% line coverage} |
| Quality/Security | {e.g. SonarQube + OWASP Dependency-Check} |
| Orchestration | {e.g. Kubernetes} |
| CI/CD | {e.g. GitHub Actions / Jenkins} |

## CHANGELOG
### v1.0 — {date} — {author}
- Added: Initial version
