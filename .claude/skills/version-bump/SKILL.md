---
name: version-bump
description: Computes and applies the next sdd_version for this repo (SDD Framework maintainer repo) using its capped major.minor.patch scheme, then updates every lockstep file, migration entry, and CHANGELOG entry that a version bump requires. Use this whenever a change is ready to ship — "bump the version", "cut a new release", "ship this as vX.Y.Z", "what's the next version", or any time you're about to touch cli-python/sdd/__init__.py, pyproject.toml, package.json, or a pack's manifest.yml sdd_version by hand. Don't compute the next version number manually — this skill's carry/rollover rule is not standard semver and hand-editing gets it wrong.
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

The version still looks like semver (`X.Y.Z`), but `Y` and `Z` are **capped counters**, not open-ended — this replaced the old "just increment patch forever" scheme (which had run away to `.100` before this was introduced). Capping keeps the numbers small and the meaning intact: `Z` — a patch within the current minor; `Y` — a minor within the current major.

- **Z (patch)** ranges **0–24**. Bumping normally means `Z += 1`.
- **Y (minor)** ranges **0–9**. Bumping normally means `Y += 1`.
- **X (major)** is uncapped.

**The carry rule** — when a bump would push a field past its cap, it rolls over instead:
- If `Z + 1` would equal `25`: instead do `Y += 1, Z = 0`. (`Z = 25` is never an actual version number.)
- If that `Y + 1` would equal `10`: instead do `X += 1, Y = 0`.

The cleanest way to compute this without off-by-one mistakes: treat the version as one running integer `N = X*250 + Y*25 + Z` (since `25*10 = 250` patches fit in one major), add 1, then reconstitute `X, Y, Z` via `divmod`:

```python
def next_version(x: int, y: int, z: int) -> tuple[int, int, int]:
    n = x * 250 + y * 25 + z + 1
    x, rem = divmod(n, 250)
    y, z = divmod(rem, 25)
    return x, y, z
```

Read the *current* version straight from `cli-python/sdd/__init__.py` (`__version__ = "X.Y.Z"`) — that file plus the other 8 lockstep files below must already agree; if they don't, stop and flag the mismatch rather than guessing which one is right.

**One-time historical note:** the transition point for this scheme was `2.7.100 → 2.8.0` — the old scheme's runaway patch count (`.100`) was reset by hand at that moment rather than divmod'd retroactively (`100` old-scheme patches do *not* mean 4 rollovers under the new rule). That reset already happened; every bump from `2.8.0` onward uses the plain carry rule above with no further special-casing.

## Applying a bump

### 1. Compute the next version

Read `__version__` from `cli-python/sdd/__init__.py`, apply the divmod rule above, confirm the result with the user's stated intent (a feature ship vs. a metadata-only bump doesn't change the *number*, but does change what goes in step 3's notes).

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
        "migrate": lambda m: {**m, "sdd_version": "NEW_VERSION"},
    },
```

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
    migrate: (manifest) => {
      manifest.sdd_version = 'NEW_VERSION';
      return manifest;
    },
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
