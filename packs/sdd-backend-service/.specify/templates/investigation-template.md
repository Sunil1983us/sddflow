# Investigation Cases
# Feature: {Feature Name}
> Version: 1.0 | Date: {date}
> Scope: Full only — skip for pilot + mvp

---

## References

| Source | Sections / IDs Used |
|---|---|
| srd.summary.md | {sections/IDs referenced — drafted at /specify} |
| arch.summary.md | {sections/IDs referenced — refined at /plan-arch: flows} |

## 1. Investigation Triggers

| ID | Trigger | Severity | SLA |
|---|---|---|---|
| INV-{NNN} | {what causes this} | High | {time to resolve} |
| INV-{NNN} | {what causes this} | Medium | {time to resolve} |

---

## 2. Investigation Case: INV-{NNN} — {Title}

- **Trigger:** {exact condition that triggers investigation}
- **Detected by:** {log event / monitor / alert}
- **Impact:** {what is affected}

**Resolution Steps:**
1. {step 1}
2. {step 2}
3. {step 3}

**Data to Collect:**
- {resource_id}
- {timestamp range}
- {relevant log events}

- **Resolution:** {how to close the case}
- **Prevention:** {what to change to avoid recurrence}

---

## 3. Investigation Case: INV-{NNN} — {Title}

- **Trigger:** {condition}
- **Detected by:** {method}
- **Impact:** {impact}

**Resolution Steps:**
1. {step}
2. {step}

**Resolution:** {how to close}

---

## 4. Investigation Log Schema

```json
{
  "investigationId": "UUID",
  "trigger": "INV-{NNN}",
  "resourceId": "UUID",
  "detectedAt": "ISO 8601",
  "resolvedAt": "ISO 8601 or null",
  "status": "OPEN | IN_PROGRESS | RESOLVED",
  "notes": "string"
}
```

---

## 5. Alerts → Investigation Mapping

| Alert | Triggers | Auto-create? |
|---|---|---|
| {alert name} | INV-{NNN} | Yes/No |

---

## Approvals

| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
