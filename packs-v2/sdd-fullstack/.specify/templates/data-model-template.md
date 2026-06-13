# Data Model
# Feature: {Feature Name}
> Version: 1.0 | Date: {date}

---

## References
| Source | Sections / IDs Used |
|---|---|
| arch.summary.md | {sections/IDs referenced} |

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

---

## Approvals
| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
