# Security Design
# App: {App Name}
> Version: 1.0 | Date: {date} | Generated at ALL scopes — depth scales
> with scope (see section markers)
>
> **Living document** — describes the whole app's security baseline
> (Keychain/Keystore usage, transport, MASVS controls), not one feature.
> Lives at `.specify/service/security-design.md`. Every feature after the
> first one extends this file (new threats, new audit events, new
> regulatory trace rows) via the living-doc-update shared block in
> `specify-doc.prompt.md` — it is never regenerated from a blank
> template.

---

## References
| Source | Sections / IDs Used |
|---|---|
| srd.summary.md | {sections/IDs referenced — drafted at /specify} |
| arch.summary.md | {sections/IDs referenced — refined at /plan-arch: cross-cutting concerns} |

## 1. Pilot Security Checklist (always)

| Control | Requirement | Status | Evidence |
|---|---|---|---|
| AuthN | All API calls require auth token (NFR-{NNN}) | {Yes/No} | {TC-NNN / TASK-NNN / scan on {date}} |
| Secure local storage | Tokens/secrets in Keychain (iOS) / Keystore (Android) — never plain AsyncStorage/SharedPreferences | {Yes/No} | {TC-NNN / code review reference} |
| Transport | TLS enforced for all API calls — no plaintext HTTP | {Yes/No} | {TC-NNN / network config reference} |
| Input validation | All user input validated before use (no raw passthrough) | {Yes/No} | {TC-NNN validation tests} |
| PII in logs | Never logged at any level (constitution Logging rule) | {Yes/No} | {log review / SAST result on {date}} |
| Secrets in bundle | No API keys/secrets baked into app bundle — secure config injection at build time | {Yes/No} | {secret-scan tool run on {date}, report at {location}} |
| Dependency check | No known-critical CVEs in dependencies | {Yes/No} | {{tool} scan on {date} — {N} critical, {N} high CVEs, all resolved/accepted} |
| Error responses | No stack traces / internals shown to user | {Yes/No} | {TC-NNN error response tests} |

> `Evidence` must reference a specific artefact (test case, scan report, task, or date). "Yes" without evidence is not accepted at mvp+ scope.

---

## 2. MVP+ — Additional Controls

| Control | Requirement | Tool/Approach |
|---|---|---|
| Certificate pinning | Pin backend API certificate/public key | {approach, e.g. react-native-ssl-pinning / Flutter http_certificate_pinning} |
| Jailbreak/root detection | Detect compromised devices, degrade/block sensitive flows | {tool, e.g. jail-monkey / flutter_jailbreak_detection} |
| Deep-link / intent validation | Validate all deep-link/universal-link params before navigation | {approach} |
| Biometric auth | Face ID / Touch ID / BiometricPrompt for sensitive actions | {approach} |
| SAST | Static analysis on every PR | {tool from constitution Quality/Security} |
| Dependency scan (SCA) | Block on critical/high CVEs | {tool, e.g. npm audit / pub outdated} |
| Secret scan | Block commit/PR containing secrets | {tool, e.g. gitleaks} |
| Audit logging | Security-relevant events logged with actor + outcome | See trigger event list below |

**Audit Trigger Events** — seed from use case Exception Paths (EP-NNN) in use-cases.md:

| Event | Source EP/FR | Log Fields Required |
|---|---|---|
| Authentication failure | {EP-NNN — auth failed} | actor_id, screen, timestamp, reason |
| Authorization denied | {EP-NNN — insufficient scope} | actor_id, resource, action, timestamp |
| Jailbreak/root detection triggered | {EP-NNN — compromised device} | device_id, platform, os_version, timestamp |
| {Additional event from EP-NNN} | {EP-NNN} | {fields} |

> Populate this table from the Exception Paths in `use-cases.md §3`. Every EP that involves auth, data access, or external system failure is a candidate audit event.

---

## 3. Full — Threat Model (STRIDE + MASVS)

| ID | Component | Threat (STRIDE category) | Description | Mitigation | Residual Risk |
|---|---|---|---|---|---|
| THR-{NNN} | {component} | Spoofing | {description} | {mitigation} | Low/Med/High |
| THR-{NNN} | {component} | Tampering | {description, e.g. APK/IPA tamper or repackaging} | {mitigation, e.g. code obfuscation + tamper detection} | Low/Med/High |
| THR-{NNN} | {component} | Repudiation | {description} | {mitigation} | Low/Med/High |
| THR-{NNN} | {component} | Information Disclosure | {description, e.g. cached PII on lost/stolen device} | {mitigation, e.g. encrypted local storage} | Low/Med/High |
| THR-{NNN} | {component} | Denial of Service | {description} | {mitigation} | Low/Med/High |
| THR-{NNN} | {component} | Elevation of Privilege | {description, e.g. jailbreak bypass} | {mitigation} | Low/Med/High |

### OWASP MASVS Reference
| MASVS Category | Applies? | Notes |
|---|---|---|
| MASVS-STORAGE | Yes/No | Local data & cache model (data-model.md §6) |
| MASVS-CRYPTO | Yes/No | Encryption at rest/in transit |
| MASVS-AUTH | Yes/No | Biometric / token refresh / session handling |
| MASVS-NETWORK | Yes/No | TLS + certificate pinning |
| MASVS-PLATFORM | Yes/No | Deep-link/intent validation, IPC |
| MASVS-CODE | Yes/No | Obfuscation, anti-tamper, anti-debug |
| MASVS-RESILIENCE | Yes/No | Jailbreak/root detection |

### DAST (for any backend APIs consumed)
| Target | Tool | Frequency |
|---|---|---|
| {API endpoint/environment} | {tool} | {e.g. every release} |

### Penetration Test Plan
| Scope | Trigger | Owner |
|---|---|---|
| {app build + backend APIs in scope} | {e.g. before go-live, annually} | {team} |

---

## 4. Regulatory / Compliance Trace

| BRD Regulation (from BRD §6) | Control(s) Implementing It | Verified By |
|---|---|---|
| {regulation, e.g. app store privacy label requirements} | {control ID(s) from sections 1-3} | {TC-NNN / ADR-NNN} |

---

## 5. Never Do (security-specific)
- Never log credentials, tokens, biometric data, or PII
- Never store secrets/API keys in plain AsyncStorage/SharedPreferences or
  source code — Keychain/Keystore + secure config injection only
- Never disable certificate pinning or TLS verification, even in mock
  profile
- Never trust client-supplied state for authorization decisions
- Never commit secrets — `.env` is gitignored, `.env.example` has
  placeholders only

---
*Pilot: section 1 only | MVP: + section 2 | Full: + sections 3-4*

## Approvals
<!-- security-sign-off: pending | reviewer: {Security Officer name from roles.yml} | date: {date} -->

| Role | Approver | Status | Date |
|---|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | | Pending | |
