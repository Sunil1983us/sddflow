# Security Design — Task Management
# Feature: task-management
> Version: 1.0 | Status: Approved | Date: 2026-05-13 | Author: Ava (Architect)
> Scope: pilot — §1 Threat Assessment only (§2–4 are generated at mvp/full scope)

---

## References
| Source | Sections / IDs Used |
|---|---|
| brd.md | BR-004 (user isolation), BR-006 |
| srd.md | FR-007 (strict user-scoping), NFR rows |
| use-cases.md | EP-1-3, EP-2-1, EP-3-1, EP-4-1 (auth/ownership exception paths) |

---

## 1. Threat Assessment

### 1.1 Assets

| Asset | Sensitivity | Why it matters |
|---|---|---|
| User task data (title, description, due dates) | Personal | May contain private plans, names, health/work details |
| JWT session tokens | Secret | Full account takeover if leaked |
| User ↔ task ownership mapping | Integrity-critical | Basis of the isolation guarantee (BR-004) |

### 1.2 Threats and Mitigations

| ID | Threat | Vector | Mitigation | Trace |
|---|---|---|---|---|
| TH-001 | Cross-user data access (horizontal privilege escalation) | Guessing/enumerating task ids in PATCH/DELETE/GET | Every query is scoped by `user_id` from the verified JWT; foreign ids return 404 (not 403) to prevent id enumeration | FR-007, EP-3-1, EP-4-1 |
| TH-002 | Unauthenticated access | Missing/forged/expired JWT | JWT signature + expiry verified on every request; 401 on failure; no anonymous routes except health check | EP-1-3, EP-2-2 |
| TH-003 | Injection via task fields | SQL/NoSQL injection through title/description | Parameterised queries only (no string-built SQL); input length limits (200/2000 chars) enforced before persistence | FR-001 |
| TH-004 | Data exposure through logs | Task titles/descriptions written to application logs | Log request metadata only (user id, route, status); never log request bodies | NFR (privacy) |
| TH-005 | Resource exhaustion | Unbounded list requests / rapid task creation | Pagination hard-capped at 100; rate limiting at the gateway (per-user) | FR-004 |
| TH-006 | Stale-data retention beyond policy | Done tasks kept forever | Retention job hard-deletes done tasks after 90 days (UC-005) | BR-005, FR-008 |

### 1.3 Out of Scope at Pilot

- §2 OWASP ASVS mapping, §3 STRIDE-per-component, §4 DAST plan — generated when
  the project upgrades to `mvp` or `full` scope (`/specify-doc security` re-run).
- Multi-factor authentication, anomaly detection — not required for pilot.

---

## Approvals

| Role | Status | Date |
|---|---|---|
| Security Officer | Approved | 2026-05-13 |
| Tech Lead | Approved | 2026-05-13 |

## Version History

| Version | Date | Command | Change | Approved by |
|---|---|---|---|---|
| 1.0 | 2026-05-13 | /specify-doc security | Initial threat assessment (§1, pilot scope) | Security Officer |
