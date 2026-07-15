## Token Usage Logging (opt-in — real when available, estimated otherwise)

Off by default. Turns on the moment `.specify/memory/token-pricing.yml`
exists (copy it from `token-pricing.yml.example` to enable — see
HOW-TO-USE.md). If that file doesn't exist, skip this section entirely —
do not create it yourself and do not log anything.

If it does exist, after every command that reads or writes a document
(`/create-context`, every `/specify-*`, `/plan-*`, `/task`, `/implement`,
`/release`, `/change`, `/checklist`, `/validate`, `/analyze`, `/clarify`):

1. **Try real usage first, if the `sdd` CLI is installed:**
   ```bash
   sdd token-log --command {this command's name, e.g. specify-brd}
   ```
   This reads Claude Code's own local session transcript for the turns
   spent on this command and writes an authoritative row itself —
   `.specify/features/{feature}/token-usage.md` is created from
   `token-usage-template.md` automatically if this is the first command
   logged for this feature; Running Totals are updated automatically too.
   Exit code 0 means it succeeded — you're done, skip step 2 entirely.
2. **Fall back to the estimate** whenever `sdd token-log` isn't
   available or exits non-zero (CLI not installed, not running under
   Claude Code, or nothing new since the last log — all normal, expected
   outcomes, not errors to report to the user): append one row to
   `.specify/features/{feature}/token-usage.md` yourself (create it from
   `token-usage-template.md` if this is the first command logged for
   this feature):
   - Input Tokens ≈ (total characters read this command, across every
     file touched — manifest, constitution, prior docs/summaries,
     templates) ÷ 4
   - Output Tokens ≈ (total characters written this command — the
     generated document plus your chat response) ÷ 4
   - Model: your own model identifier (e.g. `claude-sonnet-5`); write
     `unknown` if you cannot determine it
   - Cost: look up `{model}` in `token-pricing.yml`'s `models:` map and
     multiply its rates by the two estimates above; if the model has no
     row, or a row with `null` rates, write that file's
     `unknown_model_fallback` value instead of guessing a number
   - Source: `Estimated`
   - Timestamp: current date
   Then update the Running Totals table at the top of `token-usage.md`
   yourself (sum of every row logged so far for this feature).

These figures are for relative comparison only, `Real` rows included —
see `token-usage.md`'s own notes section for exactly what each `Source`
value does and doesn't measure.
