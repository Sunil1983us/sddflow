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
Example: "Lets customer-support agents search, view, and update customer
tickets from a single dashboard, with real-time status updates."

### 2. Actors
Who uses or calls it — humans and systems, with their role.
Example: `Support Agent | Human | Searches and updates tickets`,
`Ticketing API | System | Source of ticket data`.

### 3. Key Flows
Step by step, happy path + key unhappy paths.
Example happy path: "Step 1: Agent logs in. Step 2: Agent searches for a
ticket by customer email. Step 3: App displays matching tickets in a
list."
Example unhappy path: "Trigger: search returns no results. Steps: app
shows an empty state with a 'create ticket' call to action."

### 4. Endpoints
The backend API surface this app consumes — method, path, purpose,
caller, request/response types it expects.
Example: `GET | /api/v1/tickets?email={email} | Search tickets by
customer email | Agent UI | — | TicketSummary[]`.

### 5. Integrations
What external systems are involved, direction, purpose, and whether
Phase 1 uses a mock or the real integration.
Example: `Ticketing API | Inbound | Fetch + update ticket data | Real`,
`Auth Provider | Inbound | SSO login | Mock`.

### 6. Business Rules
Specific, verifiable rules the UI must enforce.
Example: "A ticket cannot be marked Resolved unless it has at least one
agent reply."

### 7. Non-Functional Requirements
Performance, accessibility, browser/device support targets.
Example: `Performance | First Contentful Paint < 2s`, `Accessibility |
WCAG 2.1 AA`, `Browser Support | Latest 2 versions of Chrome/Firefox/Safari`.

### 8. Constraints
Technical and organisational constraints that shape the design.
Example: "Must use the existing design system component library." /
"Must support keyboard-only navigation throughout."

### 9. Out of Scope
What is explicitly excluded from this version.
Example: "Dark mode — Phase 2." / "Offline support — not in this
release."

### 10. Open Questions
Things that still need an answer, with an owner and due date — these
get resolved before or during /clarify.
Example: `OQ-001 | Which design system version are we standardising on? |
Tech Lead | 2026-06-20`.

### 11. Tech Stack
What technologies you are using — drives constitution.md Part 2 (Tech
Stack table) at /specify Action 1. Fill what you know — leave
`[MISSING — ask user]` for the rest; GATE-1 is where any remaining gaps
get finalized.
Example: `Language | TypeScript 5.x`, `Framework | React 18`, `Build Tool
| Vite`.

## What the Agent Extracts for Constitution

From your tech stack section:
  Language, Framework, Build Tool, State Management, Component
  Library/Design System, Routing, API Client, Bundler, Data Cache,
  Configuration, Secrets, Resilience, Observability, Logging, Testing,
  Coverage Gate, Linting/Formatting, Accessibility, CI/CD, Hosting/CDN →
  fills Tech Stack table

From your constraints section:
  Business rules → Domain Rules
  "never do" items → Never Do list
  Compliance requirements → Core Principles

## Template

# System Context — {App Name}
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
Step 2: {app calls API → result}
Step 3: {outcome}

### Flow 2: {Name} — Unhappy Path (if in scope)
Trigger: {what causes this}
Steps: {what happens + resolution}

## 4. Endpoints
| Method | Path | Purpose | Caller | Request | Response |
|---|---|---|---|---|---|
| GET | /api/v1/{resource} | {purpose} | {caller} | {type} | {type} |

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
| Performance | {load time target} |
| Accessibility | {WCAG level} |
| Browser Support | {browsers/versions} |

## 8. Constraints
- {Technical constraint}
- {Organisational constraint}

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
| Language | {e.g. TypeScript 5.x} |
| Framework | {e.g. React 18} |
| Build Tool | {e.g. Vite} |
| State Management | {e.g. Redux Toolkit / Zustand / Pinia / Context API} |
| Component Library/Design System | {e.g. MUI / shadcn-ui / Tailwind + custom} |
| Routing | {e.g. React Router / Vue Router / Angular Router} |
| API Client | {e.g. fetch + React Query / Axios / Apollo} |
| Bundler | {e.g. Vite / Webpack / Next.js / Nuxt} |
| Data Cache | {e.g. React Query cache / none} |
| Configuration | {e.g. .env files / runtime config.json} |
| Secrets | {e.g. env vars — never in bundle} |
| Resilience | {e.g. retry on fetch / offline handling} |
| Observability | {e.g. Sentry / RUM / none} |
| Logging | {e.g. structured console logs / error boundary} |
| Testing | {e.g. Vitest + Testing Library} |
| Coverage Gate | {e.g. 80% line coverage} |
| Linting/Formatting | {e.g. ESLint + Prettier} |
| Accessibility | {e.g. axe-core, WCAG 2.1 AA} |
| CI/CD | {e.g. GitHub Actions} |
| Hosting/CDN | {e.g. S3 + CloudFront / Vercel / Netlify / nginx} |

## CHANGELOG
### v1.0 — {date} — {author}
- Added: Initial version
