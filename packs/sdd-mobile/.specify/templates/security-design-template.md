# Security Design
# Feature: {Feature Name}
> Version: 1.0 | Date: {date} | Generated at ALL scopes — depth scales
> with scope (see section markers)

---

## References
| Source | Sections / IDs Used |
|---|---|
| srd.summary.md | {sections/IDs referenced — drafted at /specify} |
| arch.summary.md | {sections/IDs referenced — refined at /plan-arch: cross-cutting concerns} |

## 1. Pilot Security Checklist (always)

| Control | Requirement | Status |
|---|---|---|
| AuthN | All API calls require auth token (NFR-{NNN}) | {Yes/No} |
| Secure local storage | Tokens/secrets in Keychain (iOS) / Keystore (Android) — never plain AsyncStorage/SharedPreferences | {Yes/No} |
| Transport | TLS enforced for all API calls — no plaintext HTTP | {Yes/No} |
| Input validation | All user input validated before use (no raw passthrough) | {Yes/No} |
| PII in logs | Never logged at any level (constitution Logging rule) | {Yes/No} |
| Secrets in bundle | No API keys/secrets baked into app bundle — secure config injection at build time | {Yes/No} |
| Dependency check | No known-critical CVEs in dependencies | {Yes/No} |
| Error responses | No stack traces / internals shown to user | {Yes/No} |

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
| Audit logging | Security-relevant events logged with actor + outcome | {events list} |

---

## 3. Full — Threat Model (STRIDE + MASVS)

| ID | Component | Threat (STRIDE category) | Description | Mitigation | Residual Risk |
|---|---|---|---|---|---|
| THR-001 | {component} | Spoofing | {description} | {mitigation} | Low/Med/High |
| THR-002 | {component} | Tampering | {description, e.g. APK/IPA tamper or repackaging} | {mitigation, e.g. code obfuscation + tamper detection} | Low/Med/High |
| THR-003 | {component} | Repudiation | {description} | {mitigation} | Low/Med/High |
| THR-004 | {component} | Information Disclosure | {description, e.g. cached PII on lost/stolen device} | {mitigation, e.g. encrypted local storage} | Low/Med/High |
| THR-005 | {component} | Denial of Service | {description} | {mitigation} | Low/Med/High |
| THR-006 | {component} | Elevation of Privilege | {description, e.g. jailbreak bypass} | {mitigation} | Low/Med/High |

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
| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
