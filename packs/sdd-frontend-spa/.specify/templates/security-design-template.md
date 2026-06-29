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

| Control | Requirement | Status | Evidence |
|---|---|---|---|
| AuthN | All authenticated routes require a valid session/token (NFR-{NNN}) | {Yes/No} | {TC-NNN / TASK-NNN / scan on {date}} |
| Token storage | Auth token stored per the chosen trade-off — httpOnly+Secure cookie (preferred) or in-memory; never `localStorage`/`sessionStorage` for long-lived tokens | {Yes/No} | {TC-NNN / architecture decision reference} |
| XSS / DOM-XSS | No raw HTML injection (`innerHTML`, `v-html`, `dangerouslySetInnerHTML`) without sanitization | {Yes/No} | {TC-NNN / SAST result on {date}} |
| CSP | `Content-Security-Policy` header set — no `unsafe-inline`/`unsafe-eval` for scripts | {Yes/No} | {TC-NNN / infrastructure config reference} |
| Input validation | All user input validated/escaped before render or submission | {Yes/No} | {TC-NNN validation tests} |
| Secrets | No API keys/secrets in source, `.env` committed, or baked into the JS bundle | {Yes/No} | {secret-scan tool run on {date}, report at {location}} |
| PII in logs | Never logged to console or error tracker at any level (constitution Logging rule) | {Yes/No} | {log review / SAST result on {date}} |
| Transport | TLS enforced for all API calls — no plaintext HTTP, no mixed content | {Yes/No} | {TC-NNN / infrastructure config reference} |
| Dependency check | No known-critical CVEs in `package.json` dependencies | {Yes/No} | {{tool} scan on {date} — {N} critical, {N} high CVEs, all resolved/accepted} |
| Error responses | No stack traces / internals shown to the user | {Yes/No} | {TC-NNN error response tests} |

> `Evidence` must reference a specific artefact (test case, scan report, task, or date). "Yes" without evidence is not accepted at mvp+ scope.

---

## 2. MVP+ — Additional Controls

| Control | Requirement | Tool/Approach |
|---|---|---|
| CSRF | If using cookie-based auth: CSRF token on state-changing requests, `SameSite=Strict/Lax` cookies | {approach — N/A if token-in-header only} |
| Clickjacking | `X-Frame-Options: DENY` and/or CSP `frame-ancestors 'none'` | {confirm header set — see docker-config-template nginx.conf} |
| Third-party scripts | All third-party `<script>`/`<link>` tags vetted; Subresource Integrity (`integrity` + `crossorigin`) on each | {list of third-party scripts + SRI status} |
| SAST | Static analysis on every PR | {tool from constitution Quality/Security} |
| Dependency scan (SCA) | `npm audit` (or equivalent) — block on critical/high CVEs | {tool} |
| Secret scan | Block commit/PR containing secrets | {tool, e.g. gitleaks} |
| Audit logging | Security-relevant client events (login, permission denial) sent to backend/RUM with actor + outcome | {events list} |

---

## 3. Full — Threat Model (STRIDE)

| ID | Component | Threat (STRIDE category) | Description | Mitigation | Residual Risk |
|---|---|---|---|---|---|
| THR-{NNN} | {component} | Spoofing | {description, e.g. token theft via XSS} | {mitigation, e.g. httpOnly cookie + CSP} | Low/Med/High |
| THR-{NNN} | {component} | Tampering | {description, e.g. tampered client-side state/localStorage} | {mitigation, e.g. server-side re-validation, SEC-7 classification} | Low/Med/High |
| THR-{NNN} | {component} | Repudiation | {description} | {mitigation} | Low/Med/High |
| THR-{NNN} | {component} | Information Disclosure | {description, e.g. sensitive data cached in browser storage} | {mitigation, e.g. data-model.md §6 classification — no sensitive data in localStorage} | Low/Med/High |
| THR-{NNN} | {component} | Denial of Service | {description, e.g. third-party script outage blocking render} | {mitigation, e.g. resilience.md error boundary + async loading} | Low/Med/High |
| THR-{NNN} | {component} | Elevation of Privilege | {description, e.g. client-side-only route guard bypass} | {mitigation, e.g. server-side authZ enforcement — never trust client routing} | Low/Med/High |

### DAST
| Target | Tool | Frequency |
|---|---|---|
| {staging URL} | {tool, e.g. OWASP ZAP} | {e.g. every release} |

### Penetration Test Plan
| Scope | Trigger | Owner |
|---|---|---|
| {in-scope app + consumed APIs} | {e.g. before go-live, annually} | {team} |

---

## 4. Regulatory / Compliance Trace

| BRD Regulation (from BRD §6) | Control(s) Implementing It | Verified By |
|---|---|---|
| {regulation, e.g. cookie consent / accessibility law} | {control ID(s) from sections 1-3} | {TC-NNN / ADR-NNN} |

---

## 5. Never Do (security-specific)
- Never log credentials, tokens, or PII to console or error tracker
- Never store long-lived auth tokens in `localStorage`/`sessionStorage` —
  use httpOnly+Secure cookies or in-memory storage
- Never render unsanitized user input via `innerHTML`/`v-html`/
  `dangerouslySetInnerHTML`
- Never trust client-side route guards as the sole authorization
  control — server must re-enforce
- Never add a third-party `<script>` without SRI (`integrity` +
  `crossorigin`) and a documented vetting decision
- Never commit secrets — `.env` is gitignored, `.env.example` has
  placeholders only; no API keys baked into the bundle

---
*Pilot: section 1 only | MVP: + section 2 | Full: + sections 3-4*

## Approvals
<!-- security-sign-off: pending | reviewer: {Security Officer name from roles.yml} | date: {date} -->

| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
