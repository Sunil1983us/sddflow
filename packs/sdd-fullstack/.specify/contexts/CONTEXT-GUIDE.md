# How to Write Your Context
# This is the ONLY input the agent needs.
# Constitution Part 2 is generated FROM this file.

## Don't Want to Write This Yourself? Use /create-context

Not everyone can fill out a structured context file from scratch — and
that's fine. Run `/create-context` instead:

1. Paste whatever you have — rough notes, an email, a requirements doc,
   even half-formed bullet points. Any format. Cover backend and frontend
   if you can, but partial info for either side is OK.
2. The agent maps it onto the sections below (including the Backend /
   Frontend / Shared Tech Stack tables), fills in what it can, and gives
   you a plain-language checklist of what's still missing.
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
2-3 sentences. What problem does it solve? What does it process — and
which parts are backend vs frontend?
Example: "Lets customer-support agents search, view, and update customer
tickets from a dashboard. The backend validates updates against business
rules and persists them; the frontend renders the ticket list and detail
views."

### 2. Actors
Who uses or calls it — humans and systems, with their role.
Example: `Support Agent | Human | Searches and updates tickets via the
UI`, `Ticketing DB | System | Stores ticket records`.

### 3. Key Flows
Step by step, happy path + key unhappy paths — note which steps happen in
the frontend vs the backend.
Example happy path: "Step 1: Agent searches by email in the UI. Step 2:
Frontend calls GET /api/v1/tickets?email=. Step 3: Backend validates and
queries the DB, returns matching tickets. Step 4: Frontend renders the
list."
Example unhappy path: "Trigger: backend returns 404 (no tickets found).
Steps: frontend shows an empty state with a 'create ticket' call to
action."

### 4. Endpoints
The API contract between backend and frontend — method, path, purpose,
caller, request/response types. This is the single source of truth both
layers are built against.
Example: `GET | /api/v1/tickets?email={email} | Search tickets by
customer email | Frontend | — | TicketSummary[]`.

### 5. Integrations
What external systems are involved, direction, purpose, and whether
Phase 1 uses a mock or the real integration.
Example: `Auth Provider | Inbound | SSO login | Mock`, `Notification
Service | Outbound | Email on ticket update | Real`.

### 6. Business Rules
Specific, verifiable rules the system must enforce — note whether
enforced by the backend, the frontend, or both.
Example: "A ticket cannot be marked Resolved unless it has at least one
agent reply (enforced by backend; frontend disables the button until
true)."

### 7. Non-Functional Requirements
Performance, availability, accessibility, and scalability targets for
both layers.
Example: `Backend Performance | P99 < 300ms`, `Frontend Performance |
First Contentful Paint < 2s`, `Accessibility | WCAG 2.1 AA`,
`Availability | 99.9%`.

### 8. Constraints
Technical, regulatory, and organisational constraints that shape the
design of either layer.
Example: "Must run on existing Kubernetes cluster — no new
infrastructure." / "Must use the existing design system component
library."

### 9. Out of Scope
What is explicitly excluded from this version.
Example: "Multi-currency support — Phase 2." / "Dark mode — not in this
release."

### 10. Open Questions
Things that still need an answer, with an owner and due date — these
get resolved before or during /clarify.
Example: `OQ-001 | Which team owns the notification service SLA? |
Architect | 2026-06-20`.

### 11. Tech Stack
What technologies you are using — drives constitution.md Part 2 (Tech
Stack table, split Backend / Frontend / Shared) at /specify Action 1.
Fill what you know — leave `[MISSING — ask user]` for the rest; GATE-1
(or your scope's equivalent constitution review) is where any remaining
gaps get finalized. This pack covers both layers — fill Backend AND
Frontend; Shared applies to both.
Example: `Backend: Language | Java 21`, `Frontend: Framework | React 18`,
`Shared: API Style | REST + OpenAPI`.

## What the Agent Extracts for Constitution

From your tech stack section (Backend, Frontend, and Shared):
  Backend:  Language, Framework, Build Tool, Messaging/Async, Schema,
            Data Store, Data Cache, DB Migration, Resilience, Testing,
            Coverage Gate
  Frontend: Language, Framework, Build Tool, State Management, Component
            Library/Design System, Routing, API Client, Data Cache,
            Testing, Coverage Gate, Accessibility
  Shared:   API Style, Serialisation, Configuration, Secrets,
            Observability, Logging, Quality/Security, Orchestration,
            CI/CD
  → fills constitution Tech Stack table for both layers

From your constraints section:
  Business rules → Domain Rules
  "never do" items → Never Do list
  Compliance requirements → Core Principles

## Template

# System Context — {Service Name}
# Version: {version} | Scope: {pilot | mvp | full}
# Date: {date} | Author: {author}

## 1. What This Service Does
{2-3 sentences. What problem does it solve? What does it process — and
which parts are backend vs frontend?}

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
> Drives constitution.md Part 2 (Tech Stack table) at /specify Action 1.
> Fill what you know — leave `[MISSING — ask user]` for the rest; GATE-1
> (or your scope's equivalent constitution review) is where any remaining
> gaps get finalized. This pack covers both layers — fill Backend AND
> Frontend; Shared applies to both.

### Backend
| Concern | Choice |
|---|---|
| Language | {e.g. Java 21} |
| Framework | {e.g. Spring Boot 3.x} |
| Build Tool | {e.g. Maven} |
| Messaging/Async | {e.g. Kafka / RabbitMQ / none} |
| Schema | {e.g. Flyway-managed SQL} |
| Data Store | {e.g. PostgreSQL 15} |
| Data Cache | {e.g. Redis / none} |
| DB Migration | {e.g. Flyway / Liquibase} |
| Resilience | {e.g. Resilience4j — retry/circuit breaker} |
| Testing | {e.g. JUnit 5 + Testcontainers} |
| Coverage Gate | {e.g. 80% line coverage} |

### Frontend
| Concern | Choice |
|---|---|
| Language | {e.g. TypeScript 5.x} |
| Framework | {e.g. React 18} |
| Build Tool | {e.g. Vite} |
| State Management | {e.g. Redux Toolkit / Zustand / Pinia / Context API} |
| Component Library/Design System | {e.g. MUI / shadcn-ui / Tailwind + custom} |
| Routing | {e.g. React Router / Vue Router / Angular Router} |
| API Client | {e.g. fetch + React Query / Axios / Apollo} |
| Data Cache | {e.g. React Query cache / none} |
| Testing | {e.g. Vitest + Testing Library} |
| Coverage Gate | {e.g. 80% line coverage} |
| Accessibility | {e.g. axe-core, WCAG 2.1 AA} |

### Shared
| Concern | Choice |
|---|---|
| API Style | {e.g. REST + OpenAPI} |
| Serialisation | {e.g. JSON / Avro / Protobuf} |
| Configuration | {e.g. env vars / config server / .env files} |
| Secrets | {e.g. Vault / cloud secrets manager — never in frontend bundle} |
| Observability | {e.g. OpenTelemetry + Grafana / Sentry / RUM} |
| Logging | {e.g. structured JSON logs (backend) / console + error boundary (frontend)} |
| Quality/Security | {e.g. SonarQube + OWASP Dependency-Check + ESLint} |
| Orchestration | {e.g. Kubernetes} |
| CI/CD | {e.g. GitHub Actions / Jenkins} |

## CHANGELOG
### v1.0 — {date} — {author}
- Added: Initial version
