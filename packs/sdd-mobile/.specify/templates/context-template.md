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
| Language/Framework | {e.g. React Native 0.74 + TypeScript / Flutter 3.x + Dart} |
| Navigation | {e.g. React Navigation / Expo Router / Flutter Navigator 2.0} |
| State Management | {e.g. Redux Toolkit / Zustand / Riverpod / Bloc} |
| Local Storage/DB | {e.g. SQLite / WatermelonDB / Hive / Realm} |
| API Client | {e.g. fetch + React Query / Axios / Dio} |
| Build Tool | {e.g. Metro / Gradle + xcodebuild / Flutter build} |
| Push Notifications | {e.g. Firebase Cloud Messaging / APNs} |
| Crash/Analytics | {e.g. Sentry / Firebase Crashlytics} |
| Data Cache | {e.g. query cache / persisted store / none} |
| Offline Sync | {e.g. queued mutations / background sync / none} |
| Configuration | {e.g. .env files / build flavors per environment} |
| Secrets | {e.g. Keychain / Keystore / secure storage} |
| Resilience | {e.g. retry + offline queue / optimistic UI} |
| Observability | {e.g. crash reporting + performance monitoring} |
| Logging | {e.g. structured logs / remote log shipping} |
| Testing | {e.g. Jest + React Native Testing Library / Detox} |
| Coverage Gate | {e.g. 80% line coverage} |
| Quality/Security | {e.g. ESLint + Prettier / dart analyze, MASVS checklist} |
| CI/CD | {e.g. GitHub Actions / Fastlane lanes} |
| App Store Distribution | {e.g. TestFlight + Play Console internal track} |

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

