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
the accountable role). When recording an approval, the agent asks once for the
approver name/role and an optional comment.

**Governance guidance by scope:** chat mode is fine for `pilot`. For `mvp` use
local mode (named approver + audit file). For `full` scope prefer jira mode —
independent tracking of who approved what, when.

### jira mode commands

Sequences follow `plan_mode` (manifest.yml). Doc keys match the `.md`
filenames: `design` exists in unified mode; `arch`/`hld`/`adr` in separate mode.

| Phase | Sequence (unified) | Sequence (separate) | Reviewer |
|---|---|---|---|
| specify | BRD → Use Cases → SRD → Design | BRD → Use Cases → SRD | PO → BA → BA → Architect |
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
