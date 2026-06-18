# /submit-review

Submit the most recently generated SDD document for stakeholder review.

## What this does

1. Identifies which document was just generated (from conversation context or $ARGUMENTS)
2. Runs `sdd review submit --doc <doc_key>`
3. Reports what was submitted, to whom, and what the reviewer needs to do

## Usage

```
/submit-review          # auto-detects document from context
/submit-review brd      # explicit document key
/submit-review hld      # explicit document key
```

## Document keys

| Key | Document | Typical reviewer |
|---|---|---|
| `brd` | Business Requirements | Product Owner |
| `srd` | System Requirements | Business Analyst |
| `arch` | Architecture Overview | Architect |
| `hld` | High-Level Design | Architect |
| `lld` | Low-Level Design | Tech Lead |
| `adr` | Architecture Decisions | Architect |
| `tasks` | Task Breakdown | Scrum Master |
| `runbook` | Runbook | DevOps |
| `release` | Release Notes | Release Manager |

## Agent instructions

Run:
```bash
sdd review submit --doc {doc_key}
```

After it completes, tell the user:
- Which document was submitted and its Confluence URL
- Who it is assigned to (role and Jira username)
- The Jira task key
- That they should tell the reviewer to open Jira, review the Confluence page,
  and either set the task to Done with comment "Approved", or add review comments
- That they should run `/check-review` when the reviewer has responded
