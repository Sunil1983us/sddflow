# Production Debugging & Error Tracking
# Feature: {Feature Name}
> Version: 1.0 | Date: {date: YYYY-MM-DD}
> Scope: Full only — skip for pilot + mvp

---

## References
| Source | Sections / IDs Used |
|---|---|
| srd.summary.md | {sections/IDs referenced — drafted at /specify} |
| arch.summary.md | {sections/IDs referenced — refined at /plan-arch: flows} |

## 1. Error-Tracking SDK Integration

| Concern | Detail |
|---|---|
| SDK | {Sentry / Bugsnag / etc. — from constitution.md Tech Stack → Observability} |
| Init location | {entry file, e.g. `src/main.tsx` — before app render} |
| Environment tagging | `environment: {dev/staging/prod}`, `release: {app version}` |
| Correlation | Every error event tagged with `correlationId` (matches `X-Correlation-Id` sent to backend — api-spec.md §3) |
| PII scrubbing | `beforeSend` hook strips: {list fields — auth tokens, form field values marked Confidential/Restricted in data-model.md §6} |
| Sample rate | Errors: 100% | Performance/RUM traces: {n%} |

---

## 2. Source-Map Upload (Readable Stack Traces)

| Step | Detail |
|---|---|
| Build | Source maps generated for production build (`{build tool} build --sourcemap`) |
| Upload | CI step uploads source maps to {Sentry/Bugsnag} on release, tagged with `release` version |
| Hosting | Source maps NOT served publicly — uploaded then excluded from deploy artifact (OPS-7) |
| Verification | Confirm stack traces in error-tracking dashboard show original TS/JSX file + line, not minified bundle |

---

## 3. RUM (Real User Monitoring) Dashboards

| Metric | Target | Dashboard |
|---|---|---|
| Largest Contentful Paint (LCP) | < {2.5s} | {dashboard link/name} |
| Interaction to Next Paint (INP) | < {200ms} | {dashboard link/name} |
| Cumulative Layout Shift (CLS) | < {0.1} | {dashboard link/name} |
| JS error rate | < {threshold}% of sessions | {dashboard link/name} |
| API error rate (client-observed) | < {threshold}% of calls | {dashboard link/name} |

---

## 4. Investigation Triggers

| ID | Trigger | Severity | SLA |
|---|---|---|---|
| INV-{NNN} | {what causes this — e.g. spike in JS error rate on /checkout} | High | {time to resolve} |
| INV-{NNN} | {what causes this — e.g. Core Web Vitals regression after deploy} | Medium | {time to resolve} |

---

## 5. Investigation Case: INV-{NNN} — {Title}

**Trigger:** {exact condition that triggers investigation — alert/threshold}
**Detected by:** {error-tracking alert / RUM dashboard / user report}
**Impact:** {what is affected — route, user segment, browser}

**Resolution Steps:**
1. Open error-tracking issue — confirm affected release/version and
   correlation ID(s)
2. Cross-reference correlation ID with backend logs (api-spec.md §3
   X-Correlation-Id) to determine if root cause is client or server
3. Reproduce using the playbook in §7
4. {fix / rollback / feature-flag off}

**Data to Collect:**
- {correlationId}
- {browser, OS, viewport — from error event context}
- {route + component stack}
- {timestamp range}

**Resolution:** {how to close the case}
**Prevention:** {what to change to avoid recurrence — e.g. add error
boundary, add test case}

---

## 6. Investigation Case: INV-{NNN} — {Title}

**Trigger:** {condition}
**Detected by:** {method}
**Impact:** {impact}

**Resolution Steps:**
1. {step}
2. {step}

**Resolution:** {how to close}

---

## 7. Reproduction Playbook (User-Reported Bugs)

When a user reports a bug, collect:

| Field | How to Collect |
|---|---|
| Browser + version | `navigator.userAgent` or ask user |
| OS | `navigator.userAgent` or ask user |
| Viewport size | `window.innerWidth x window.innerHeight` |
| App version/release | Footer/about page or build info endpoint |
| Correlation ID(s) | From error-tracking session replay, or ask user for timestamp to search logs |
| Steps to reproduce | Exact click path — use session replay if enabled |
| Screenshot/recording | Attach if available |

**Reproduce locally:**
1. Match browser/OS/viewport as closely as possible (browser dev tools
   device emulation, or matching real device)
2. Use the correlation ID to pull the matching backend request/response
   from logs (api-spec.md)
3. Replay the user flow against staging with matching data shape

---

## 8. Triage Severity Matrix

| Severity | Definition | Examples | Response |
|---|---|---|---|
| Critical | App unusable for all/most users | Blank screen on load, auth broken | Page on-call immediately, hotfix/rollback |
| High | Core flow broken for a segment | Checkout fails for one payment method | Fix within SLA (INV table), feature-flag off if possible |
| Medium | Non-core feature broken, workaround exists | Filter UI broken but list still loads | Scheduled fix next release |
| Low | Cosmetic / edge case | Minor layout issue on rare viewport | Backlog |

---

## 9. Error-Tracking Event Schema

```json
{
  "eventId": "UUID",
  "correlationId": "UUID — matches X-Correlation-Id sent to backend",
  "release": "string — app version",
  "environment": "dev | staging | prod",
  "route": "string — current route/path",
  "componentStack": "string",
  "errorMessage": "string",
  "browser": "string",
  "os": "string",
  "viewport": "string — e.g. 1280x800",
  "timestamp": "ISO 8601"
}
```

---

## 10. Alerts → Investigation Mapping

| Alert | Triggers | Auto-create? |
|---|---|---|
| JS error rate > {threshold} | INV-001 | Yes |
| Core Web Vitals regression | INV-002 | No — reviewed weekly |
| API error rate (client-observed) > {threshold} | INV-{NNN} | Yes |

---

## Approvals
| Role | Approver | Status | Date |
|---|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | | Pending | |
