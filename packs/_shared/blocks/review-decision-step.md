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
     comments (this also surfaces comments left via the dashboard when
     Jira is configured — dashboard comments mirror to the doc's Jira
     review ticket). Read each one, edit the document to address the
     feedback, apply **Revision Logging** below, then run
     `sdd review apply --doc {doc_key}`. Tell the user the document has
     been updated per the review comments and the reviewer has been
     notified — then **STOP**. Do not continue to step 2; wait for the
     user to check back in.
   - **Exit 2 (PENDING)** — tell the user the document is still awaiting
     review by the accountable role (see roles.yml) — **STOP**, do not
     continue to step 2.
   - **CLI not configured, or the command is unavailable** — this is
     chat-mode review: if the user's message was an explicit approval
     signal, continue to step 2. Otherwise treat their message as direct
     feedback (including feedback the user relays from a local-mode
     dashboard comment, which has no Jira ticket to poll) — apply
     **Revision Logging** below, then ask for re-review; do not continue
     to step 2.

**Revision Logging** — every time reviewer feedback causes a content edit,
regardless of which mode surfaced it (a Jira comment via `sdd review
check`, a dashboard comment, or feedback relayed directly in chat):
increment the document's `Version:` header (`1.0` → `1.1`, `1.1` → `1.2`,
...) and append a row to its `## Version History` table:
`| {new version} | {today} | {reviewer name if known, else "reviewer feedback"} | {1-sentence summary of what changed} | — |`
— the same discipline `/change` already uses for post-approval CRs. Skip
only if the feedback needed no content change (e.g. a clarifying question
you answered without editing the document).

2. Resolve the approver's name: find this gate's `accountable` role in
   `.specify/memory/roles.yml` → `gates:` (match by document/command name;
   `roles.yml`'s own comments name which gate maps to which document), then
   look up that role key (e.g. `product_owner`) in `roles.yml`'s top-level
   `roles:` map. If a non-empty name is filled in there, use it directly —
   no need to ask. Only if `roles.yml` doesn't exist, the matching gate/role
   entry is missing, or the value is still the shipped empty string (`""`),
   ask once instead: "Recording the approval — approver name and an
   optional comment?" (default comment if none given: "approved in chat").
3. Update the document header: flip its `Status:` value (`Draft` or
   `Proposed`) to `Approved`, date → today.
4. Update the Approvals table: all Pending rows → `Approved` + today's
   date, and fill each row's `Approver` column with the name resolved in
   step 2 — this is what makes "who actually approved this" visible
   directly in the document, not just the role that was accountable for
   it. Version History: append a row using the document's **current**
   version (a pure approval doesn't bump it — only Revision Logging above
   does that):
   `| {current version} | {today} | {approver name from step 2} | Approved | — |`
5. Re-save the document and regenerate its `.summary.md`.
6. If the `sdd` CLI is installed, record it:
   `sdd review approve --doc {doc_key} --local --by "{approver}" --note "{comment}"`
   This also updates the document's existing Confluence page when a
   `confluence:` section exists in `.specify/integrations.yml`. If the CLI
   is not installed, skip — the `Status: Approved` header is the
   authoritative gate; tell the user any Confluence copy was NOT updated.
