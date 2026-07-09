# How to Describe Your Project (or Skip This Entirely)

For sdd-micro, `context.md` is optional. The two ways to start:

## Option A — Just tell the agent (recommended for most micro projects)

```
/specify
A CLI script in Python that prints "Hello, world!" and accepts an
optional --name flag.
```

One to three sentences is enough — the agent drafts constitution Part 2
directly from your message, and GATE-1 is where you catch anything it
guessed wrong.

## Option B — Write context.md first

Useful if you want a written record before you start, or you're using
`/create-context` to turn rough notes into something structured. Fill
`.specify/contexts/{feature}.md` from `context-template.md`:

- **What This Does** — 1-3 sentences
- **Tech Stack** — language, run command, test command; skip rows that
  don't apply (e.g. no framework, no storage)
- **Ground Rules** — anything you explicitly want followed (optional)
- **Out of Scope** — only if it matters for something this small

Leave anything unknown blank or write "not sure" — `/specify` will mark
it `[MISSING — ask user]` and you resolve it at GATE-1.

## When to use the full context-template.md instead

If you find yourself wanting Actors, Endpoints, Integrations, or
Non-Functional Requirements sections, this project has likely outgrown
sdd-micro — see README.md → "Outgrowing sdd-micro".
