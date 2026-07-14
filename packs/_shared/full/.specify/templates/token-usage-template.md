# Token Usage Log
# Feature: {Feature Name}
> Self-estimated, not measured. Living document — appended to after every
> command, never regenerated from scratch (that would erase history).

---

## Running Totals

| Metric | Value |
|---|---|
| Total Est. Input Tokens | {sum of Est. Input Tokens column} |
| Total Est. Output Tokens | {sum of Est. Output Tokens column} |
| Total Est. Cost (USD) | {sum of Est. Cost column, or "n/a — see notes" if any row is unpriced} |
| Commands logged | {count of rows} |
| Last updated | {ISO date of most recent row} |

---

## Per-Command Log

| # | Command | Model | Est. Input Tokens | Est. Output Tokens | Est. Cost (USD) | Timestamp |
|---|---|---|---|---|---|---|

---

## How These Numbers Are Estimated — read before trusting this file

- **Self-estimated, not measured.** No AI tool this framework supports
  (Claude Code, GitHub Copilot, Cursor, Windsurf, or copy-paste "any AI")
  exposes an API letting an agent introspect its own exact token
  consumption mid-session — this is a platform limitation, not something
  a future version of this framework can fix by improving its formula.
  Every row here is an approximation:
  - Est. Input Tokens ≈ (total characters read this command — manifest,
    constitution, prior docs/summaries, templates) ÷ 4
  - Est. Output Tokens ≈ (total characters written this command — the
    generated document plus the chat response) ÷ 4
  - This ignores prompt-caching, tool-call overhead, and model-specific
    tokenization — real usage is usually higher than shown here.
- **Why this reads much lower than your provider's own usage/billing
  dashboard, specifically:** the estimate is deliberately scoped to only
  the SDD documents this one command intentionally read or wrote (per
  AI-2's `reading_mode` — often just a `.summary.md`, not the full prior
  document). It excludes everything else the same turn actually spent
  tokens on: the system prompt, tool/function definitions, prior
  conversation turns still in context, and any other files the agent
  read for unrelated reasons. Those are frequently the majority of a
  turn's real token cost, and there's no way for this framework to see
  or count them from inside a prompt. **For actual, billing-accurate
  numbers, use your AI tool's own native usage reporting** (e.g. Claude
  Code's `/cost` command or the Anthropic Console's usage page, GitHub
  Copilot's usage dashboard, or your provider's equivalent) — this file
  is not, and cannot become, a substitute for that.
- **Cost depends on `.specify/memory/token-pricing.yml`.** That file
  ships as `token-pricing.yml.example` with placeholder (`null`) rates —
  copy it in and fill in current prices from your provider's own pricing
  page. Until then, or for any model missing a row, the cost column
  reads the value from that file's `unknown_model_fallback`.
- **Use this for relative comparison, not billing.** It's useful for
  spotting which command or feature is expensive relative to another —
  it is not a substitute for your provider's actual invoice.
