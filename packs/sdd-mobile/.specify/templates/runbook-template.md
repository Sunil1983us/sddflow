# Runbook
# Feature: {Feature Name}
> Version: 1.0 | Date: {date}
> Scope: MVP+ only — skip for pilot

---

## References
| Source | Sections / IDs Used |
|---|---|
| plan.summary.md | {sections/IDs referenced} |
| arch.summary.md | {sections/IDs referenced} |

## 1. Local Setup

```bash
git clone {repo}
cd {app}
cp .env.example .env          # fill values
npm install                    # or: flutter pub get
{run command}                  # e.g. npx react-native run-ios
                                # or: flutter run -d <device>
```

**Health check:** App launches to home screen without crash, API client
reaches mock/staging backend.

---

## 2. Build Profiles

| Profile | Purpose | Backend Target |
|---|---|---|
| mock | Local dev / unit-test | All API calls mocked |
| staging | QA / UAT / TestFlight internal | Staging backend |
| production | App store release | Production backend |

---

## 3. Common Operations

| Task | Command |
|---|---|
| Run unit tests | `{test command}` |
| Run component/screen tests | `{component test command}` |
| Run E2E (Detox/integration_test) | `{e2e command}` |
| Check coverage | `{coverage command}` |
| Build release artifact | `{fastlane/gradle/xcodebuild command}` |
| View device logs | `{adb logcat / xcrun simctl spawn booted log}` |

---

## 4. Troubleshooting

| Symptom | Likely Cause | Resolution |
|---|---|---|
| {symptom} | {cause} | {fix} |
| App crashes on launch (prod build only) | Missing/invalid env config injected at build time | Verify CI build container secrets — never debug with prod keys locally |
| API calls failing in staging build | Wrong build profile / base URL | Confirm `.env` profile matches target backend |
| Offline queue not syncing | Connectivity listener not re-attached after backgrounding | Check resilience.md §sync retry policy |

---

## 5. Key Environment Variables

| Variable | Purpose | Example |
|---|---|---|
| {VAR_NAME} | {purpose} | {example — no real secrets} |

---

## 6. Rollback

### Staged Rollout Halt (Play Console / App Store Connect)
```
1. Open Play Console → Production → Release → Halt rollout
   (or App Store Connect → reject/remove the build from sale)
2. Confirm current rollout percentage frozen — no new installs receive
   the bad build
3. Notify on-call (see §7) and roles.yml devops_sre
```

### OTA Update Rollback (CodePush / EAS Update — if applicable)
```bash
# CodePush
appcenter codepush rollback {app-name} {deployment} 

# EAS Update
eas update --branch {branch} --message "rollback to {previous-update-id}"
```
If no OTA mechanism configured: ship an emergency hotfix release through
the standard store pipeline (expedited review).

### App-Store Incident Response (rejected release / emergency hotfix)
```
1. If release REJECTED by store review:
   - Read rejection reason, fix per security-design.md / MASVS checklist
   - Re-submit with CHG-NNN task referencing the rejection
2. If CRITICAL bug found post-release:
   - Halt staged rollout (above) immediately
   - Trigger OTA rollback if available — otherwise prepare expedited
     hotfix build
   - Open incident per investigation.md (Crash & Incident Triage)
```

---

## 7. On-Call Quick Reference

| Alert | First Action | Escalation |
|---|---|---|
| Crash-free rate drops below {target %} (Crashlytics/Play Vitals) | Halt staged rollout | devops_sre (roles.yml) → tech_lead |
| Spike in {specific crash signature} | Check investigation.md INV-NNN playbook | tech_lead → architect |
| OTA update failing to apply | OTA rollback (above) | devops_sre (roles.yml) |
| App rejected by store review | Read rejection reason, assign CHG-NNN | product_owner + tech_lead |

---

## Approvals
| Role | Approver | Status | Date |
|---|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | | Pending | |
