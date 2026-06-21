# Use Case Specification — {Feature Name}
Feature: {manifest.project.feature}
Version: v1.0 | Date: {date}
Status: DRAFT

---

## §1 Actor Registry

| Actor ID | Name | Type | Description |
|---|---|---|---|
| ACT-001 | {Primary User} | Primary | Human actor who initiates the main flow |
| ACT-002 | {External System} | System | External automated system or service |
| ACT-003 | {Administrator} | Secondary | Human actor with administrative privileges |

**Actor Types:**
- **Primary** — initiates the use case (has a goal to achieve)
- **Secondary** — participates or is notified, does not initiate
- **System** — automated actor (external service, scheduler, other system)

---

## §2 Use Case Index

| UC-ID | Title | Actor(s) | Priority | BR Traces | FR Traces (SRD) |
|---|---|---|---|---|---|
| UC-001 | {Title} | ACT-001 | High | BR-001, BR-002 | _(filled by /specify-srd)_ |
| UC-002 | {Title} | ACT-001, ACT-002 | Medium | BR-003 | _(filled by /specify-srd)_ |

---

## §3 Use Case Details

### UC-001 — {Use Case Title}

**Actor(s):** ACT-001  
**Priority:** High  
**Trigger:** {What event or action causes this use case to start}  
**BR Traces:** BR-001, BR-002

**Preconditions:**
- {Condition 1 — must be true before this use case can begin}
- {Condition 2}

**Postconditions — Success:**
- {Verifiable system state after the use case completes successfully}

**Postconditions — Failure:**
- {Verifiable system state if the use case cannot complete}

#### Main Path (MP)

| Step | Actor | Action / Decision | System Response |
|---|---|---|---|
| 1 | ACT-001 | {Actor performs action} | {System acknowledges or responds} |
| 2 | System | — | {System processes or validates} |
| 3 | ACT-001 | {Actor performs next action} | {System confirms or displays result} |
| 4 | System | — | {System persists state, sends notification, etc.} |

#### Alternate Paths (AP)

**AP-001A — {Alternate Path Title}**
- At step 2: {Condition that causes the alternate path to activate}
- → {Alternate step 1}
- → {Alternate step 2}
- → Resume at Main Path step 3 / End with success

**AP-001B — {Alternate Path Title}**
- At step 1: {Condition}
- → {Alternative steps taken}
- → End with {outcome}

#### Exception Paths (EP)

**EP-001A — {Exception Title}**
- At step 2: {Error or failure condition}
- → System: {Error message or recovery action shown to actor}
- → Outcome: Use case aborts / resumes at step 1 / degrades gracefully

**EP-001B — {Exception Title}**
- At step 3: {Error or failure condition}
- → System: {System-level error handling, e.g. timeout, rollback, retry}
- → Outcome: {How the system fails safely and notifies the actor}

**Business Rules Applied:** BR-001, BR-002  
**Linked FR-NNN:** _(filled by /specify-srd)_  
**Non-Functional Constraints:** NFR-001

---

### UC-002 — {Use Case Title}

**Actor(s):** ACT-001, ACT-002  
**Priority:** Medium  
**Trigger:** {What initiates this use case}  
**BR Traces:** BR-003

**Preconditions:**
- {Condition}

**Postconditions — Success:**
- {State}

**Postconditions — Failure:**
- {State}

#### Main Path (MP)

| Step | Actor | Action / Decision | System Response |
|---|---|---|---|
| 1 | ACT-001 | {Action} | {Response} |
| 2 | ACT-002 | {External system action} | {System integrates response} |
| 3 | System | — | {System completes flow} |

#### Alternate Paths (AP)

**AP-002A — {Title}**
- At step 2: {Condition}
- → {Steps}
- → End with {outcome}

#### Exception Paths (EP)

**EP-002A — {Title}**
- At step 2: ACT-002 returns an error
- → System: {Handle external error, e.g. show user-friendly message, trigger retry}
- → Outcome: {Degraded mode or abort}

**Business Rules Applied:** BR-003  
**Linked FR-NNN:** _(filled by /specify-srd)_  
**Non-Functional Constraints:** NFR-002

---

## §4 Use Case Relationships

```
UC-001 ──includes──► UC-002     (UC-001 always triggers UC-002 as a sub-flow)
UC-003 ──extends──►  UC-001     (UC-003 adds optional behaviour to UC-001)
```

**includes** — UC-A always executes UC-B as part of its flow (mandatory sub-use-case)  
**extends** — UC-A adds optional or conditional behaviour to UC-B (extension point)

_(Remove this section if no UC relationships apply.)_

---

## §5 Traceability Matrix

| UC-ID | BR-NNN (BRD) | Priority | Notes |
|---|---|---|---|
| UC-001 | BR-001, BR-002 | High | Core happy path |
| UC-002 | BR-003 | Medium | Integration flow |

FR-NNN columns are populated by **/specify-srd** after this document is approved.
