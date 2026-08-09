## Document Review Gates — Three Modes

Each SDD document is gated: the next document in a phase cannot proceed until
the current one is approved. The `Status:` header inside the `.md` file is the
**authoritative gate** in every mode — Jira and Confluence are integrations on
top of it, never a prerequisite.

| Mode | Needs | Approval flow | Audit trail |
|---|---|---|---|
| **chat** (default) | nothing | Reviewer reads the doc; user replies "approved" in chat → agent flips `Status: Draft → Approved` + fills Approvals table | Doc header + Approvals table + git history |
| **local** | `pip install sddflow` | Same as chat, plus the agent records it: `sdd review approve --doc {doc} --local --by "{approver}" --note "{comment}"` | `.specify/.local-approvals.yml` |
| **jira** | CLI + `integrations.yml` (`jira:` + `confluence:`) | `sdd review submit / check / apply` — Confluence page + Jira review story per doc | Jira + Confluence |

**Confluence stays in sync in every mode.** When a `confluence:` section exists
in `.specify/integrations.yml`, `sdd review approve --local` also updates the
document's existing Confluence page after flipping the status — chat and local
approvals never leave Confluence stale. Manual re-push at any time:
`sdd confluence push --doc {doc}` (needs only the `confluence:` section, no Jira).

**Who approves** is defined per gate in `.specify/memory/roles.yml` (RACI —
the accountable role). When recording an approval, the agent resolves the
approver's name from `roles.yml`'s `roles:` map first (filled in once per
project) and only asks the user directly if that name is still empty —
either way, the resolved name is written into the document's own
`## Approvals` table (`Approver` column), not just the role label, so it's
visible who actually approved it without cross-referencing roles.yml.

**Governance guidance by scope:** chat mode is fine for `pilot`. For `mvp` use
local mode (named approver + audit file). For `full` scope prefer jira mode —
independent tracking of who approved what, when.

**Self-approval risk (chat mode).** Nothing in chat mode stops the same
conversation that drafted a document from also being the one that replies
"approved" to it — there is no independent reviewer identity check, only
the human typing the word. This is why the scope guidance above escalates:
`local` mode at least records a named approver in an audit file, and
`jira` mode requires the actual accountable person (from `roles.yml`) to
act in Jira, outside the drafting conversation entirely. If chat mode is
used past `pilot`, treat approvals as informal and know that the
mechanism doesn't verify who is typing "approved" — for a genuinely
independent gate, have a *different* conversation/session (or a human
outside the AI tool altogether) perform the approval, not the same
session that generated the document.

### jira mode commands

Sequences follow `plan_mode` (manifest.yml). Doc keys match the `.md`
filenames: `design` exists in unified mode; `arch`/`hld`/`adr` in separate mode.

| Phase | Sequence (unified) | Sequence (separate) | Reviewer |
|---|---|---|---|
| specify | BRD → Use Cases → SRD → Design | BRD → Use Cases → SRD | PO → BA → BA → Architect |
| validate | Validate → Analyze → Clarify | Validate → Analyze → Clarify | PO → Tech Lead → Architect |
| planning | LLD (mvp+) | Arch → HLD → ADR (mvp+) → LLD (mvp+) | Tech Lead / Architect |
| tasks | Tasks | Tasks | Scrum Master |
| release | Runbook → Release | Runbook → Release | DevOps → Release Manager |

```bash
sdd review submit --doc brd      # push to Confluence + create Jira review story
sdd review check  --doc brd      # poll: exit 0=approved 1=needs-revision 2=pending
sdd review apply  --doc brd      # re-push after addressing reviewer comments
sdd review status                # full dashboard for all documents
```

When `sdd review check` exits 1 (NEEDS REVISION): read reviewer comments, update
the document, then run `sdd review apply` and ask reviewer to re-review.
Configure reviewers in `.specify/integrations.yml` — see `integrations.yml.example`.

**What `sdd review apply` actually does to an already-Approved document.**
This is the command every revision-driven step calls (a reviewer's NEEDS
REVISION feedback being addressed, or `/clarify` patching a document that
was already Approved) — it never creates a second Jira ticket for the
same document; it always re-uses the one ticket found by that document's
persistent label, updating it in place. On every call it also:
1. **Reverts the document's own `Status:` header** from `Approved` back
   to `Draft` (or `Proposed` for `adr.md`) — this happens unconditionally,
   even in pure chat/local mode with no `jira:`/`confluence:` configured,
   since it's a local-file operation. A document still mid-review (never
   yet Approved) is left untouched — nothing to revert.
2. Posts a "please re-review" comment on the existing Jira ticket, if one
   exists for this doc.
3. **Nudges the ticket's Jira workflow status**, only if `reopen_status`
   is set in `integrations.yml` (unset by default — see
   `integrations.yml.example`). The CLI cannot guess a real status name
   for your workflow, so this is opt-in: without it, a ticket already
   moved to Done/Closed stays there and only gets the comment above —
   with it, `sdd review apply` attempts a transition to the configured
   status (e.g. `"In Review"`) so the re-review request doesn't sit
   unnoticed on a closed ticket. Silently a no-op if the ticket is
   already in that status or the workflow has no path to it from the
   current state — never blocks the rest of the command.

**The `validate` phase is optional per-document.** Unlike the `specify`/
`planning`/`tasks`/`release` phases, `validate`/`analyze`/`clarify` fall back
to chat approval individually if their own `document_reviews` entry is
missing — add `document_reviews.validate` (and/or `.analyze`, `.clarify`) to
`integrations.yml` only for the ones you want routed through Jira/Confluence;
the rest stay chat-only.

**Blocked documents can still collect answers via Jira/Confluence.** A
document like `validate.md` can be blocked on `[NEEDS CLARIFICATION-NNN]`
markers in its source docs before it's ever submitted for review — see
`validate.prompt.md`'s §3a. `sdd review push-questions --doc {doc}` pushes
the open items to a Jira ticket + Confluence page (reusing the same
reviewer/ticket `sdd review submit` will use once unblocked — the ticket
evolves in place, no duplicate). `sdd review pull-answers --doc {doc}`
reads reviewer replies (a comment starting with the item's ID, e.g.
`brd:NC-002: 90 days`) and patches the answered marker directly into its
source document, bumping that document's version, and re-pushes that
document's own Confluence page immediately so it never goes stale.

**`clarify.md`'s own items (AMB/GAP/CON/ASM/OQ/R) work the same way**, via
the same two commands and the same doc key (`--doc clarify`) — even though
they're tracked by a STATUS TABLE row rather than a bracketed marker.
Reviewer replies as `clarify:AMB-001: <answer>`; pulling answers fills the
item's `{FILL...}` placeholder and flips its STATUS TABLE row to the
correct terminal status for its type (RESOLVED / CONFIRMED / DECIDED /
CORRECTED), then re-pushes clarify.md's own Confluence page. See
`clarify.prompt.md`'s "Accepted reply forms."

**Every review-driven edit bumps the version.** Whichever mode surfaced the
feedback — a Jira comment, a dashboard comment, or direct chat feedback —
increment the document's `Version:` header and append a row to its
`## Version History` table before re-submitting (see each command's own
review-response step for the exact format). A pure approval with no content
change does not bump the version.
