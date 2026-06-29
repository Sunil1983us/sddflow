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
| AuthN | All endpoints require auth (NFR-{NNN}) | {Yes/No} | {TC-NNN / TASK-NNN / scan on {date}} |
| AuthZ | Role/scope check before business logic | {Yes/No} | {TC-NNN controller test + constitution rule reference} |
| Input validation | All request fields validated (no raw passthrough) | {Yes/No} | {TC-NNN validation tests} |
| Secrets | No secrets in code/config/logs — env vars or vault | {Yes/No} | {secret-scan tool run on {date}, report at {location}} |
| PII in logs | Never logged at any level (constitution Logging rule) | {Yes/No} | {log review / SAST result on {date}} |
| Transport | TLS enforced — no plaintext HTTP | {Yes/No} | {TC-NNN / infrastructure config reference} |
| Dependency check | No known-critical CVEs in dependencies | {Yes/No} | {{tool} scan on {date} — {N} critical, {N} high CVEs, all resolved/accepted} |
| Error responses | No stack traces / internals leaked to caller | {Yes/No} | {TC-NNN error response tests} |

> `Evidence` must reference a specific artefact (test case, scan report, task, or date). "Yes" without evidence is not accepted at mvp+ scope.

---

## 2. MVP+ — Additional Controls

| Control | Requirement | Tool/Approach |
|---|---|---|
| SAST | Static analysis on every PR | {tool from constitution Quality/Security} |
| Dependency scan (SCA) | Block on critical/high CVEs | {tool} |
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

---

## 3. Full — Threat Model (STRIDE)

| ID | Component | Threat (STRIDE) | Description | Mitigation | CVSS (qualitative) | Residual Risk |
|---|---|---|---|---|---|---|
| THR-{NNN} | {component} | Spoofing | {description} | {mitigation} | {Critical 9-10 / High 7-8.9 / Med 4-6.9 / Low 0-3.9 or "QA"} | Low/Med/High |
| THR-{NNN} | {component} | Tampering | {description} | {mitigation} | {CVSS} | Low/Med/High |
| THR-{NNN} | {component} | Repudiation | {description} | {mitigation} | {CVSS} | Low/Med/High |
| THR-{NNN} | {component} | Information Disclosure | {description} | {mitigation} | {CVSS} | Low/Med/High |
| THR-{NNN} | {component} | Denial of Service | {description} | {mitigation} | {CVSS} | Low/Med/High |
| THR-{NNN} | {component} | Elevation of Privilege | {description} | {mitigation} | {CVSS} | Low/Med/High |

> **CVSS column:** Use the [CVSS 3.1 calculator](https://www.first.org/cvss/calculator/3.1) for formal scoring, or use the qualitative band (Critical/High/Med/Low) and mark "QA" if formal scoring is out of scope. Any THR with CVSS ≥ 7.0 (High or Critical) must have a confirmed mitigation before /release.

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

> Verified By is filled in incrementally as later commands run:
> ADR-NNN from /plan-adr, TC-NNN from /task. Confirm no placeholders
> remain before /release §1 Pre-Release Checklist.

---

## 5. Never Do (security-specific)
- Never log credentials, tokens, card numbers, or PII
- Never trust client-supplied IDs for authorization decisions
- Never disable TLS verification, even in mock profile
- Never commit secrets — `.env` is gitignored, `.env.example` has placeholders only

---
*Pilot: section 1 only | MVP: + section 2 | Full: + sections 3-4*

## Approvals

<!-- security-sign-off: pending | reviewer: {Security Officer name from roles.yml} | date: {date} -->

| Role | Status | Date |
|---|---|---|
| Security Officer (accountable — controls adequacy) | Pending | |
| Tech Lead (consulted — implementation feasibility) | Pending | |
