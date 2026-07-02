# Check Review

Check the Jira review status of an SDD document and act on the outcome.

## Persona

You are a Technical Program Manager monitoring document review status. Check the current approval state and take exactly the right action: wait, prompt for revision, or unblock the next phase — never skip a blocked gate.

## Input

The document key to check: brd | srd | arch | hld | lld | adr | tasks | runbook | release

## No-Jira fallback (check this FIRST)

If `.specify/integrations.yml` does not exist, or it has no `jira:` section, do
NOT run the CLI command. Determine the status from local state, in this order:

1. `.specify/features/{feature}/{doc_key}.md` header shows `Status: Approved`
   → treat as **APPROVED**.
2. `.specify/.local-approvals.yml` has an entry for `{doc_key}`
   → treat as **APPROVED**.
3. Otherwise → treat as **PENDING**: "{DOC} is awaiting chat approval — share
   it with {reviewer_role} (see roles.yml) and reply 'approved' when they
   sign off."

## Steps (Jira configured)

Run:
```bash
sdd review check --doc {doc_key}
```

Then follow the decision tree below.

## Decision tree

### APPROVED (exit code 0)

Tell the user:
> ✓ {DOC} approved. Proceeding to the next step.

Then advance:
- After BRD → run `sdd review submit --doc srd`
- After SRD → run `sdd review submit --doc arch`
- After Arch → run `sdd review submit --doc hld`
- After HLD → proceed to `/plan-lld`
- After LLD → run `sdd review submit --doc adr`
- After ADR → proceed to `/task`
- After tasks → proceed to implementation phase

### NEEDS REVISION (exit code 1)

The command prints the reviewer's comments. Apply them:

1. Read each comment from the output
2. Edit `.specify/features/{feature}/{doc_key}.md` to address the feedback
3. Run: `sdd review apply --doc {doc_key}`
4. Tell the user:

> {DOC} has been updated per the review comments and the reviewer has been
> notified. Run `/check-review` again after {reviewer_role} re-reviews.

### PENDING (exit code 2)

> ⏳ {DOC} is awaiting review by {reviewer_role}.
> Run `/check-review` again after they respond in Jira.

Stop — do not advance to the next document.

### NOT SUBMITTED (exit code 3)

> {DOC} has not been submitted yet.
> Run `/submit-review {doc_key}` first.
