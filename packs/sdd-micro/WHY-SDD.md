# Why SDD — Even for a Tiny Project?

## The problem this pack avoids

Without any structure, an AI coding session for a small project tends to
drift: the tech stack changes opinion between commands, "just add a
quick config option" turns into three unrelated features, and by the
time something breaks you have no record of what was actually decided
and why.

The full SDD packs solve this with a constitution, requirements
documents, and staged review gates. That's the right tool for a team
project — and complete overkill for a script that prints "Hello, world!"

## What sdd-micro keeps

Just the two things that actually prevent drift on a small project:

1. **A constitution** (`constitution.md` Part 2) — one short, DRAFT
   document naming the tech stack and any ground rules, which you
   confirm once (GATE-1). Every later command reads it, so the agent
   doesn't silently switch languages, invent a framework you didn't ask
   for, or forget a rule you stated on day one.
2. **A task list** (`tasks.md`) — work is broken into small, verifiable
   steps before any code is written, and each one is checked off with an
   actual verification result, not an assumed one. This is what keeps
   "add a quick option" from quietly becoming three features.

## What sdd-micro deliberately drops

Everything that exists in the full packs to make a *multi-person, funded,
audited* project traceable:

- **BRD / Use Cases / SRD** — formal requirements docs written for a
  business stakeholder to sign off on. A personal script has no such
  stakeholder.
- **Validate / Analyze / Clarify** — review gates between requirements
  documents that don't exist here.
- **Design / Architecture docs** — for a project small enough to fit in
  one `tasks.md`, the architecture *is* the task list.
- **Release / Jira / Confluence** — go-live gates and ticket tracking for
  work nobody outside you needs visibility into.

None of this is "SDD is only good with all the ceremony" — it's the
opposite claim: the *value* of SDD is a constitution the agent can't
silently drift from, plus small verified steps. Everything else is
overhead that should scale with the project, not be paid upfront
regardless of size.

## When to add the ceremony back

The moment this project gets a second contributor, a real deployment, or
someone who needs to sign off on requirements, the tradeoff flips — see
README.md → "Outgrowing sdd-micro" for how to move to `sdd-universal`
without starting over.
