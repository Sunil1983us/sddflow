# Constitution Amendment
# Feature: {Feature Name} | Part 2 Version Bump
> Previous Version: v{N.M} | New Version: v{N.M+1} | Date: {date: YYYY-MM-DD}
> Amended By: {agent/user} | Triggered By: CHG-{NNN} / {reason}

---

## 1. Version Change

| Field | Previous | New |
|---|---|---|
| Version | v{N.M} | v{N.M+1} |
| Amendment Type | Minor (0.X) — additive change \| Major (X.0) — breaking change |
| Approved By | — | {role} on {date: YYYY-MM-DD} |

**Minor amendment (0.X):** new field, new integration, new domain rule — does not invalidate existing spec docs
**Major amendment (X.0):** tech stack change, scope change, core principle change — may require re-run of spec docs

---

## 2. Changed Rows (Diff)

| Section | Row / Field | Previous Value | New Value | Reason |
|---|---|---|---|---|
| Tech Stack | {row name} | {old value} | {new value} | {why changed} |
| Core Principles | {principle} | — | {new principle} | {why added} |
| Domain Rules | {rule} | {old text} | {new text} | {why changed} |
| Never Do | {item} | — | {new item} | {why added} |

---

## 3. Change Impact Matrix

_(Derived from `.specify/memory/change-rules.md` Change Impact Matrix)_

| Change Type | Documents Affected | Action Required |
|---|---|---|
| {change type} | {doc list} | Re-run / Review / Note only |

**Documents requiring re-run or review:**
- [ ] {doc}.md — reason: {why impacted}
- [ ] {doc}.md — reason: {why impacted}

**Documents NOT impacted:**
- {doc}.md — reason: {why unaffected}

---

## 4. Downstream Task Impact

| CHG-NNN | Description | Estimated Lines | Affected Tasks |
|---|---|---|---|
| CHG-{NNN} | {description} | ~{N} lines | TASK-{NNN} (update), new TASK-{NNN} |

---

## 5. Approvals

| Role | Decision | Date |
|---|---|---|
| Tech Lead | Approved / Changes Requested | |
| Architect | Approved / Changes Requested | |
| Product Owner (if scope/domain change) | Approved / N/A | |
