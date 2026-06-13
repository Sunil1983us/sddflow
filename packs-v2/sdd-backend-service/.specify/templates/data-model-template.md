# Data Model
# Feature: {Feature Name}
> Version: 1.0 | Date: {date} | Scope: MVP+
> Drafted at: /specify (Input: srd.summary.md)
> Refined at: /plan-arch (Input: + arch.summary.md — entity design)

---

## 1. Entity Relationship
```mermaid
erDiagram
    {ENTITY_A} {
        UUID id PK
        VARCHAR status
        DECIMAL amount
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    {ENTITY_B} {
        UUID id PK
        UUID entity_a_id FK
        VARCHAR field_1
        TIMESTAMP created_at
    }
    {ENTITY_A} ||--o{ {ENTITY_B} : "has"
```

## 2. Tables

### {entity_a}
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | UUID | NOT NULL | PK — generated |
| status | VARCHAR(30) | NOT NULL | Current status |
| amount | DECIMAL(19,4) | NULL | Monetary — 4dp always |
| currency | VARCHAR(3) | NULL | With amount always |
| created_at | TIMESTAMP | NOT NULL | UTC |
| updated_at | TIMESTAMP | NOT NULL | UTC |

**Indexes:**
- `idx_{table}_status` ON {table}(status)
- `idx_{table}_{field}` ON {table}({field})

### {entity_b}
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | UUID | NOT NULL | PK |
| entity_a_id | UUID | NOT NULL | FK → {entity_a}.id |
| {field} | VARCHAR({n}) | NOT NULL | |
| created_at | TIMESTAMP | NOT NULL | UTC |

## 3. Enums
```
{EntityStatus}:
  {STATE_1}, {STATE_2}, {STATE_3}, {TERMINAL}
```

## 4. Flyway Migration Scripts
| Script | Purpose |
|---|---|
| V001__{desc}.sql | Create {entity_a} table + indexes |
| V002__{desc}.sql | Create {entity_b} table + indexes |

## 5. Data Dictionary
| Field | Business Meaning |
|---|---|
| id | Unique system identifier — never exposed externally |
| status | Current lifecycle state of the entity |
| amount | Monetary value — always stored with currency |
| {field} | {business meaning} |

## 6. Data Classification & Privacy (SEC-7)

| Table.Column | Classification | PII? | Encryption | Retention | Masking in Logs |
|---|---|---|---|---|---|
| {entity_a}.{field} | Public/Internal/Confidential/Restricted | Yes/No | At-rest: {alg} / In-transit: TLS | {N days/years or "indefinite"} | {mask pattern or "N/A"} |
| {entity_b}.{field} | {classification} | Yes/No | {approach} | {policy} | {pattern} |

**Classification key:**
- Public — no restriction
- Internal — employees/contractors only
- Confidential — need-to-know (e.g. financial, business-sensitive)
- Restricted — regulated PII/PCI/PHI — encryption + access audit mandatory

Any column marked PII = Yes must:
- Never appear in logs (constitution Part 1 — Logging)
- Be covered by a retention/deletion policy (BRD §6 regulatory trace)
- Be listed in security-design.md §4 Regulatory/Compliance Trace

---
*Drafted from: srd.summary.md (at /specify) | Refined from: arch.summary.md (at /plan-arch)*
