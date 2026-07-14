# Token Usage Log
# Feature: {Feature Name}
> Real when available, estimated otherwise. Living document — appended
> to after every command, never regenerated from scratch (that would
> erase history).

---

## Running Totals

| Metric | Value |
|---|---|
| Total Input Tokens | {sum of Input Tokens column} |
| Total Output Tokens | {sum of Output Tokens column} |
| Total Cost (USD) | {sum of Cost column, or "n/a — see notes" if any row is unpriced} |
| Commands logged | {count of rows} |
| Last updated | {ISO date/time of most recent row} |

---

## Per-Command Log

| # | Command | Model | Input Tokens | Output Tokens | Cost (USD) | Source | Timestamp |
|---|---|---|---|---|---|---|---|

---

## How These Numbers Are Captured — read before trusting this file

- **`Source` tells you whether a row is Real or Estimated — check it
  before comparing rows to each other.** A `Real` row and an `Estimated`
  row are not measuring the same thing (see below); mixing them in one
  comparison will mislead you more than either one alone.
- **`Real (Claude Code)`** — actual measured token counts pulled from
  Claude Code's own local session transcript
  (`~/.claude/projects/.../*.jsonl`, including any subagent transcripts)
  via `sdd token-log`. This is the real usage the Anthropic API reported
  for the turns spent on this command — not an approximation. Only
  available when this session is running under Claude Code itself; every
  other AI tool this framework supports (GitHub Copilot, Cursor,
  Windsurf, copy-paste "any AI") has no local equivalent to read, so
  falls through to the estimate below. Even under Claude Code, this can
  under- or over-attribute usage at the boundary between two commands
  run back-to-back with no gap, and undocumented changes to Claude
  Code's own transcript format could silently break it in a future
  release — if `sdd token-log` ever exits non-zero, that's the fallback
  kicking in as designed, not a bug to chase.
- **`Estimated`** — no AI tool this framework supports exposes an API
  letting an agent introspect its own exact token consumption
  mid-session from *inside a prompt*; this is the fallback used whenever
  `Real` isn't available. It approximates:
  - Input Tokens ≈ (total characters read this command — manifest,
    constitution, prior docs/summaries, templates) ÷ 4
  - Output Tokens ≈ (total characters written this command — the
    generated document plus the chat response) ÷ 4
  - This ignores prompt-caching, tool-call overhead, and model-specific
    tokenization, and — unlike the `Real` rows — is deliberately scoped
    to only the SDD documents this command intentionally read or wrote
    (per AI-2's `reading_mode`, often just a `.summary.md`). It excludes
    everything else the same turn actually spent tokens on: the system
    prompt, tool/function definitions, and prior conversation turns
    still in context. Those are frequently the majority of a turn's real
    cost — estimated rows read far lower than a provider's own
    usage/billing dashboard because of this, not because the ÷4 formula
    itself is wrong.
- **For actual, billing-accurate numbers regardless of Source**, use
  your AI tool's own native usage reporting (e.g. Claude Code's `/cost`
  command or the Anthropic Console's usage page, GitHub Copilot's usage
  dashboard, or your provider's equivalent) — this file, `Real` rows
  included, is not, and cannot become, a full substitute for that; cache
  tokens in particular are billed at their own rates this file's schema
  doesn't split out (`Real` rows fold cache-creation and cache-read
  tokens into Input Tokens as one approximation of "billed input").
- **Cost depends on `.specify/memory/token-pricing.yml`.** That file
  ships as `token-pricing.yml.example` with placeholder (`null`) rates —
  copy it in and fill in current prices from your provider's own pricing
  page. Until then, or for any model missing a row, the cost column
  reads the value from that file's `unknown_model_fallback`. Logging
  (both `Real` and `Estimated`) is off entirely until this file exists —
  see `HOW-TO-USE.md`.
- **Use this for relative comparison, not billing.** It's useful for
  spotting which command or feature is expensive relative to another —
  it is not a substitute for your provider's actual invoice.
