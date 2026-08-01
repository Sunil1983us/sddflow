## Jira Epic/Feature — Created Now, Not Later

Check whether `.specify/integrations.yml` has a `jira:` section.

If yes — create the single parent Jira issue for this feature now, right
after saving constitution.md, before GATE-1 and before any spec document
exists:
```bash
sdd jira push --level epic
```
This is safe even though `brd.md` doesn't exist yet — the Epic's
description falls back to a placeholder ("Details pending — run
/specify-brd...") and is automatically refreshed with real content
(Problem Statement, Business Hypothesis, Description, Out of Scope from
brd.md §4/§1; NFR from srd.md §3 once it exists) the next time an
Epic-touching command runs (e.g. `/specify-brd`'s review submission)
after `brd.md` exists — the command is idempotent, so running it again
just updates the same issue in place. Every review ticket and dev
Story/Task created later in this feature's lifecycle nests under this
one Epic from the start.

If the command fails, or `jira:` isn't configured, mention it briefly
(one line) and continue — a missing Epic never blocks constitution
generation.
