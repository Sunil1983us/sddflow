from __future__ import annotations
import re
import subprocess
from pathlib import Path
import click
from rich.console import Console

from sdd.utils.atlassian_auth import load_profile, build_session
from sdd.utils.integrations import load_integrations
from sdd.utils.jira_client import JiraClient
from sdd.utils.sdd_parser import parse_tasks
from sdd.utils.manifest import read_manifest
from sdd.utils.validate import safe_feature_path
from sdd.utils.git_host import detect_host, get_provider, PrCreateError

console = Console()


def _slug(title: str) -> str:
    s = re.sub(r'[^a-z0-9\s-]', '', title.lower())
    s = re.sub(r'\s+', '-', s.strip())
    return s[:50].rstrip('-')


def _run(cmd: list[str]) -> tuple[int, str, str]:
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


@click.group()
def pr_command():
    """PR automation — create branches and PRs linked to Jira tasks."""


@pr_command.command("create")
@click.option("--task",    required=True, help="Task ID, e.g. TASK-001")
@click.option("--base",    default="main", show_default=True,
              help="Base branch for the PR")
@click.option("--profile", default=None)
@click.option("--feature", default=None)
def pr_create(task, base, profile, feature):
    """Create a git branch and PR for a task, linked back to Jira."""
    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print(f"  [bold cyan]PR Create[/bold cyan] — {task.upper()}")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()

    try:
        cfg = load_integrations()
    except FileNotFoundError as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)

    manifest     = read_manifest() or {}
    proj         = manifest.get("project") or {}
    feature_name = feature or proj.get("feature", "")

    # ── Find task in tasks.md ─────────────────────────────────────────────────
    try:
        features_dir = safe_feature_path(Path(".specify") / "features", feature_name)
    except ValueError as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)
    tasks        = parse_tasks(features_dir)
    matched      = [t for t in tasks if t.id.upper() == task.upper()]
    if not matched:
        console.print(f"  [red]✗  {task.upper()} not found in tasks.md[/red]")
        raise SystemExit(1)
    sdd_task = matched[0]

    # ── Look up Jira issue ────────────────────────────────────────────────────
    jira_key: str | None = None
    jira_url: str | None = None
    jira_client = None
    if cfg.jira:
        try:
            prof       = load_profile(profile or cfg.profile)
            session    = build_session(prof)
            jira_client = JiraClient(session, prof.base_url)
            issue      = jira_client.find_by_label(
                cfg.jira.project_key, f"sdd:{task.upper()}"
            )
            if issue:
                jira_key = issue["key"]
                jira_url = f"{prof.base_url}/browse/{jira_key}"
        except Exception as e:
            console.print(f"  [dim]·  Jira lookup skipped: {e}[/dim]")

    # ── Create git branch ─────────────────────────────────────────────────────
    branch_pattern = (
        cfg.pr_automation.branch_pattern
        if cfg.pr_automation else "feature/{task_id}-{slug}"
    )
    branch_name = branch_pattern.format(
        task_id=task.lower(),
        slug=_slug(sdd_task.title),
    )

    code, _, err = _run(["git", "checkout", "-b", branch_name])
    if code != 0:
        console.print(f"  [red]✗  Could not create branch '{branch_name}': {err}[/red]")
        raise SystemExit(1)
    console.print(f"  [green]✓[/green]  Branch: [cyan]{branch_name}[/cyan]")

    code, _, err = _run(["git", "push", "-u", "origin", branch_name])
    if code != 0:
        console.print(f"  [yellow]·[/yellow]  Push failed (push manually): {err}")
    else:
        console.print(f"  [green]✓[/green]  Pushed to origin")

    # ── Build PR content ──────────────────────────────────────────────────────
    title_pattern = (
        cfg.pr_automation.pr_title_pattern
        if cfg.pr_automation else "feat({task_id}): {title}"
    )
    pr_title = title_pattern.format(
        task_id=task.upper(),
        title=sdd_task.title,
    )

    jira_section = ""
    if jira_key and jira_url:
        jira_section = f"## Jira\n[{jira_key}]({jira_url}) — {sdd_task.title}\n\n"

    ac_block = (
        "\n".join(f"- [ ] {ac}" for ac in sdd_task.acceptance_criteria)
        or "- [ ] See task description"
    )
    satisfies = ", ".join(sdd_task.satisfies) if sdd_task.satisfies else "—"
    story_ref = f"Story: {sdd_task.story_id}  \n" if sdd_task.story_id else ""

    # ── Pre-review summary (if pre_review enabled and summary exists) ─────────
    pre_review_section = ""
    if cfg.code_review.enabled and cfg.code_review.pre_review:
        summary_path = features_dir / f".pre-review-{task.lower()}.md"
        if summary_path.exists():
            pre_review_section = f"\n## Pre-Review\n\n{summary_path.read_text().strip()}\n\n"
            console.print(f"  [green]✓[/green]  Pre-review summary included")
        else:
            console.print(
                f"  [yellow]⚠[/yellow]  Pre-review enabled but not run for {task.upper()}. "
                "Run [cyan]/pre-review[/cyan] first, or set "
                "[cyan]code_review.pre_review: false[/cyan] to skip."
            )

    pr_body = (
        f"{jira_section}"
        f"## What this implements\n\n"
        f"{sdd_task.description or sdd_task.title}\n\n"
        f"## Acceptance Criteria\n\n"
        f"{ac_block}\n\n"
        f"## Traceability\n\n"
        f"{story_ref}"
        f"Satisfies: {satisfies}\n"
        f"{pre_review_section}"
    )

    # ── Create PR via the detected git host's provider ────────────────────────
    # detect_host() reads `git remote get-url origin` and classifies it as
    # github | bitbucket | gitlab | azure | unknown — see utils/git_host.py.
    # Every host below this point only differs in how create_pr() is
    # implemented; branch/push, PR title/body, and the Jira comment-back are
    # identical regardless of where the repo is hosted.
    remote_info = detect_host()
    provider    = get_provider(remote_info)

    try:
        pr_url = provider.create_pr(pr_title, pr_body, base, branch_name)
    except PrCreateError as e:
        console.print()
        console.print(f"  [yellow]{provider.name}: {e} — create the PR manually with:[/yellow]")
        console.print(f"\n  [bold]Title:[/bold] {pr_title}")
        console.print(f"\n  [bold]Body:[/bold]\n{pr_body}")
        console.print(f"\n  Branch [cyan]{branch_name}[/cyan] is already pushed to origin.")
        console.print()
        return

    console.print(f"  [green]✓[/green]  PR ({provider.name}): [cyan]{pr_url}[/cyan]")

    # ── Update Jira ───────────────────────────────────────────────────────────
    if jira_key and jira_client:
        try:
            jira_client.add_comment(jira_key, f"PR created: {pr_url}")
            console.print(f"  [green]✓[/green]  Jira [{jira_key}] updated with PR link")
        except Exception:
            console.print(f"  [dim]·  Could not update Jira (PR still created)[/dim]")

    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print(f"  [bold green]PR created![/bold green]")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()
