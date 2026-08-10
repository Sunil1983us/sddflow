## What does this change?

<!-- One or two sentences: what shipped, and why. Link the issue this addresses, if any. -->

## Where does it apply?

<!-- Which pack(s), the Python CLI, the Node CLI, the dashboard, or docs-only. -->

## Checklist

- [ ] Tests pass locally (`cd cli-python && python3 -m pytest tests -q`, and/or `cd cli && npm test`)
- [ ] If this touches a canonical `_shared/` source, `bash packs/_shared/sync-blocks.sh` was run and the synced output is included
- [ ] If this is something `sdd upgrade` would carry to an existing user's project (CLI code, pack templates/prompts, `_shared/` content, `setup.sh`/`setup.ps1`), the version was bumped per `.claude/skills/version-bump/SKILL.md` — otherwise this is docs-only and needs no bump
- [ ] `python3 packs/_shared/tests/check-cross-references.py --verbose` passes, if a `.prompt.md`/`CLAUDE.md`/`*-template.md` cross-reference was touched

## Anything a reviewer should know?

<!-- Edge cases considered, things intentionally left out, follow-up work. -->
