**`{Feature Name}` convention.** Every generated document's `{Feature Name}`
placeholder (`# Feature: {Feature Name}`, `# Use Case Specification —
{Feature Name}`, etc. — nearly every template header) resolves from
`manifest.yml`'s `project.name`, falling back to `project.feature` only if
`project.name` is empty. This matches the one place this was already
defined explicitly (the Jira Epic Summary rule in specify-brd.prompt.md) —
now it applies everywhere `{Feature Name}` appears.
Never substitute `context.md`'s own title/Service Name for this — that's
free text the user may phrase more descriptively than the manifest (e.g.
"NIPE Validation Service" vs. a manifest `name: Validation`), and using it
produces a document header that silently disagrees with `manifest.yml`,
Confluence page titles, and the Jira Epic summary.
