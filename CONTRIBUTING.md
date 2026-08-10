# Contributing

Thanks for considering a contribution. A few things to know before you file
an issue or open a PR.

## Reporting a bug or requesting a feature

Use [GitHub Issues](https://github.com/sunil1983us/universalguide/issues) —
pick the **Bug report** or **Feature request** template. A few notes that
save a round-trip:

- **Security vulnerability?** Don't use a public issue — see
  [SECURITY.md](SECURITY.md) for private disclosure instead.
- Say **which part** is affected: a specific `sdd-*` pack (and which
  command/prompt), the Python CLI (`sddflow`), the Node CLI (maintenance
  mode only — see below), or the dashboard. This repo hosts several
  distinct things in one place, so this narrows it down fast.
- Include your `sdd_version` (from `.specify/manifest.yml`, or
  `sdd --version`) and, for a pack issue, the `project_type` and `scope`.

## What this repo is

This is the **maintainer repo** for the SDD Framework — a set of
self-contained packs end-users copy into their own projects, plus the
`sddflow` CLI that scaffolds and drives them. If your issue is about
something a pack *generated* (a spec document, a piece of generated code)
rather than the framework itself, it's likely an AI-behavior question
specific to your project's own `context.md`/`constitution.md`, not a bug
in this repo — worth double-checking before filing.

## Scope: what belongs here

- **Core** (must work with nothing else configured): the SDD packs,
  the Python CLI, the review-gate system (chat/local/jira modes), the
  dashboard.
- **Optional adapters** (integrate with core, never required by it):
  Jira, Confluence, PR automation (GitHub/GitLab/Bitbucket/Azure DevOps),
  diagram rendering.
- **Node CLI** (`cli/`): frozen at scaffolding-only (`init`/`upgrade`),
  maintenance mode, no new features — see its own
  [README](cli/README.md) for why. Bug fixes are still welcome there;
  new functionality should go in the Python CLI instead.

A feature request that adds a new required dependency to core is unlikely
to be accepted as-is; the same idea as an *optional* adapter usually is.

## Opening a pull request

1. Check whether an issue already covers what you're proposing —
   for anything beyond a small fix, opening an issue first avoids
   duplicated work.
2. Keep the change scoped to one thing. If it touches a canonical
   `_shared/` source, run `bash packs/_shared/sync-blocks.sh` and include
   the synced output in your diff — don't hand-edit a pack's copy
   directly, it'll get silently reverted on the next sync by anyone else.
3. Run the relevant test suite before opening the PR:
   ```bash
   cd cli-python && python3 -m pytest tests -q
   cd cli && npm test
   bash packs/_shared/tests/test-setup.sh
   python3 packs/_shared/tests/check-cross-references.py --verbose
   ```
4. If your change is something `sdd upgrade` would carry to an existing
   user's project (CLI code, pack templates/prompts, `_shared/` content,
   `setup.sh`/`setup.ps1`), it needs a version bump — see
   `.claude/skills/version-bump/SKILL.md` for the exact rule (standard
   SemVer: patch for fixes, minor for backward-compatible additions,
   major for anything breaking). Pure documentation changes don't need
   one.

## License

By contributing, you agree your contribution is licensed under this
repo's [MIT license](LICENSE).
