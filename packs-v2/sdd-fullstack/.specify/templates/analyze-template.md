# Analysis Report — {Feature Name}
> Version: 1.0 | Date: {date}
> Input: srd.summary.md + brd.summary.md

---

## 1. Executive Summary
{2-3 sentences: overall complexity rating, biggest risks, key recommendation}

Overall Complexity: LOW | MEDIUM | HIGH | CRITICAL

---

## 2. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-001 | {risk description} | Low/Med/High | Low/Med/High/Critical | {mitigation} |

### High/Critical Risks — Detail

#### R-{NNN}: {Risk Title}
**Description:** {what could go wrong}
**Trigger:** {what causes this risk}
**Impact on design:** {how this affects architecture/implementation}
**Mitigation:** {concrete action to reduce risk}
**Owner:** {team/person responsible}

---

## 3. Dependency Map

### Internal Dependencies
| Dependency | Type | Risk | Notes |
|---|---|---|---|
| {service/component} | Hard/Soft | Low/Med/High | {notes} |

### External Dependencies
| System | Owner | Dependency Type | Risk | Contingency |
|---|---|---|---|---|
| {system} | {team} | Blocking/Non-blocking | Low/Med/High | {fallback} |

### Timeline Dependencies
| Item | Blocks | Due | Status |
|---|---|---|---|
| {item} | {what it blocks} | {date} | {status} |

---

## 4. Complexity Assessment

### By Feature Area
| Area | Complexity | Reason |
|---|---|---|
| {feature area} | Low/Med/High | {reason} |

### By FR
| FR | Complexity | Design Impact |
|---|---|---|
| FR-001 | Low/Med/High | {impact on design} |

### Technical Complexity Hotspots
{Areas that need extra design attention or spike work before implementation}

---

## 5. NFR Impact Analysis

| NFR | Requirement | Design Constraint | Risk |
|---|---|---|---|
| NFR-001 | {requirement} | {what it forces in design} | Low/Med/High |

### Critical NFR Decisions
{NFRs that fundamentally shape the architecture — describe the design
 constraints they impose}

---

## 6. Assumptions Register

| ID | Assumption | If Wrong | Probability |
|---|---|---|---|
| A-001 | {what we are assuming} | {impact if false} | Low/Med/High |

---

## 7. Unknowns and Spikes Needed

| ID | Unknown | Impact | Spike Required? |
|---|---|---|---|
| U-001 | {what we don't know yet} | {impact on design} | Yes/No |

---

## 8. Recommendation

### Approach
{Given the analysis — recommended implementation approach}

### High-Risk Items to Address in CLARIFY
{List the items from this analysis that must be clarified before design}
{These feed directly into the CLARIFY verb}

### Suggested Task Complexity Flags
{Areas where tasks will likely need SPLIT treatment}
{Agent uses this during TASK verb to pre-flag complex tasks}

---

## Summary
> Lines: {N} / {SUMMARY_MAX_LINES}

## What
{1-2 sentences}

## Key Risks
- {R-NNN}: {one line}

## Key Dependencies
- {dependency}: {owner}

## Complexity Hotspots
{identifiers — comma separated}

## NFR Constraints
- {NFR-NNN}: {design impact}

## Unknowns Needing Spikes
- {U-NNN}: {one line}
