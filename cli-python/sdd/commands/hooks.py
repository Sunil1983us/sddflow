"""`sdd hooks` -- installs a git post-commit hook that runs `sdd
token-log --command implement` automatically after every commit.

Exists because prompt-file instructions are advice, not enforcement: a
user reported that even after implement.prompt.md was strengthened to
say the Token Usage Logging step must run per task regardless of any
"proceed without stopping" instruction (see CHANGELOG v3.0.1), an agent
mid-flow on a long /implement batch still skipped it -- it wasn't
re-reading the prompt file fresh at each task boundary. A git hook
makes this deterministic instead of hoped-for: it fires on every commit
regardless of what the AI agent remembers to do, since `sdd token-log`
sums usage since the last logged row -- calling it more often than
strictly needed (e.g. once per paired-test commit within one task) is
harmless, never double-counts.

Opt-in, not wired into `sdd init`/setup.sh -- installing a git hook is
a real side effect on the user's repository and shouldn't happen
without being asked, same principle as token-pricing.yml itself being
opt-in. Safe by construction either way: the hook script itself is
best-effort and silent (does nothing, quietly, if `sdd` isn't on PATH,
pricing isn't configured, or there's nothing new to log -- see
CLAUDE.md -> "Token Usage Logging") and never blocks the commit it's
attached to.
"""

from __future__ import annotations

import stat
from pathlib import Path

import click
from rich.console import Console

console = Console()

# First line doubles as both the shebang and our install marker (grepped
# for by `status`/`uninstall` to tell "ours" apart from a hook a user
# already had) -- bumping this version string is how a future release
# would detect and refresh an older installed copy, though nothing does
# that yet since the script has never changed shape.
_MARKER = "# sdd-token-log-hook v1"

_HOOK_SCRIPT = f"""#!/bin/sh
{_MARKER}
# Installed by `sdd hooks install`. Best-effort, per-commit token usage
# logging -- automates the manual `sdd token-log --command implement`
# call so it can't be silently skipped mid a long /implement run (a
# prompt-file instruction alone isn't a hard guarantee an AI agent
# follows it every task -- see CHANGELOG v3.0.1). Quiet by design,
# matching every other token-usage code path: does nothing, silently,
# if `sdd` isn't on PATH, pricing isn't configured, or there's nothing
# new since the last logged row -- see CLAUDE.md -> "Token Usage
# Logging" for what each of those outcomes means. Never blocks the
# commit: always exits 0 regardless of what sdd token-log reports.
if command -v sdd >/dev/null 2>&1; then
    sdd token-log --command implement >/dev/null 2>&1 || true
fi
exit 0
"""


def _git_hooks_dir(root: Path) -> Path | None:
    git_dir = root / ".git"
    if not git_dir.is_dir():
        return None
    return git_dir / "hooks"


def _is_ours(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        first_line = path.read_text(errors="replace").splitlines()[:2]
    except OSError:
        return False
    return any(_MARKER in line for line in first_line)


@click.group()
def hooks_command():
    """Install/manage git hooks that automate SDD housekeeping (currently:
    per-commit token usage logging)."""


@hooks_command.command("install")
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite an existing post-commit hook that isn't ours.",
)
def hooks_install(force):
    """Install the post-commit hook that runs `sdd token-log` after every
    commit. Refuses to clobber a foreign post-commit hook unless --force
    is passed -- re-running this safely no-ops (updates in place) once
    it's already ours."""
    root = Path(".")
    hooks_dir = _git_hooks_dir(root)
    if hooks_dir is None:
        console.print(
            "[red]✗  Not a git repository (no .git/ found here).[/red] "
            "Run this from your project root, after `git init`."
        )
        raise SystemExit(1)

    hooks_dir.mkdir(parents=True, exist_ok=True)
    target = hooks_dir / "post-commit"

    if target.exists() and not _is_ours(target):
        console.print(
            f"[yellow]·  {target} already exists and wasn't installed by "
            "sdd -- leaving it alone.[/yellow]\n"
            "   Add this line to your existing hook to get the same effect:\n"
            "   [dim]command -v sdd >/dev/null 2>&1 && sdd token-log "
            "--command implement >/dev/null 2>&1 || true[/dim]\n"
            "   Or re-run with [bold]--force[/bold] to overwrite it entirely."
        )
        if not force:
            raise SystemExit(2)

    target.write_text(_HOOK_SCRIPT)
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    console.print(
        f"[green]✓[/green]  Installed post-commit hook at [cyan]{target}[/cyan] -- "
        "every commit from here on triggers `sdd token-log --command implement` "
        "automatically (silently, if token-pricing.yml isn't configured)."
    )


@hooks_command.command("status")
def hooks_status():
    """Report whether the post-commit token-logging hook is installed."""
    root = Path(".")
    hooks_dir = _git_hooks_dir(root)
    if hooks_dir is None:
        console.print("[dim]Not a git repository -- nothing to check.[/dim]")
        return
    target = hooks_dir / "post-commit"
    if not target.exists():
        console.print(
            "[dim]No post-commit hook installed. Run `sdd hooks install` to "
            "add automatic per-commit token usage logging.[/dim]"
        )
    elif _is_ours(target):
        console.print(f"[green]✓[/green]  sdd token-log hook installed at {target}")
    else:
        console.print(
            f"[yellow]·  A post-commit hook exists at {target} but wasn't "
            "installed by sdd.[/yellow]"
        )


@hooks_command.command("uninstall")
def hooks_uninstall():
    """Remove the post-commit hook, but only if sdd installed it -- never
    touches a hook it didn't write."""
    root = Path(".")
    hooks_dir = _git_hooks_dir(root)
    target = hooks_dir / "post-commit" if hooks_dir else None
    if not target or not target.exists():
        console.print("[dim]No post-commit hook to remove.[/dim]")
        return
    if not _is_ours(target):
        console.print(
            f"[yellow]·  {target} wasn't installed by sdd -- leaving it alone.[/yellow]"
        )
        raise SystemExit(2)
    target.unlink()
    console.print(f"[green]✓[/green]  Removed {target}.")
