# Spec Quality Checklist
# Feature: {Feature Name}
> Version: 1.0 | Date: {date} | Scope: {pilot | mvp | full}

---

## Summary
- Total items: {N}
- Open: {N}
- Resolved: {N}
- Blocking /validate: {N} (CRITICAL)

---

## CHK-NNN Items

| ID | Dimension | Severity | Location | Finding | Action Required |
|---|---|---|---|---|---|
| CHK-{NNN} | {Clarity\|Completeness\|Consistency\|Measurability} | CRITICAL\|HIGH\|MEDIUM\|LOW | {doc + section} | {what is wrong} | {what to fix} |

### Severity Guide
- **CRITICAL** — blocks /validate: no measurable NFR target; FR has no acceptance scenario; [NEEDS CLARIFICATION] not resolved
- **HIGH** — should fix before /validate: vague adjective without a number; FR missing a success condition; UC with < 2 acceptance scenarios
- **MEDIUM** — fix before /plan-design: terminology inconsistency; out-of-scope item not listed; assumption not marked
- **LOW** — improve before /task: wording improvement; minor redundancy

### Dimension Guide
- **Clarity** — no vague adjectives without measurable values ("fast", "scalable", "secure")
- **Completeness** — every FR has a UC, every UC has ≥ 2 acceptance scenarios, Out of Scope section exists
- **Consistency** — same concept named the same way in brd.md and srd.md; no duplicate FRs
- **Measurability** — every NFR has a numeric threshold (ms, %, TPS, uptime %)

---

## Status
[ ] All CRITICAL items resolved — /validate may proceed
[ ] All HIGH items resolved (recommended before /validate)
