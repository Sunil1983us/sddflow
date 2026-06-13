# Analysis Report
# Feature: {Feature Name}
> Version: 1.0 | Date: {date} | Input: srd.summary.md + brd.summary.md

---

## 1. Executive Summary
{2-3 sentences: overall complexity, biggest risks, key recommendation.}
Overall Complexity: LOW | MEDIUM | HIGH

---

## 2. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-001 | {risk} | Low/Med/High | Low/Med/High/Critical | {action} |

### High/Critical Risks — Detail

#### R-{NNN}: {Risk Title}
**Description:** {what could go wrong}
**Trigger:** {what causes this}
**Impact on design:** {architectural consequence}
**Mitigation:** {concrete action}

---

## 3. Dependency Map

| Dependency | Type | Owner | Risk | Contingency |
|---|---|---|---|---|
| {system/team} | Blocking/Non-blocking | {owner} | Low/Med/High | {fallback} |

---

## 4. Complexity Assessment

| Area | Complexity | Reason | Likely SPLIT? |
|---|---|---|---|
| {feature area} | Low/Med/High | {reason} | Yes/No |

---

## 5. NFR Impact Analysis

| NFR | Requirement | Design Constraint |
|---|---|---|
| NFR-{NNN} | {requirement} | {what it forces in design} |

---

## 6. Unknowns — Spike Work Needed

| ID | Unknown | Impact | Spike? |
|---|---|---|---|
| U-001 | {what we don't know} | {consequence} | Yes/No |

---

## 7. Recommendation

**Approach:** {suggested implementation approach}

**Items to Raise in /clarify:**
- {ambiguity from R-NNN or U-NNN}

**Tasks Likely Needing SPLIT:**
- {area} — reason: {complexity or size}

---
*Generated from: srd.summary.md + brd.summary.md*
