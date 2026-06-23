# How To Use — SDD Pack

---

No `.specify/contexts/{feature}.md` yet? Run `/create-context` first —
paste rough notes and the agent drafts context.md with you, instead of
writing it by hand. See `.specify/contexts/CONTEXT-GUIDE.md`.

## Command Flow

| Command | What It Does | Scope |
|---|---|---|
| `/specify` | Constitution Part 2 (DRAFT) only | Always |
| **GATE-1** | You review + finalize constitution Part 2 (manual) | Always |
| `/specify-brd` | Business Requirements Document | Always |
| `/specify-uc` | Use Case Specification (Actors + MP/AP/EP) | Always |
| `/specify-srd` | Software Requirements Document | Always |
| `/specify-doc {name}` | Extended docs (security, data-model, resilience…) | Scope-dependent |
| `/checklist` | Spec quality gate | Mandatory mvp+, optional pilot |
| `/validate` | Business sign-off on BRD + Use Cases + SRD | Always |
| `/analyze` | Risks + complexity + distributed systems check | Always |
| `/clarify` | Questions → you answer → update spec | Always |
| `/plan-design` | Architecture + Diagrams + API Design + ADRs | Always |
| `/plan-lld` | LLD + class/sequence diagrams | MVP+ only |
| `/task` | Feature → Story → Task + Jira CSV | Always |
| `/implement` | Code one task at a time | Always |
| `/release` | UAT + deployment plan + go-live gate | Always |
| `/orchestrate` | Drive full pipeline automatically — pauses at every human gate | Optional |

---

## Command Flow Diagrams

### Pilot
```
/specify → [GATE-1] → /specify-brd → /specify-uc → /specify-srd
→ /checklist (optional) → /validate → /analyze → /clarify
→ /plan-design → /task → /implement → /release
```

### MVP+
```
/specify → [GATE-1] → /specify-brd → /specify-uc → /specify-srd
→ /specify-doc security → /specify-doc data-model
→ /checklist (mandatory) → /validate → /analyze → /clarify
→ /plan-design → /plan-lld → /task → /implement → /release
```

---

## Scope Presets

### Pilot — Demo / Proof of Concept
```yaml
scope: "pilot"
# /specify-doc: none (security-design §1 via /specify-srd)
# /checklist: optional
# /plan-lld: skipped
# /implement: code + tests only
```

### MVP — First Production Release
```yaml
scope: "mvp"
# /specify-doc: security-design §1-2, data-model
# /checklist: mandatory
# /plan-lld: included
# /implement: + QA cases, Runbook
```

### Full — Complete Production
```yaml
scope: "full"
# /specify-doc: security-design §1-4, data-model, resilience, investigation
# /checklist: mandatory
# /plan-lld: included
# /implement: + QA cases, Runbook, OpenAPI
```

---

## Constitution — How It Gets Filled

/specify reads your context and extracts (as a DRAFT — see GATE-1):

| Extracted | From your context section |
|---|---|
| Language + Framework | Tech stack section |
| Build Tool | Derived from language |
| API Style | Endpoint contracts |
| Messaging | Integration section |
| Database + Cache | Tech stack / integrations |
| DB Migration | Derived from framework |
| Config + Secrets | Infrastructure section |
| Resilience | NFR section |
| Observability + Logging | NFR / tech stack |
| Testing + Coverage | NFR section |
| CI/CD + Orchestration | Infrastructure |
| Core Principles | Domain + constraints |
| Domain Rules | Business rules |
| Never Do | Constraints |

**Tip: richer context = better constitution draft.**

---

## GATE-1 — Finalize Constitution Part 2 (manual, blocking)

After /specify, Part 2 is a DRAFT. Before /specify-brd can run:

1. Open `.specify/memory/constitution.md` → Part 2
2. Review every row — Tech Stack, Core Principles, Domain Rules, Never Do
3. Resolve any `[MISSING — ask user]` markers
4. Edit anything wrong directly — your edits are AUTHORITATIVE
5. Tell the agent: **"Constitution Part 2 finalized"**

A later `/specify` re-run must propose changes for review — it will
never silently overwrite a finalized Part 2.

---

## Review Gates

| Command | Reviewer (see roles.yml) | Before Next |
|---|---|---|
| GATE-1 | Tech lead (accountable) | /specify-brd |
| /specify-brd | Product owner | /specify-uc |
| /specify-uc | Business analyst + Product owner | /specify-srd |
| /specify-srd | Business analyst | /validate |
| /validate | Product owner + Business analyst | /analyze |
| /analyze | Tech lead (+ architect, security officer consulted) | /clarify |
| /clarify | Product owner (accountable), BA (consulted) | /plan-design |
| /plan-design | Tech lead + architect + stakeholders | /plan-lld or /task |
| /plan-lld | Senior developer | /task |
| /task | Product owner + dev team (+ QA lead consulted) | /implement |
| /implement | Assigned developer — per task PR | /release |
| /release | QA lead (responsible), product owner (accountable) | go-live |

---

## Reading Mode — Quality vs Token Economy

```yaml
reading_mode: "auto"    # auto | summary | full
```

- **auto** (default): use `.summary.md` if present; fall back to full doc + auto-generate summary
- **summary**: always use summary only; strict token economy
- **full**: always read full `.md`; maximum quality at higher token cost

Set `reading_mode: "full"` in `manifest.yml` for complex features where you want the agent to read every document completely.

---

## Summary Limits
Edit `.specify/memory/summary-rules.md`:
```
pilot: SUMMARY_MAX_LINES: 20
mvp:   SUMMARY_MAX_LINES: 25
full:  SUMMARY_MAX_LINES: 30
```
Tell agent: "Summary rules updated — re-read summary-rules.md"

---

## Workflow Mode — GitHub or Local

```yaml
workflow_mode: "github"   # github | local   DEFAULT: github
```

**github** (default) — branch + PR flow:
- `/implement` ends each task with `"PR ready — {N} lines, {N} files"`
- CI (`.github/workflows/quality-gate.yml`) runs build/test/coverage/
  lint/secret-scan/SCA on every PR push
- `/release` requires every task PR-approved and merged

**local** — no git hosting required:
- `/implement` runs build/test/coverage/lint locally, reports ✅/❌,
  ends with `"Task accepted — {N} lines, {N} files"`
- `/release` requires every task `"Task accepted"`

Switch modes any time by editing `manifest.yml`.

---

## PR Rules
```yaml
pr_rules:
  max_lines_per_pr: 400
  max_files_per_pr: 5
```

---

## Upgrading Scope

1. Edit `manifest.yml`: `scope: "pilot"` → `"mvp"` (or `"full"`)
2. Run `sdd review status` to see newly required documents
3. Generate new spec docs: `/specify-doc {name}` for each
4. Run `/plan-lld` if upgrading from pilot
5. Append `CHG-NNN` tasks to `tasks.md`

---

## File Ownership

| File | Owner | Changes |
|---|---|---|
| manifest.yml | You | Per project |
| contexts/{f}.md | You | Per feature |
| .specify/memory/roles.yml | You | RACI owners per project |
| constitution.md Part 1 | Framework | Never |
| constitution.md Part 2 | Agent (/specify) → You (GATE-1) | Generated draft, then finalized |
| summary-rules.md | You | When limit changes |
| All templates | Framework | Never |
| CLAUDE.md | Framework | Never |
