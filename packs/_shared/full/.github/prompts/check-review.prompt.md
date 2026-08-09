# Check Review

Check the review status of an SDD document and act on the outcome.

## Persona

You are a Technical Program Manager monitoring document review status. Check the current approval state and take exactly the right action: wait, prompt for revision, or unblock the next phase — never skip a blocked gate.

## Input

The document key to check: brd | use-cases | srd | design (unified) | arch | hld | adr (separate) | lld | tasks | runbook | release

Which planning keys apply depends on `plan_mode` in `.specify/manifest.yml`:
`design` for unified mode; `arch`, `hld`, `adr` for separate mode.

## Steps

Always run this — it works whether or not `jira:`/`confluence:` are configured.
Unlike `sdd review submit` (which hard-requires both `jira:` and `confluence:`),
`sdd review check` has no such prerequisite: with no `jira:` section at all it
still checks `.specify/.local-approvals.yml` for a recorded approval and
surfaces any unacknowledged dashboard comments directly (see the NEEDS
REVISION note below) — this is not a chat-only fallback, the CLI call itself
already covers it:

```bash
sdd review check --doc {doc_key}
```

Only skip this call — and fall back to a purely local check — if the `sdd`
CLI itself is **not installed at all** (`pip install sddflow`). That is a
genuinely different situation from "no `jira:`/`confluence:` configured,"
which the command above already handles on its own. In that not-installed
case only, determine status directly: the document's own `Status:` header
reading `Approved` → treat as **APPROVED**; otherwise
`.specify/.local-approvals.yml` has an entry for `{doc_key}` → treat as
**APPROVED**; otherwise → treat as **PENDING**: "{DOC} is awaiting chat
approval — share it with {reviewer_role} (see roles.yml) and reply 'approved'
when they sign off."

Then follow the decision tree below.

## Decision tree

### APPROVED (exit code 0)

Tell the user:
> ✓ {DOC} approved. Proceeding to the next step.

Then advance — read `plan_mode` and `scope` from `.specify/manifest.yml` first:
- After BRD → run `sdd review submit --doc use-cases`
- After Use Cases → run `sdd review submit --doc srd`
- After SRD → **unified**: run `sdd review submit --doc design` |
  **separate**: run `sdd review submit --doc arch`
- After Design (unified) → proceed to `/plan-lld` (mvp+) or `/task` (pilot)
- After Arch (separate) → run `sdd review submit --doc hld`
- After HLD (separate) → run `sdd review submit --doc adr` (mvp+) or
  proceed to `/task` (pilot — ADR and LLD are skipped)
- After ADR (separate, mvp+) → proceed to `/plan-lld`
- After LLD → proceed to `/task`
- After tasks → proceed to implementation phase

### NEEDS REVISION (exit code 1)

The command prints the reviewer's comments — this includes dashboard comments
in every mode: mirrored to the Jira review ticket and printed from there when
`jira:` is configured; surfaced directly by the CLI's own local-mode fallback
when it isn't. Apply them:

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
