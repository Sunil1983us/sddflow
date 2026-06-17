# User Stories
## Feature: Task Management
## Project: Todo API | Run by: /task

---

## Must Have

### STORY-001 — Create a Task
**As a** registered user  
**I want to** create a task with a title, optional description, due date, and priority  
**So that** I can capture and track work I need to do

**Acceptance Criteria:**
- AC-001-1: POST /tasks with valid payload returns 201 with created task (id, status=open, created_at)
- AC-001-2: Missing title returns 400 Bad Request
- AC-001-3: Past due_date returns 400 Bad Request
- AC-001-4: Unauthenticated request returns 401

**Story Points:** 3  
**Satisfies:** FR-001, FR-002

---

### STORY-002 — List My Tasks
**As a** registered user  
**I want to** see my tasks, filtered by status or priority  
**So that** I can focus on what's relevant right now

**Acceptance Criteria:**
- AC-002-1: GET /tasks returns only the current user's tasks
- AC-002-2: ?status=done returns only done tasks
- AC-002-3: ?priority=high returns only high-priority tasks
- AC-002-4: Response includes next_cursor when more pages exist
- AC-002-5: Empty result returns {data: [], next_cursor: null}

**Story Points:** 3  
**Satisfies:** FR-003, FR-004

---

### STORY-003 — Update a Task
**As a** registered user  
**I want to** update a task's title, description, due date, priority, or status  
**So that** I can keep my tasks current as work evolves

**Acceptance Criteria:**
- AC-003-1: PATCH /tasks/:id with valid payload returns 200 with updated task
- AC-003-2: Marking status=done sets completed_at timestamp
- AC-003-3: Attempting to update another user's task returns 404
- AC-003-4: Invalid status value returns 400

**Story Points:** 2  
**Satisfies:** FR-005, FR-007

---

### STORY-004 — Delete a Task
**As a** registered user  
**I want to** remove a task I no longer need  
**So that** my task list stays clean and relevant

**Acceptance Criteria:**
- AC-004-1: DELETE /tasks/:id returns 204 No Content
- AC-004-2: Deleted task no longer appears in GET /tasks
- AC-004-3: Attempting to delete another user's task returns 404

**Story Points:** 2  
**Satisfies:** FR-006, FR-007

---

## Should Have

### STORY-005 — Task Data Isolated per User
**As a** registered user  
**I want to** be certain I can never see or modify another user's tasks  
**So that** I trust my data is private

**Acceptance Criteria:**
- AC-005-1: User A's tasks never appear in User B's GET /tasks response
- AC-005-2: User A PATCH/DELETE on User B's task IDs returns 404 (not 403)
- AC-005-3: Prisma user-scope middleware test confirms filter applies to all queries

**Story Points:** 3  
**Satisfies:** FR-007

---

## Won't Have (this release)

- Task sharing / collaboration
- File attachments
- Subtasks
- Reminder email dispatch
- Archive retrieval endpoint (/tasks/archive)
