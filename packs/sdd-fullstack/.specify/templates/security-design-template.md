# Security Design
# Service: {Service Name}
> Version: 1.0 | Date: {date} | Generated at ALL scopes — depth scales
> with scope (see section markers)
> Covers: Server-side / backend (OWASP Top 10, ASVS) AND
> Client-side / frontend (XSS, CSRF, token storage, SCA) — see subsections
>
> **Living document** — describes the whole service's security baseline,
> not one feature. Lives at `.specify/service/security-design.md`. Every
> feature after the first one extends this file (new threats, new audit
> events, new regulatory trace rows) via the living-doc-update shared
> block in `specify-doc.prompt.md` — it is never regenerated from a blank
> template.

---

## References
| Source | Sections / IDs Used |
|---|---|
| srd.summary.md | {sections/IDs referenced — drafted at /specify} |
| arch.summary.md | {sections/IDs referenced — refined at /plan-arch: cross-cutting concerns} |

## 1. Pilot Security Checklist (always)

### 1a. Server-Side (Backend)

| Control | Requirement | Status | Evidence |
|---|---|---|---|
| AuthN | All endpoints require auth (NFR-{NNN}) | {Yes/No} | {TC-NNN / TASK-NNN / scan on {date}} |
| AuthZ | Role/scope check before business logic | {Yes/No} | {TC-NNN controller test + constitution rule reference} |
| Input validation | All request fields validated (no raw passthrough) | {Yes/No} | {TC-NNN validation tests} |
| Secrets | No secrets in code/config/logs — env vars or vault | {Yes/No} | {secret-scan tool run on {date}, report at {location}} |
| PII in logs | Never logged at any level (constitution Logging rule) | {Yes/No} | {log review / SAST result on {date}} |
| Transport | TLS enforced — no plaintext HTTP | {Yes/No} | {TC-NNN / infrastructure config reference} |
| Dependency check | No known-critical CVEs in dependencies | {Yes/No} | {{tool} scan on {date} — {N} critical, {N} high CVEs, all resolved/accepted} |
| Error responses | No stack traces / internals leaked to caller | {Yes/No} | {TC-NNN error response tests} |

### 1b. Client-Side (Frontend)

| Control | Requirement | Status | Evidence |
|---|---|---|---|
| XSS | All user-supplied content escaped/sanitized before render | {Yes/No} | {TC-NNN / SAST result on {date}} |
| Token storage | Auth tokens stored per security policy (httpOnly cookie preferred over localStorage) | {Yes/No} | {TC-NNN / architecture decision reference} |
| CSRF | State-changing requests protected (CSRF token / SameSite cookies) | {Yes/No} | {TC-NNN / infrastructure config reference} |
| Transport | All API calls over TLS — no mixed content | {Yes/No} | {TC-NNN / network config reference} |
| Dependency check | No known-critical CVEs in npm dependencies | {Yes/No} | {{tool} scan on {date} — {N} critical, {N} high CVEs, all resolved/accepted} |
| Error responses | No stack traces / internals shown to user | {Yes/No} | {TC-NNN error response tests} |

> `Evidence` must reference a specific artefact (test case, scan report, task, or date). "Yes" without evidence is not accepted at mvp+ scope.

---

## 2. MVP+ — Additional Controls

### 2a. Server-Side (Backend)

| Control | Requirement | Tool/Approach |
|---|---|---|
| SAST | Static analysis on every PR | {tool from constitution Quality/Security} |
| Dependency scan (SCA) | Block on critical/high CVEs | {tool, e.g. OWASP dependency-check} |
| Secret scan | Block commit/PR containing secrets | {tool, e.g. gitleaks} |
| Rate limiting | Per-client throttling on public endpoints | {approach} |
| Audit logging | Security-relevant events logged with actor + outcome | See trigger event list below |

**Audit Trigger Events** — seed from use case Exception Paths (EP-NNN) in use-cases.md:

| Event | Source EP/FR | Log Fields Required |
|---|---|---|
| Authentication failure | {EP-NNN — auth failed} | actor_id, endpoint, timestamp, reason |
| Authorization denied | {EP-NNN — insufficient scope} | actor_id, resource, action, timestamp |
| Input validation failure (security-relevant fields) | {EP-NNN — invalid input} | actor_id, field_name, timestamp |
| {Additional event from EP-NNN} | {EP-NNN} | {fields} |

> Populate this table from the Exception Paths in `use-cases.md §3`. Every EP that involves auth, data access, or external system failure is a candidate audit event.

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
