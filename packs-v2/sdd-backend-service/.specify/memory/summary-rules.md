# Summary Rules
SUMMARY_MAX_LINES: 20
# pilot:15-20 | mvp:20-25 | full:25-35
# Format: What → Key Decisions → Key Artifacts → Constraints → Out of Scope
# To change: edit SUMMARY_MAX_LINES, tell agent: "re-read summary-rules.md"

## AI-2 — Summary-First Rule (token economy, mandatory)
After /specify, every command reads ONLY `.summary.md` files for prior
documents — never the full `.md`. This keeps token usage roughly constant
per command regardless of how many documents exist (see
docs/SUMMARY-GUIDE.md → "What Each Verb Reads").

Exception: /implement reads `tasks.md` (current task only, in full) +
`constitution.md` (in full) — both are required for correct code
generation and are not summarized.

If a command needs detail beyond a summary, it should ask the user
whether to read the full document rather than reading it by default.

## .raw.md Files — Never Read (AI-2 exception)
`.specify/contexts/{feature}.raw.md`, if present, holds a user's original
unformatted notes saved by `/create-context`. It is reference-only — no
command (including /specify) ever reads it. Only `/create-context` reads
it, and only if the user re-runs that command to regenerate context.md.
