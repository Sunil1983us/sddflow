---
name: version-bump
description: Classifies a change as patch/minor/major (standard SemVer) and applies the next sdd_version for this repo (SDD Framework maintainer repo), then updates every lockstep file, migration entry, and CHANGELOG entry that a version bump requires. Use this whenever a change is ready to ship — "bump the version", "cut a new release", "ship this as vX.Y.Z", "what's the next version", or any time you're about to touch cli-python/sdd/__init__.py, pyproject.toml, package.json, or a pack's manifest.yml sdd_version by hand. Don't compute the next version number manually — the classification step (which field to bump) is a judgment call this skill walks through deliberately, and getting it wrong misleads anyone reading the number.
---

# Version Bump (SDD Framework maintainer repo)

This repo keeps one version number (`sdd_version`) in lockstep across 9 files, and every bump also needs a migration entry in two upgrade scripts plus a CHANGELOG entry. This skill covers the whole thing end to end, minus the final commit — leave that as an explicit, human-reviewed step.

## When to bump (and when not to)

`sdd_version` exists so `sdd upgrade` can tell an existing user's project it's behind and walk it forward through migrations. Only bump it for changes that `sdd upgrade` actually carries to a user's project:

- **Bump**: CLI command code (`cli-python/sdd/**`, `cli/src/**`), anything under a pack's `.specify/templates/**`, `.claude/commands/**`, `.github/prompts/**`, `.github/instructions/**`, `setup.sh`/`setup.ps1`, `_shared/blocks/**`, `_shared/full/**` — anything a real `sdd upgrade` migration would touch or that changes CLI-observable behavior.
- **Don't bump**: prose-only documentation that `sdd upgrade` never reads or writes — root `README.md`, `CHANGELOG.md`, `CLAUDE.md`, `SPEC-KIT-COMPARISON.md`, `PACK-SPEC.md`, a pack's own `README.md`/`WHY-SDD.md` prose, code comments, this skill file. Commit these directly with a normal descriptive message — no version bump, no migration entry, no MIGRATIONS-list touch. Their history is tracked by git commit SHA/date, not by a version number.
- **Mixed commit** (touches both): bump for the functional part — don't let doc edits riding alongside a real change suppress the bump, and don't let a functional change hide behind a "docs" label to avoid one.
- **Grey area**: default to *not* bumping unless you can point at the specific thing `sdd upgrade` would carry forward. It's cheaper to be wrong by under-bumping (a maintainer notices and bumps later) than by over-bumping (another entry in a 9-file lockstep and two migration scripts for something no user's project ever needed to know about).

This replaced the earlier default of bumping for every shipped change regardless of content — six bumps landed in one day earlier in this repo's history, several of them for root-doc-only edits with zero functional code touched.

## The versioning rule

Standard [SemVer](https://semver.org/) `MAJOR.MINOR.PATCH`, uncapped, no rollover math. Every bump increments **exactly one** field — the one matching the most significant kind of change in the release — and resets every field to its right to `0`. Which field moves is a classification you make deliberately, not an automatic "current + 1":

- **PATCH (Z)** — bug fixes only. No new command, no new template, no new manifest field, no new CLI flag, no behavior a user's project didn't already have. `Z += 1`, `X`/`Y` untouched.
- **MINOR (Y)** — backward-compatible additions. New command, new pack, new optional manifest field, new CLI flag, an extended template, a new opt-in mechanism (e.g. `sdd hooks`). A project that ignores the release loses nothing; one that adopts it gains something, with zero forced action. `Y += 1, Z = 0`.
- **MAJOR (X)** — breaking or requires-review changes. Renamed/removed command or flag, a manifest schema change that needs actual data transformation (not just a version stamp), changed doc-set requirements for an existing scope, anything that could silently alter an existing project's behavior if the user doesn't look at it. `X += 1, Y = 0, Z = 0`.

If a single commit mixes kinds (e.g. a bug fix riding along with a new command), classify by the **highest** kind present — one new command pulls the whole release to MINOR even if three unrelated one-line fixes are bundled in. Don't split a bump across two commits just to keep the classification pure; note the mix in the CHANGELOG entry instead.

When genuinely unsure whether something is PATCH or MINOR (e.g. "does relaxing a validation rule count as an addition?"), default to the more significant of the two candidates — MINOR over PATCH, MAJOR over MINOR. Under-classifying (calling a real behavior change a "patch") is the worse failure mode: it teaches readers the version number can't be trusted, which defeats the entire point of using SemVer.

Read the *current* version straight from `cli-python/sdd/__init__.py` (`__version__ = "X.Y.Z"`) — that file plus the other 8 lockstep files below must already agree; if they don't, stop and flag the mismatch rather than guessing which one is right.

**Historical note:** versions before this rule took effect (through `3.0.2`) were assigned by an earlier capped-counter scheme (`Y` capped 0–9, `Z` capped 0–24, with divmod-based rollover) that treated every bump as PATCH by default regardless of what shipped — that's exactly the flaw this rule replaces. Nothing about past version numbers is retroactively renumbered; `3.0.2` is simply where classification-based SemVer starts being applied going forward.

## Applying a bump

### 1. Classify the change, then compute the next version

Look at what's actually shipping (the diff, not just the description) and classify it PATCH / MINOR / MAJOR per the rule above. State the classification and the one-sentence reason before computing the number — this is the step worth getting right; the arithmetic after it is trivial (`X.Y.Z` → bump the classified field by 1, zero every field to its right). If the change's nature is ambiguous, ask the user rather than silently picking the smaller bump.

### 2. Update all 9 lockstep files

```
cli/package.json                                  "version": "X.Y.Z"
cli-python/pyproject.toml                          version = "X.Y.Z"
cli-python/sdd/__init__.py                         __version__ = "X.Y.Z"
packs/sdd-backend-service/.specify/manifest.yml     sdd_version: "X.Y.Z"
packs/sdd-frontend-spa/.specify/manifest.yml        sdd_version: "X.Y.Z"
packs/sdd-fullstack/.specify/manifest.yml           sdd_version: "X.Y.Z"
packs/sdd-mobile/.specify/manifest.yml              sdd_version: "X.Y.Z"
packs/sdd-universal/.specify/manifest.yml           sdd_version: "X.Y.Z"
```

`packs/sdd-micro` is deliberately excluded — it's frozen outside this lockstep (see the repo's `CLAUDE.md`). Don't touch it.

A single `sed -i 's/OLD_VERSION/NEW_VERSION/'` across all 8 (non-`__init__.py`... actually including it) works cleanly since the old version string is otherwise unique in each file — verify with a `grep -rn NEW_VERSION` pass afterward rather than trusting the sed silently.

### 3. Append a migration entry to both upgrade scripts

Every version bump gets a matching entry at the **end** of the `MIGRATIONS` list in both:
- `cli-python/sdd/commands/upgrade.py` (Python dict)
- `cli/src/commands/upgrade.js` (JS object, same content in JS syntax)

Write the actual `description`/`notes` to explain *this specific change* — what shipped, why, and what a user upgrading from the old version needs to know. If this bump is purely packaging/versioning housekeeping with no functional change (nothing in a user's `manifest.yml` or generated files differs), say so explicitly in the notes rather than inventing user-facing impact that doesn't exist — several past entries in this chain do exactly that (e.g. the packaging-metadata-only bump), and it's more honest than padding.

Python template (`upgrade.py`):
```python
    {
        "from":        "OLD_VERSION",
        "to":          "NEW_VERSION",
        "description": "One-line summary of what changed and why",
        "notes": [
            "First note -- what changed, in enough detail that a maintainer "
            "reading this months later understands the change without "
            "re-reading the diff",
            "Second note -- why, e.g. what user request or bug prompted it",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "Verified: cli-python pytest N/N (M pre-existing + K new)",
        ],
    },
```

Do **not** add a `"migrate"` key to the dict literal. Both `upgrade.py` and `upgrade.js` document (see the comment above their `MIGRATIONS`/`Migration` definitions) that every entry only ever stamps `sdd_version` — `_migrate_fn()` / `migrateFn()` supplies that lambda automatically for every entry, and the actual apply code never reads a per-entry `"migrate"` key at all. An explicit `"migrate": lambda ...` here is dead code that mypy's `Migration` TypedDict also rejects as an unknown key (`typeddict-unknown-key`) — this exact mistake shipped across 6 entries in one session before being caught by a red CI badge. Only touch `_CUSTOM_MIGRATE`/`CUSTOM_MIGRATE` directly in `upgrade.py`/`upgrade.js` for the rare entry that truly needs to transform manifest content beyond stamping the version.

JS template (`upgrade.js`) — same content, JS object syntax, string concatenation instead of adjacent-literal concatenation for the notes:
```javascript
  {
    from: 'OLD_VERSION',
    to:   'NEW_VERSION',
    description: "One-line summary of what changed and why",
    notes: [
      "First note -- ..." +
      "continued on the next line if long",
      "Second note -- ...",
    ],
  },
```

Keep the two entries' `notes` substantively the same — a maintainer or user should get the same story from either CLI's `sdd upgrade` output.

### 4. Add a CHANGELOG.md entry

Insert a new `## [NEW_VERSION] — DATE (one-line summary)` section immediately after the top `---` separator in `CHANGELOG.md`, i.e. *before* the previous top entry (newest first). Match the structure already used by every existing entry:

```markdown
## [NEW_VERSION] — DATE (one-line summary)

One or two prose paragraphs: what prompted this change, in plain language.

### Added / Changed / Fixed
(whichever apply -- most entries only need one or two of these)

- Bullet per notable change, same level of detail as the migration notes.

### Verified

- What was actually run to confirm this works (test counts, linters, smoke tests).

---
```

### 5. Verify

Run, in order, and don't proceed to commit if any fail:

```bash
python3 -c "import ast; ast.parse(open('cli-python/sdd/commands/upgrade.py').read())"
node --check cli/src/commands/upgrade.js
cd cli-python && python3 -m pytest tests -q
```

If pack-level files (templates, prompts, `_shared/blocks/`) were touched as part of the change being shipped — not just the version bump itself — also run:

```bash
bash packs/_shared/sync-blocks.sh          # re-sync shared content, check for unexpected diffs
python3 packs/_shared/tests/check-cross-references.py --verbose
bash packs/_shared/tests/test-setup.sh
bash packs/_shared/tests/test-setup-micro.sh
```

### 6. Stop here

Do not commit or push. Show a `git status --short` / `git diff --stat` summary and let the change be reviewed as a normal commit — this skill's job ends at "everything is ready to commit," matching how this repo's sessions have consistently operated (verify everything, then a separate, explicit, human-reviewed commit+push).
