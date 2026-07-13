Check `.specify/integrations.yml` for `confluence:` and `jira:` sections.

**Both configured — submit immediately.** This pushes the document to
Confluence AND creates the Jira review Story in one call, right now —
there is no separate "push a draft, wait, then submit" staging step;
both happen together the moment the document is generated:
```bash
sdd review submit --doc {doc_key}
```
Tell the user:
> "Pushed to Confluence and submitted for Jira review — see the links
> above. Reply **'approved'** (or 'yes', 'LGTM', 'looks good') once it's
> reviewed, or just check back with me any time — I'll poll Jira for you."

If the command fails (e.g. `'{doc_key}' not in document_reviews in
integrations.yml` — the Jira review-story gate needs a reviewer assigned
per doc, configured separately from `jira:`/`confluence:` themselves),
say so briefly, **do not silently drop all the way to chat mode** — a
`confluence:` section still means the document should land in
Confluence. Fall through to the "Only `confluence:` configured" branch
below instead (push a draft there); only fall all the way to chat mode
if `confluence:` itself is absent too.

**Only `confluence:` configured (no `jira:`, or `jira:` present but
`sdd review submit` failed above)** — no formal Jira gate exists (yet, or
for this doc); push a draft for informal stakeholder comments instead:
```bash
sdd confluence draft --doc {doc_key}
```
> "Draft pushed to Confluence — open the link above. Stakeholders can
> comment on any section. Say **'done'** when reviewed and I'll pull the
> comments, incorporate them, then ask you to approve in chat."

When the user says **"done"**: run `sdd confluence pull --doc {doc_key}`
automatically. If the pulled file contains a `## Confluence Comments`
section, match each comment against the marker ID it cites (e.g. a comment
starting "NC-002: ..." answers `[NEEDS CLARIFICATION-002: ...]`; older
comments with no cited ID fall back to matching by nearest question text),
resolve the corresponding `[NEEDS CLARIFICATION-NNN]`/`[ASSUMPTION-NNN]`
marker, update the document, remove the comments section, and re-save
the document and its `.summary.md`. Then present it and ask for
**'approved'**.

**Neither configured (chat mode)** — present the document above and ask:
> "Generated. Review it above and reply **'approved'** (or 'yes', 'LGTM')
> to continue, or provide feedback:"
