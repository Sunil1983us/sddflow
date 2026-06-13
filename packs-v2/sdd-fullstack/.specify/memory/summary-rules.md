# Summary Rules
SUMMARY_MAX_LINES: 20
# pilot:15-20 | mvp:20-25 | full:25-35
# Format: What → Key Decisions → Key Artifacts → Constraints → Out of Scope
# To change: edit SUMMARY_MAX_LINES, tell agent: "re-read summary-rules.md"

## .raw.md Files — Never Read (AI-2 exception)
`.specify/contexts/{feature}.raw.md`, if present, holds a user's original
unformatted notes saved by `/create-context`. It is reference-only — no
command (including /specify) ever reads it. Only `/create-context` reads
it, and only if the user re-runs that command to regenerate context.md.
