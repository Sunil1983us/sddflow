# Security Policy

## Reporting a Vulnerability

**Do not open a public GitHub issue for a security vulnerability.**

Instead, use GitHub's private vulnerability reporting:

1. Go to [Security → Advisories → Report a vulnerability](https://github.com/sunil1983us/sddflow/security/advisories/new).
2. Describe the issue, affected component (Python CLI, Node CLI, dashboard,
   or a specific pack), affected version(s), and reproduction steps.

This opens a private discussion visible only to you and the maintainer until
a fix is ready — nothing is public until you and the maintainer agree it
should be.

If you don't have GitHub access or the link above doesn't work for you,
email **sunil1983.us@gmail.com** instead, with "SECURITY" in the subject
line.

## What's in scope

- `cli-python/` (the `sddflow` PyPI package) and `cli/` (the Node CLI,
  maintenance mode) — credential handling (`keyring`, `.specify/auth.yml`),
  the dashboard's write-endpoint auth (session token, CSRF, Origin
  checking — see `cli-python/README.md` → "Dashboard security"), and
  request handling for the Jira/Confluence integrations.
- The `sdd-*` packs' `setup.sh`/`setup.ps1` scripts — these run
  non-interactively in CI and take user-supplied strings (project name,
  feature name), so injection-class issues there are in scope.

## What's generally out of scope

- Documents an AI agent generates while *following* a pack's prompts —
  that content is only as trustworthy as the AI tool and the project data
  it was given; it isn't something this repo's code controls at runtime.
- Vulnerabilities in third-party dependencies with no SDD-specific
  exploitation path — please report those upstream instead (though a note
  here is still welcome if it affects how this project uses that
  dependency).

## Supported versions

This project doesn't maintain long-term-support branches — only the
latest published version (`cli-python/sdd/__init__.py` → `__version__`,
matching PyPI) receives fixes. If you're on an older version, please
upgrade (`sdd upgrade` for a project already using a pack, or
`pip install --upgrade sddflow`) before reporting, if practical — a fix
may already be shipped.
