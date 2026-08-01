# System Context — {Service Name}
# Version: {version} | Scope: {pilot | mvp | full}
# Date: {date: YYYY-MM-DD} | Author: {author}

> This is the single source of truth for this service.
> All documents, code, tasks, and tests are derived from this file.
> Never change code without updating this context first.

---

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
| OQ-{NNN} | {question} | {owner} | {date: YYYY-MM-DD} |

## 11. Tech Stack
> Drives constitution.md Part 2 (Tech Stack table) at /specify Action 1.
> Fill what you know — leave `[MISSING — ask user]` for the rest; GATE-1
> is where any remaining gaps get finalized.

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

---

## CHANGELOG

### v1.0 — {date: YYYY-MM-DD} — {author}
- Added: Initial version

### How to add future entries:
v{N.N} — {date: YYYY-MM-DD} — {author}
Added:   {new capability or rule}
Changed: {what was modified and why}
Fixed:   {what was corrected}
Removed: {what was explicitly removed}
Impact:  {which documents need updating}

