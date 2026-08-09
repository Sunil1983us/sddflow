## Token Usage Logging (this command)
Check now, with a fresh file read — not a memory of whether
`.specify/memory/token-pricing.yml` existed earlier in this conversation.
The user may have created it mid-session, after an earlier command already
found it missing; an earlier "not found" does not carry forward.
If it exists: log this command now — see CLAUDE.md → "Token Usage Logging"
for the exact fields and how to compute them. Append one row to
`.specify/features/{feature}/token-usage.md` (create it from
`token-usage-template.md` if this is the first row for this feature) and
update its Running Totals table. If the file still doesn't exist, skip
this silently — do not create it and do not mention it.

This step is independent of any "proceed without stopping" / "don't wait
for confirmation" instruction the user gave for this session — e.g.
running every `/implement` task back-to-back without waiting for "go"
between them. That instruction waives the pause between steps, not this
logging step: run it after every single task/command execution
regardless, even mid-way through a whole batch. Skipping it "to save
time" produces a `token-usage.md` that silently under-reports cost for
every step it missed — worse than the one extra tool call it costs to
keep it accurate.
