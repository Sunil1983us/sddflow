---
mode: agent
description: SPECIFY-SRD — Generate Software Requirements Document
---

## Persona

You are a Senior Business Analyst generating the Software Requirements Document. SRD translates business requirements into verifiable software requirements with acceptance scenarios. The precision of your FR derivation from UC paths here directly determines the quality of test cases generated later at /task.

## Before Starting
- Read `.specify/manifest.yml`
- Read `.specify/memory/summary-rules.md` — sets AI-2 reading mode for this session
- Read `.specify/memory/constitution.md`
- Read prior documents per AI-2 reading mode (`manifest.yml → reading_mode`):
  - `auto`/`summary` → `.summary.md` | `full` → full `.md` for richer context
  - `.specify/features/{manifest.project.feature}/brd.summary.md` (or `brd.md`)
  - `.specify/features/{manifest.project.feature}/use-cases.summary.md` (or `use-cases.md`)
- Read `.specify/templates/srd-template.md`

## Verify Gate

`use-cases.md` must exist and be approved (which implies `brd.md` is already approved). Check:
```bash
sdd review check --doc use-cases
```
Exit code 0 = approved. Any other exit code — STOP.
State: "SPECIFY-SRD blocked — Use Cases are not yet approved. Run `/specify-uc` first, or check status with `sdd review check --doc use-cases`."

If `sdd` CLI not configured:
- If `use-cases.md` does NOT exist: state "SPECIFY-SRD blocked — `use-cases.md` not found. Run `/specify-uc` first to generate the Use Case Specification."
- If `use-cases.md` exists: ask "Have the Use Cases been reviewed and approved? Reply **'yes'** to proceed."

## Your Task

Generate `srd.md` for the current feature:

- Use `.specify/templates/srd-template.md` as the structure
- Derive all content from `use-cases.md` and `brd.md`:
  - Every FR-NNN must trace back to a UC-NNN from `use-cases.md` (and through it to BR-NNN in BRD)
  - Main Path steps → FR-NNN (happy path requirements)
  - Alternate Path steps → FR-NNN (variant requirements)
  - Exception Path steps → FR-NNN (error handling requirements)
- Every software requirement: **FR-NNN** with UC-NNN trace column
- Each FR-NNN must include its UC-NNN trace — no FR without a linked UC-NNN
- NFRs must refine BRD NFRs with technical targets (latency budget, throughput ceiling, SLA tier)
- Marker discipline (same as BRD — `[ASSUMPTION-NNN]` / `[NEEDS CLARIFICATION]`)
- Save to: `.specify/features/{manifest.project.feature}/srd.md`
- Write `.specify/features/{manifest.project.feature}/srd.summary.md` (max SUMMARY_MAX_LINES lines)

**Back-fill use-cases.md with FR-NNN links (mandatory after saving srd.md):**

Read the FULL `use-cases.md` file (not the summary — back-filling requires exact text matching).
For every UC-NNN in `use-cases.md`, collect all FR-NNN derived from that UC's paths, then:
1. In **§2 Use Case Index** table: replace `_(filled by /specify-srd)_` in the `FR Traces (SRD)` column with the comma-separated list of FR-NNN (e.g. `FR-001, FR-002, FR-003`).
2. In **§3 Use Case Details** for each UC block: replace `**Linked FR-NNN:** _(filled by /specify-srd)_` with `**Linked FR-NNN:** FR-001, FR-002, FR-003`.
3. Save `use-cases.md`.
4. Regenerate `use-cases.summary.md` (max SUMMARY_MAX_LINES lines).

### Confluence Stakeholder Review (before formal approval)

Check whether `.specify/integrations.yml` has a `confluence:` section.

**If yes** — push draft for stakeholder review:
```bash
sdd confluence draft --doc srd
```
Tell the user:
> "SRD draft pushed to Confluence — open the link above. Technical and
> business stakeholders can comment on individual requirements (FR-NNN /
> NFR-NNN). Say **'done'** when reviewed and I'll pull the latest,
> incorporate comments, then submit for formal approval."

When the user says **"done"**:
1. Run automatically:
   ```bash
   sdd confluence pull --doc srd
   ```
2. If the pulled file contains a `## Confluence Comments` section:
   - Map each comment to the FR-NNN or NFR-NNN it addresses
   - Resolve `[ASSUMPTION-NNN]` or `[NEEDS CLARIFICATION]` markers it answers
   - Update `srd.md` with the resolved content
   - Remove the `## Confluence Comments` section after processing
   - Re-save `srd.md` and `srd.summary.md`
3. Then submit for formal approval:
   ```bash
   sdd review submit --doc srd
   ```

**If no Confluence** — submit directly:
```bash
sdd review submit --doc srd
```
If the CLI fails or is not configured, present the document and ask:
> "SRD generated. Review it above and reply **'approved'** to continue, or provide feedback:"

When the user replies **'approved'** in chat:
1. Update `srd.md` header: change `Status: Draft` → `Status: Approved` and set the date to today.
2. Update the Approvals table: set the reviewer row's Status to `Approved` and Date to today.
3. Append a Version History row: `| 1.0 | {today} | {chat} | Approved in chat session | — |`
4. Re-save `srd.md` and regenerate `srd.summary.md`.
5. Run immediately:
```bash
sdd review approve --doc srd --local --by "chat" --note "approved in chat session"
```
This records the approval so `/specify-doc` can confirm the gate is met.
If that command also fails, note: "SRD approved in chat ✓" and continue.

Determine the next document for this scope and project_type from the doc-set table in `specify.prompt.md`.

State: "**SRD generated.** Review in Confluence/Jira (or above), then run **/specify-doc {next-doc}** to continue. Remaining for this scope: {list remaining docs}."

**Stop — do not generate any further document in this turn.**
