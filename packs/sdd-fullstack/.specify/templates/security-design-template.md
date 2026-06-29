# Security Design
# Feature: {Feature Name}
> Version: 1.0 | Date: {date} | Generated at ALL scopes — depth scales
> with scope (see section markers)
> Covers: Server-side / backend (OWASP Top 10, ASVS) AND
> Client-side / frontend (XSS, CSRF, token storage, SCA) — see subsections

---

## References
| Source | Sections / IDs Used |
|---|---|
| srd.summary.md | {sections/IDs referenced — drafted at /specify} |
| arch.summary.md | {sections/IDs referenced — refined at /plan-arch: cross-cutting concerns} |

## 1. Pilot Security Checklist (always)

### 1a. Server-Side (Backend)

| Control | Requirement | Status |
|---|---|---|
| AuthN | All endpoints require auth (NFR-{NNN}) | {Yes/No} |
| AuthZ | Role/scope check before business logic | {Yes/No} |
| Input validation | All request fields validated (no raw passthrough) | {Yes/No} |
| Secrets | No secrets in code/config/logs — env vars or vault | {Yes/No} |
| PII in logs | Never logged at any level (constitution Logging rule) | {Yes/No} |
| Transport | TLS enforced — no plaintext HTTP | {Yes/No} |
| Dependency check | No known-critical CVEs in dependencies | {Yes/No} |
| Error responses | No stack traces / internals leaked to caller | {Yes/No} |

### 1b. Client-Side (Frontend)

| Control | Requirement | Status |
|---|---|---|
| XSS | All user-supplied content escaped/sanitized before render | {Yes/No} |
| Token storage | Auth tokens stored per security policy (httpOnly cookie preferred over localStorage) | {Yes/No} |
| CSRF | State-changing requests protected (CSRF token / SameSite cookies) | {Yes/No} |
| Transport | All API calls over TLS — no mixed content | {Yes/No} |
| Dependency check | No known-critical CVEs in npm dependencies | {Yes/No} |
| Error responses | No stack traces / internals shown to user | {Yes/No} |

---

## 2. MVP+ — Additional Controls

### 2a. Server-Side (Backend)

| Control | Requirement | Tool/Approach |
|---|---|---|
| SAST | Static analysis on every PR | {tool from constitution Quality/Security} |
| Dependency scan (SCA) | Block on critical/high CVEs | {tool, e.g. OWASP dependency-check} |
| Secret scan | Block commit/PR containing secrets | {tool, e.g. gitleaks} |
| Rate limiting | Per-client throttling on public endpoints | {approach} |
| Audit logging | Security-relevant events logged with actor + outcome | {events list} |

### 2b. Client-Side (Frontend)

| Control | Requirement | Tool/Approach |
|---|---|---|
| CSP | Content-Security-Policy header restricts script/style/connect sources | {policy summary} |
| SRI | Subresource Integrity hashes on third-party scripts/CDN assets | {Yes/No + tool} |
| Dependency scan (SCA) | `npm audit` (or equivalent) blocks on critical/high CVEs | {tool} |
| Secret scan | No API keys/secrets in frontend bundle | {tool, e.g. gitleaks} |
| Session timeout | Idle session expiry + re-auth prompt | {approach} |

---

## 3. Full — Threat Model (STRIDE)

### 3a. Server-Side Threats

| ID | Component | Threat (STRIDE category) | Description | Mitigation | Residual Risk |
|---|---|---|---|---|---|
| THR-{NNN} | {backend component} | Spoofing | {description} | {mitigation} | Low/Med/High |
| THR-{NNN} | {backend component} | Tampering | {description} | {mitigation} | Low/Med/High |
| THR-{NNN} | {backend component} | Repudiation | {description} | {mitigation} | Low/Med/High |
| THR-{NNN} | {backend component} | Information Disclosure | {description} | {mitigation} | Low/Med/High |
| THR-{NNN} | {backend component} | Denial of Service | {description} | {mitigation} | Low/Med/High |
| THR-{NNN} | {backend component} | Elevation of Privilege | {description} | {mitigation} | Low/Med/High |

### 3b. Client-Side Threats

| ID | Component | Threat (STRIDE category) | Description | Mitigation | Residual Risk |
|---|---|---|---|---|---|
| THR-{NNN} | {frontend component} | Spoofing | {e.g. phishing via UI clone} | {mitigation} | Low/Med/High |
| THR-{NNN} | {frontend component} | Tampering | {e.g. DOM/storage tampering} | {mitigation} | Low/Med/High |
| THR-{NNN} | {frontend component} | Information Disclosure | {e.g. token leak via XSS} | {mitigation, CSP + sanitization} | Low/Med/High |
| THR-{NNN} | {frontend component} | Elevation of Privilege | {e.g. client-side route guard bypass} | {server-side authZ as source of truth} | Low/Med/High |

### DAST
| Target | Tool | Frequency |
|---|---|---|
| {backend endpoint/environment} | {tool} | {e.g. every release} |
| {frontend deployed app} | {tool, e.g. OWASP ZAP against staging} | {e.g. every release} |

### Penetration Test Plan
| Scope | Trigger | Owner |
|---|---|---|
| {in-scope systems — backend + frontend} | {e.g. before go-live, annually} | {team} |

---

## 4. Regulatory / Compliance Trace

| BRD Regulation (from BRD §6) | Control(s) Implementing It | Verified By |
|---|---|---|
| {regulation} | {control ID(s) from sections 1-3, backend and/or frontend} | {TC-NNN / ADR-NNN} |

---

## 5. Never Do (security-specific)
- Never log credentials, tokens, card numbers, or PII (backend or frontend
  console/error-tracking logs)
- Never trust client-supplied IDs for authorization decisions
- Never disable TLS verification, even in mock profile
- Never commit secrets — `.env` is gitignored, `.env.example` has placeholders only
- Never store auth tokens in localStorage/sessionStorage if httpOnly
  cookies are an option (frontend)
- Never render unsanitized user input as HTML (frontend XSS)

---
*Pilot: sections 1a+1b only | MVP: + sections 2a+2b | Full: + sections 3-4 (both subsections)*

## Approvals
<!-- security-sign-off: pending | reviewer: {Security Officer name from roles.yml} | date: {date} -->

| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
