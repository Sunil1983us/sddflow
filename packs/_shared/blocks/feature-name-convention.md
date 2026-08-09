**`{Feature Name}` convention.** Every generated document's `{Feature Name}`
placeholder (`# Feature: {Feature Name}`, `# Use Case Specification —
{Feature Name}`, etc. — nearly every template header, plus Confluence page
titles and the Jira Epic Summary — see `specify-brd.prompt.md`'s Jira Epic
Summary rule, which follows this same order) resolves in this order:
1. `manifest.yml`'s `project.feature_display_name`, if present and non-empty
   — this feature's own display name. Use this on any project with more
   than one feature: `project.name` stays one stable identity for the
   whole project, so if it were reused as every feature's document-header
   name too, a second feature's BRD would header itself identically to the
   first feature's, and their Confluence pages would collide on title
   (page lookup is by title) — Jira Epic summaries would collide the same
   way. `feature_display_name` is what actually varies per feature: update
   it — not `project.name` — every time `project.feature` switches to a
   different feature (see CLAUDE.md "Feature Drift Check").
2. `manifest.yml`'s `project.name`, if `feature_display_name` is absent or
   empty — the common case for a single-feature project, where the
   project's identity and its one feature's identity are the same thing,
   so no separate field is needed.
3. `manifest.yml`'s `project.feature` (the slug), only if both of the above
   are empty.
Never substitute `context.md`'s own title/Service Name for this — that's
free text the user may phrase more descriptively than the manifest (e.g.
"NIPE Validation Service" vs. a manifest `name: Validation`), and using it
produces a document header that silently disagrees with `manifest.yml`,
Confluence page titles, and the Jira Epic summary.
