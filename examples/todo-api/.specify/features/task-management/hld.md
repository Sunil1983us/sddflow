# High Level Design
## Feature: Task Management
## Project: Todo API | Run by: /plan-hld

---

## Component Diagram

```mermaid
graph TD
    Client["Web Client (React)"]
    GW["API Gateway (Kong)\nRate limit: 300 req/min/user"]
    Auth["Auth Middleware\n(JWT RS256 verify)"]
    Scope["User-Scope Middleware\n(AsyncLocalStorage user_id)"]
    Router["Tasks Router\n(Express)"]
    Service["TaskService\n(domain logic)"]
    Repo["TaskRepository\n(Prisma + user-scope filter)"]
    DB[("PostgreSQL 16\ntasks table")]
    Purge["Purge Cron\n(platform team)"]

    Client -->|HTTPS| GW
    GW -->|forward with X-User-Id| Auth
    Auth --> Scope
    Scope --> Router
    Router --> Service
    Service --> Repo
    Repo -->|SQL + WHERE user_id| DB
    Purge -->|DELETE done tasks > 90d| DB
```

---

## Request Flow — POST /tasks

```mermaid
sequenceDiagram
    participant C as Client
    participant GW as Gateway
    participant M as Auth+Scope Middleware
    participant R as Tasks Router
    participant S as TaskService
    participant DB as PostgreSQL

    C->>GW: POST /tasks {title, priority, due_date}
    GW->>M: forward + inject X-User-Id header
    M->>M: verify JWT, set user_id in AsyncLocalStorage
    M->>R: next()
    R->>R: validate body with Zod schema
    R->>S: createTask({title, priority, due_date})
    S->>S: validate due_date not in past
    S->>DB: INSERT INTO tasks (user_id from ALS, ...)
    DB-->>S: task row
    S-->>R: Task domain object
    R-->>C: 201 Created {id, title, status, created_at, ...}
```

---

## Data Model

```mermaid
erDiagram
    USERS {
        uuid id PK
        string email
        timestamp created_at
    }
    TASKS {
        uuid id PK
        uuid user_id FK
        string title
        text description
        timestamp due_date
        enum priority
        enum status
        timestamp completed_at
        boolean archived
        timestamp created_at
        timestamp updated_at
    }
    USERS ||--o{ TASKS : "owns"
```

---

## API Surface

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /tasks | JWT | Create task → 201 |
| GET | /tasks | JWT | List own tasks (filtered, paginated) → 200 |
| PATCH | /tasks/:id | JWT | Update task fields → 200 |
| DELETE | /tasks/:id | JWT | Soft-delete task → 204 |

---

## Key Indexes

```sql
-- Primary lookup: user's tasks in reverse chronological order
CREATE INDEX idx_tasks_user_created ON tasks (user_id, created_at DESC)
  WHERE archived = false;

-- Filter by status
CREATE INDEX idx_tasks_user_status ON tasks (user_id, status)
  WHERE archived = false;

-- Purge job
CREATE INDEX idx_tasks_purge ON tasks (status, completed_at)
  WHERE status = 'done' AND archived = false;
```
