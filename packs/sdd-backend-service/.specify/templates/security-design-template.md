# Security Design
# Service: {Service Name}
> Version: 1.0 | Date: {date: YYYY-MM-DD} | Generated at ALL scopes — depth scales
> with scope (see section markers)
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

| Control | Requirement | Status | Evidence |
|---|---|---|---|
| AuthN | All endpoints require auth (NFR-{NNN}) | {Yes/No} | {TC-NNN / TASK-NNN / scan on {date: YYYY-MM-DD}} |
| AuthZ | Role/scope check before business logic | {Yes/No} | {TC-NNN controller test + constitution rule reference} |
| Input validation | All request fields validated (no raw passthrough) | {Yes/No} | {TC-NNN validation tests} |
| Secrets | No secrets in code/config/logs — env vars or vault | {Yes/No} | {secret-scan tool run on {date: YYYY-MM-DD}, report at {location}} |
| PII in logs | Never logged at any level (constitution Logging rule) | {Yes/No} | {log review / SAST result on {date: YYYY-MM-DD}} |
| Transport | TLS enforced — no plaintext HTTP | {Yes/No} | {TC-NNN / infrastructure config reference} |
| Dependency check | No known-critical CVEs in dependencies | {Yes/No} | {{tool} scan on {date: YYYY-MM-DD} — {N} critical, {N} high CVEs, all resolved/accepted} |
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

**OWASP Top 10 Controls Mapping** — for each category, state the concrete control (or `N/A — {why}` if genuinely inapplicable):

| OWASP Top 10 (2021) | Applies? | Control |
|---|---|---|
| A01 Broken Access Control | Yes/No | {control, e.g. per-request authorization check on every endpoint} |
| A02 Cryptographic Failures | Yes/No | {control, e.g. TLS 1.2+, encrypted at rest} |
| A03 Injection | Yes/No | {control, e.g. parameterized queries, input validation} |
| A04 Insecure Design | Yes/No | {control} |
| A05 Security Misconfiguration | Yes/No | {control} |
| A06 Vulnerable and Outdated Components | Yes/No | {control — ties to Dependency scan row above} |
| A07 Identification and Authentication Failures | Yes/No | {control} |
| A08 Software and Data Integrity Failures | Yes/No | {control} |
| A09 Security Logging and Monitoring Failures | Yes/No | {control — ties to Audit logging row above} |
| A10 Server-Side Request Forgery (SSRF) | Yes/No | {control} |

---

## 3. Threat Model (STRIDE) — mvp+

> STRIDE threat enumeration + DREAD scoring applies at mvp and full scope. DAST and the Penetration Test Plan below are full scope only — skip those two subsections entirely at mvp.

| ID | Component | Threat (STRIDE category) | Description | Mitigation | DREAD (sum, /15) | Residual Risk |
|---|---|---|---|---|---|---|
| THR-{NNN} | {component} | Spoofing | {description} | {mitigation} | {sum 5-15, e.g. 8 — High} | Low/Med/High |
| THR-{NNN} | {component} | Tampering | {description} | {mitigation} | {DREAD} | Low/Med/High |
| THR-{NNN} | {component} | Repudiation | {description} | {mitigation} | {DREAD} | Low/Med/High |
| THR-{NNN} | {component} | Information Disclosure | {description} | {mitigation} | {DREAD} | Low/Med/High |
| THR-{NNN} | {component} | Denial of Service | {description} | {mitigation} | {DREAD} | Low/Med/High |
| THR-{NNN} | {component} | Elevation of Privilege | {description} | {mitigation} | {DREAD} | Low/Med/High |

> **DREAD column:** sum of Damage + Reproducibility + Exploitability + Affected users + Discoverability, each rated 1 (Low) / 2 (Medium) / 3 (High) per specify-doc.prompt.md's rubric (total range 5-15; bands: ≥10 Critical, 7-9 High, 4-6 Medium, 1-3 Low). Any THR scoring High or Critical must have a confirmed mitigation before `/plan-design` — earlier than a `/release`-time gate would catch it, so architecture work never builds on top of an unmitigated threat.

### DAST (full scope only)

| Target | Tool | Frequency |
|---|---|---|
| {endpoint/environment} | {tool} | {e.g. every release} |

### Penetration Test Plan (full scope only)

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
*Pilot: section 1 only | MVP: + section 2 + §3 STRIDE/DREAD threat table | Full: + §3 DAST/Pen Test + section 4*

## Approvals

<!-- security-sign-off: pending | reviewer: {Security Officer name from roles.yml} | date: {date: YYYY-MM-DD} -->

| Role | Approver | Status | Date |
|---|---|---|---|
| Security Officer (accountable — controls adequacy) | | Pending | |
| Tech Lead (consulted — implementation feasibility) | | Pending | |

## Version History

| Version | Date | Feature | Change | CR |
|---|---|---|---|---|
| 1.0 | {date: YYYY-MM-DD} | {feature that first created this document} | Initial security baseline | — |
