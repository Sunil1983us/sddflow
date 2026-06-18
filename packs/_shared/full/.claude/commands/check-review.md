# /check-review

Check the review status of a document and act on the outcome.

## Usage

```
/check-review           # checks the most recently submitted document
/check-review brd       # explicit document key
/check-review hld
```

## Agent instructions

Run:
```bash
sdd review check --doc {doc_key}
```

Then act based on the exit code:

### Exit 0 — APPROVED

The document is approved. Tell the user clearly:

> ✓ {DOC} approved. Proceeding to {next step}.

Then continue to the next step in the SDD sequence:
- After BRD → submit SRD for review (`/submit-review srd`)
- After SRD → submit Arch for review (`/submit-review arch`)
- After Arch → submit HLD for review (`/submit-review hld`)
- After HLD → proceed to `/plan-lld` (or next phase)
- After LLD → submit ADR for review (`/submit-review adr`)
- After ADR → proceed to `/task`
- After tasks → proceed to implementation

### Exit 1 — NEEDS REVISION

Review comments were found. Do the following:

1. Read each comment carefully
2. Edit the document file (`.specify/features/{feature}/{doc}.md`) to address each comment
3. Run: `sdd review apply --doc {doc_key}` — this re-pushes to Confluence and notifies the reviewer
4. Tell the user:

> {DOC} updated per review comments. The reviewer ({role}) has been notified to re-review.
> Run /check-review again after they respond.

### Exit 2 — PENDING

No reviewer response yet. Tell the user:

> ⏳ {DOC} is waiting for {reviewer_role} to respond in Jira.
> Run /check-review again after they have reviewed.

Stop — do not proceed to the next document.

### Exit 3 — NOT SUBMITTED

The document has not been submitted yet. Tell the user:

> Run /submit-review {doc} first.
