## Token Usage Logging (self-estimated, opt-in)

Off by default. Turns on the moment `.specify/memory/token-pricing.yml`
exists (copy it from `token-pricing.yml.example` to enable — see
HOW-TO-USE.md). If that file doesn't exist, skip this section entirely —
do not create it yourself and do not log anything.

If it does exist, after every command that reads or writes a document
(`/create-context`, every `/specify-*`, `/plan-*`, `/task`, `/implement`,
`/release`, `/change`, `/checklist`, `/validate`, `/analyze`, `/clarify`):
append one row to `.specify/features/{feature}/token-usage.md` (create it
from `token-usage-template.md` if this is the first command logged for
this feature):

- Est. Input Tokens ≈ (total characters read this command, across every
  file touched — manifest, constitution, prior docs/summaries, templates) ÷ 4
- Est. Output Tokens ≈ (total characters written this command — the
  generated document plus your chat response) ÷ 4
- Model: your own model identifier (e.g. `claude-sonnet-5`); write
  `unknown` if you cannot determine it
- Est. Cost: look up `{model}` in `token-pricing.yml`'s `models:` map and
  multiply its rates by the two estimates above; if the model has no row,
  or a row with `null` rates, write that file's `unknown_model_fallback`
  value instead of guessing a number
- Timestamp: current date

Then update the Running Totals table at the top of `token-usage.md` (sum
of every row logged so far for this feature). These figures are
estimates for relative comparison only — see `token-usage.md`'s own
notes section for why they are not exact measurements.
