**On review response** — trigger this whenever the user's message indicates
the review has moved forward: any approval signal (**'approved'**,
**'approve'**, **'yes'**, **'LGTM'**, **'looks good'**, **'go ahead'**,
**'confirmed'**, or any similar affirmative), a mention that they've left
comments or feedback, or a general check-in ("check", "any updates?", "did
they review it?"). Don't wait specifically for the word "approved" — any of
these should trigger this step.

1. If the `sdd` CLI is configured, run `sdd review check --doc {doc_key}`
   and follow its exit code:
   - **Exit 0 (APPROVED)** — continue to step 2 below.
   - **Exit 1 (NEEDS REVISION)** — the command prints the reviewer's
     comments. Read each one, edit the document to address the feedback,
     then run `sdd review apply --doc {doc_key}`. Tell the user the
     document has been updated per the review comments and the reviewer
     has been notified — then **STOP**. Do not continue to step 2; wait
     for the user to check back in.
   - **Exit 2 (PENDING)** — tell the user the document is still awaiting
     review by the accountable role (see roles.yml) — **STOP**, do not
     continue to step 2.
   - **CLI not configured, or the command is unavailable** — this is
     chat-mode review: if the user's message was an explicit approval
     signal, continue to step 2. Otherwise treat their message as direct
     feedback — apply it to the document yourself and ask for re-review;
     do not continue to step 2.
2. Update the document header: flip its `Status:` value (`Draft` or
   `Proposed`) to `Approved`, date → today.
3. Update the Approvals table: all Pending rows → `Approved` + today's
   date. Version History: append
   `| 1.0 | {today} | {jira or chat} | Approved | — |`
4. Re-save the document and regenerate its `.summary.md`.
5. Ask once: "Recording the approval — approver name/role and an optional
   comment?" (defaults: the accountable role for this gate in roles.yml;
   "approved in chat")
6. If the `sdd` CLI is installed, record it:
   `sdd review approve --doc {doc_key} --local --by "{approver}" --note "{comment}"`
   This also updates the document's existing Confluence page when a
   `confluence:` section exists in `.specify/integrations.yml`. If the CLI
   is not installed, skip — the `Status: Approved` header is the
   authoritative gate; tell the user any Confluence copy was NOT updated.
