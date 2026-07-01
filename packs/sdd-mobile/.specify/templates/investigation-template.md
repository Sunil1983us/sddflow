# Crash & Incident Triage
# Feature: {Feature Name}
> Version: 1.0 | Date: {date}
> Scope: Full only — skip for pilot + mvp

---

## References
| Source | Sections / IDs Used |
|---|---|
| srd.summary.md | {sections/IDs referenced — drafted at /specify} |
| arch.summary.md | {sections/IDs referenced — refined at /plan-arch: flows} |

## 1. Crash-Reporting SDK Integration

| Concern | Detail |
|---|---|
| SDK | {Firebase Crashlytics / Sentry — from constitution.md Tech Stack → Crash/Analytics} |
| Init location | {entry file, e.g. `index.js` / `AppDelegate`/`MainApplication` — before app render} |
| Environment tagging | `environment: {dev/staging/prod}`, `release: {app version} (build {n})` |
| Correlation | Every crash/error event tagged with `correlationId` (matches `X-Correlation-Id` sent to backend — api-spec.md §3) |
| PII scrubbing | `beforeSend`/custom keys strip: {list fields — auth tokens, fields marked Confidential/Restricted in data-model.md §10} |
| Sample rate | Crashes: 100% | Non-fatal errors: {n%} |

---

## 2. Symbolication — dSYM (iOS) & ProGuard/R8 Mapping (Android)

| Step | Detail |
|---|---|
| iOS dSYM | CI build step uploads dSYM files to {Crashlytics/Sentry} after each release build (Xcode Cloud / macOS runner — constitution Part 1 OPS-7) |
| Android mapping | CI uploads `mapping.txt` (ProGuard/R8) to {Crashlytics/Sentry} as part of the release build (`./gradlew assembleRelease` + upload task) |
| Versioning | Symbol files tagged with exact `versionName` + `versionCode`/`buildNumber` to match crash reports |
| Verification | Confirm stack traces in crash dashboard show original Swift/Kotlin/JS file + line, not obfuscated symbols |
| React Native source maps | Hermes/JSC source maps uploaded per release for JS-layer stack traces |

---

## 3. Crash-Free Rate Dashboards

| Metric | Target | Dashboard |
|---|---|---|
| Crash-free users | > {99.5%} | {dashboard link/name} |
| Crash-free sessions | > {99%} | {dashboard link/name} |
| ANR rate (Android) | < {0.47%} (Play Console threshold) | {dashboard link/name} |
| Non-fatal error rate | < {threshold}% of sessions | {dashboard link/name} |
| API error rate (client-observed) | < {threshold}% of calls | {dashboard link/name} |

---

## 4. Investigation Triggers

| ID | Trigger | Severity | SLA |
|---|---|---|---|
| INV-{NNN} | {what causes this — e.g. crash-free rate drops below target after release} | High | {time to resolve} |
| INV-{NNN} | {what causes this — e.g. ANR rate spike on a specific device/OS combination} | Medium | {time to resolve} |
| INV-{NNN} | {what causes this — e.g. app-store review flags 1-star reviews mentioning crashes} | Medium | {time to resolve} |

---

## 5. Investigation Case: INV-{NNN} — {Title}

**Trigger:** {exact condition that triggers investigation — alert/threshold}
**Detected by:** {crash-reporting alert / dashboard / app-store review}
**Impact:** {what is affected — screen, OS version, device segment}

**Resolution Steps:**
1. Open crash-reporting issue — confirm affected release/build and
   correlation ID(s)
2. Cross-reference correlation ID with backend logs (api-spec.md §3
   X-Correlation-Id) to determine if root cause is client or server
3. Reproduce using the playbook in §7
4. {fix / rollback via store (halted rollout) / remote-config feature-flag off}

**Data to Collect:**
- {correlationId}
- {device model, OS version, app version/build}
- {screen + view-model/state at time of crash}
- {timestamp range}

**Resolution:** {how to close the case}
**Prevention:** {what to change to avoid recurrence — e.g. add defensive
check, add test case, add monitoring}

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

## 7. Reproduction Playbook (Device/OS Version Capture)

When a crash or bug is reported, collect:

| Field | How to Collect |
|---|---|
| Device model | From crash report metadata, or ask user (Settings → About) |
| OS version | From crash report metadata (iOS version / Android API level) |
| App version + build number | From crash report, or in-app About screen |
| Locale/timezone | From crash report metadata |
| Correlation ID(s) | From crash report breadcrumbs, or ask user for approximate time to search backend logs |
| Network state at time of crash | Online/offline, connection type (wifi/cellular) — from breadcrumbs |
| Steps to reproduce | Exact navigation path — use session breadcrumbs if enabled |
| Screenshot/screen recording | Attach if available |

**Reproduce locally:**
1. Match device/OS as closely as possible (simulator/emulator with matching
   OS version, or physical device matching the model class)
2. Use the correlation ID to pull the matching backend request/response
   from logs (api-spec.md)
3. Replay the user flow against staging with matching data shape and
   matching connectivity state (offline/online — resilience.md)

---

## 8. Triage Severity Matrix

| Severity | Definition | Examples | Response |
|---|---|---|---|
| Critical | App crashes on launch or for all/most users | Crash loop on startup, auth broken | Page on-call immediately, halted rollout / hotfix release |
| High | Core flow crashes for a segment | Crash on checkout for one device family | Fix within SLA (INV table), staged rollout halted if % affected high |
| Medium | Non-core feature crashes, workaround exists | Crash in settings screen, app remains usable | Scheduled fix next release |
| Low | Cosmetic / rare edge case | Crash on rare device/OS combination, low frequency | Backlog |

---

## 9. Crash/Incident Log Schema

```json
{
  "investigationId": "UUID",
  "trigger": "INV-{NNN}",
  "correlationId": "UUID — matches X-Correlation-Id sent to backend",
  "release": "string — app version (build N)",
  "platform": "ios | android",
  "osVersion": "string",
  "deviceModel": "string",
  "screen": "string — screen/route at time of crash",
  "detectedAt": "ISO 8601",
  "resolvedAt": "ISO 8601 or null",
  "status": "OPEN | IN_PROGRESS | RESOLVED",
  "notes": "string"
}
```

---

## 10. Alerts → Investigation Mapping

| Alert | Triggers | Auto-create? |
|---|---|---|
| Crash-free rate < target | INV-001 | Yes |
| ANR rate spike (Android) | INV-002 | Yes |
| App-store review flags (1-2 star, mentions crash) | INV-003 | No — reviewed weekly |
| API error rate (client-observed) > {threshold} | INV-{NNN} | Yes |

---

## Approvals
| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
