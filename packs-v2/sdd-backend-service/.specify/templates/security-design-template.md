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
| AuthN | All endpoints require auth (NFR-{NNN}) | {Yes/No} |
| AuthZ | Role/scope check before business logic | {Yes/No} |
| Input validation | All request fields validated (no raw passthrough) | {Yes/No} |
| Secrets | No secrets in code/config/logs — env vars or vault | {Yes/No} |
| PII in logs | Never logged at any level (constitution Logging rule) | {Yes/No} |
| Transport | TLS enforced — no plaintext HTTP | {Yes/No} |
| Dependency check | No known-critical CVEs in dependencies | {Yes/No} |
| Error responses | No stack traces / internals leaked to caller | {Yes/No} |

---

## 2. MVP+ — Additional Controls

| Control | Requirement | Tool/Approach |
|---|---|---|
| SAST | Static analysis on every PR | {tool from constitution Quality/Security} |
| Dependency scan (SCA) | Block on critical/high CVEs | {tool} |
| Secret scan | Block commit/PR containing secrets | {tool, e.g. gitleaks} |
| Rate limiting | Per-client throttling on public endpoints | {approach} |
| Audit logging | Security-relevant events logged with actor + outcome | {events list} |

---

## 3. Full — Threat Model (STRIDE)

| ID | Component | Threat (STRIDE category) | Description | Mitigation | Residual Risk |
|---|---|---|---|---|---|
| THR-001 | {component} | Spoofing | {description} | {mitigation} | Low/Med/High |
| THR-002 | {component} | Tampering | {description} | {mitigation} | Low/Med/High |
| THR-003 | {component} | Repudiation | {description} | {mitigation} | Low/Med/High |
| THR-004 | {component} | Information Disclosure | {description} | {mitigation} | Low/Med/High |
| THR-005 | {component} | Denial of Service | {description} | {mitigation} | Low/Med/High |
| THR-006 | {component} | Elevation of Privilege | {description} | {mitigation} | Low/Med/High |

### DAST
| Target | Tool | Frequency |
|---|---|---|
| {endpoint/environment} | {tool} | {e.g. every release} |

### Penetration Test Plan
| Scope | Trigger | Owner |
|---|---|---|
| {in-scope systems} | {e.g. before go-live, annually} | {team} |

---

## 4. Regulatory / Compliance Trace

| BRD Regulation (from BRD §6) | Control(s) Implementing It | Verified By |
|---|---|---|
| {regulation} | {control ID(s) from sections 1-3} | {TC-NNN / ADR-NNN} |

---

## 5. Never Do (security-specific)
- Never log credentials, tokens, card numbers, or PII
- Never trust client-supplied IDs for authorization decisions
- Never disable TLS verification, even in mock profile
- Never commit secrets — `.env` is gitignored, `.env.example` has placeholders only

---
*Pilot: section 1 only | MVP: + section 2 | Full: + sections 3-4*

## Approvals
| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
