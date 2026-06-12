# How To Use — SDD Pack

---

## Scope Presets

### Pilot (demo/proof of concept)
```yaml
scope: "pilot"
# Generates: BRD, SRD, Analyze, HLD, Plan, Tasks, Jira
# Skips: LLD, resilience, ADRs, QA cases, runbook
```

### MVP (first production release)
```yaml
scope: "mvp"
# Generates: all pilot + LLD, ADRs, QA cases, runbook
```

### Full (complete production)
```yaml
scope: "full"
# Generates: everything including resilience, security, investigation
```

---

## Upgrading Scope
```
1. Edit manifest.yml: scope: "pilot" → "mvp"
2. Tell agent:
   "Scope upgraded to mvp. Re-read manifest.yml.
    Generate newly enabled documents only — do not regenerate existing."
```

---

## Constitution — How It Gets Filled

SPECIFY reads your context and extracts:

| What it looks for | Where in your context |
|---|---|
| Language + Framework | Tech stack section |
| Database + Cache | Integrations or tech stack |
| Messaging | Async/event integrations |
| Deployment + CI/CD | Infrastructure section |
| Testing approach | NFR or tech stack section |
| Coverage Gate | NFR section |
| Resilience | NFR or constraints |
| Core Principles | Domain + constraints |
| Domain Rules | Business rules section |
| Never Do | Constraints section |

**Tip: The more detail in your context, the better the constitution.**

---

## Summary Limits
Edit `.specify/memory/summary-rules.md`:
```
SUMMARY_MAX_LINES: 20    ← pilot
SUMMARY_MAX_LINES: 25    ← mvp
SUMMARY_MAX_LINES: 30    ← full
```
Tell agent: "Summary rules updated — re-read summary-rules.md"

---

## PR Rules
Defaults in manifest.yml:
```yaml
pr_rules:
  max_lines_per_pr: 400   ← change if needed
  max_files_per_pr: 5
```

---

## For a New Project
```bash
cp -r sdd-{pack-name}/ new-project/
cd new-project
# Change only:
# .specify/manifest.yml        (4 fields)
# .specify/contexts/{f}.md     (your context)
# Everything else stays same
```

---

## File Ownership
| File | Owner | Changes |
|---|---|---|
| manifest.yml | You | Per project |
| contexts/{f}.md | You | Per feature |
| constitution.md Part 1 | Framework | Never |
| constitution.md Part 2 | Agent (SPECIFY) | Generated |
| summary-rules.md | You | When limit changes |
| All templates | Framework | Never |
| CLAUDE.md | Framework | Never |
| .specify/features/ | Agent | Per run |
