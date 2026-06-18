from __future__ import annotations
from pathlib import Path
import click
from rich.console import Console

from sdd.utils.atlassian_auth import load_profile, build_session
from sdd.utils.integrations import load_integrations, JiraConfig
from sdd.utils.jira_client import JiraClient
from sdd.utils.sdd_parser import parse_stories, parse_tasks, Story, Task
from sdd.utils.manifest import read_manifest

console = Console()


@click.group()
def jira_command():
    """Push SDD tasks and stories to Jira (Feature → Story → Task)."""


@jira_command.command("push")
@click.option("--profile", default=None, help="Profile from ~/.sdd/config.yml")
@click.option("--feature", default=None, help="Feature name (default: from manifest.yml)")
@click.option("--dry-run", is_flag=True, help="Print plan without calling the API")
def jira_push(profile, feature, dry_run):
    """Create or update Jira issues from stories.md and tasks.md."""
    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    label = "  [bold cyan]SDD → Jira[/bold cyan]"
    if dry_run:
        label += "  [yellow](dry run)[/yellow]"
    console.print(label)
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()

    try:
        cfg = load_integrations()
    except FileNotFoundError as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)

    if not cfg.jira:
        console.print("  [red]✗  No jira: section in .specify/integrations.yml[/red]")
        raise SystemExit(1)

    manifest     = read_manifest() or {}
    proj         = manifest.get("project") or {}
    project_name = proj.get("name", "Unknown Project")
    feature_name = feature or proj.get("feature", "")

    features_dir = Path(".specify") / "features" / feature_name
    if not features_dir.exists():
        console.print(f"  [red]✗  Feature directory not found: {features_dir}[/red]")
        raise SystemExit(1)

    stories = parse_stories(features_dir)
    tasks   = parse_tasks(features_dir)

    if not stories and not tasks:
        console.print("  [yellow]  No stories or tasks found — run /task first.[/yellow]")
        console.print()
        return

    jira_cfg = cfg.jira
    h = jira_cfg.issue_hierarchy
    console.print(f"  Project  : [cyan]{project_name}[/cyan]")
    console.print(f"  Feature  : [cyan]{feature_name}[/cyan]")
    console.print(f"  Stories  : [cyan]{len(stories)}[/cyan]")
    console.print(f"  Tasks    : [cyan]{len(tasks)}[/cyan]")
    console.print(
        f"  Jira     : [cyan]{jira_cfg.project_key}[/cyan]  "
        f"[dim]{h['feature']} → {h['story']} → {h['task']}[/dim]"
    )
    console.print()

    if dry_run:
        _print_dry_run(feature_name, stories, tasks, jira_cfg)
        return

    try:
        prof    = load_profile(profile or cfg.profile)
        session = build_session(prof)
    except Exception as e:
        console.print(f"  [red]✗  Auth error: {e}[/red]")
        raise SystemExit(1)

    client = JiraClient(session, prof.base_url)
    _push(client, feature_name, stories, tasks, jira_cfg)


def _print_dry_run(feature_name: str, stories: list[Story],
                   tasks: list[Task], cfg: JiraConfig) -> None:
    h = cfg.issue_hierarchy
    console.print("  [bold]Would create:[/bold]")
    console.print(f"  ┌── [{h['feature']}] {feature_name}")
    for story in stories:
        pts = f"  {story.story_points}sp" if story.story_points else ""
        console.print(
            f"  │   ├── [{h['story']}] {story.id} — {story.title} "
            f"[dim]({story.moscow}{pts})[/dim]"
        )
        for task in [t for t in tasks if t.story_id == story.id]:
            console.print(f"  │   │   └── [{h['task']}] {task.id} — {task.title}")
    orphans = [t for t in tasks if not any(s.id == t.story_id for s in stories)]
    if orphans:
        console.print("  │")
        console.print("  │   [yellow](orphaned — no matching Story):[/yellow]")
        for task in orphans:
            console.print(
                f"  │   └── [{h['task']}] {task.id} — {task.title}  "
                f"[dim](Story: {task.story_id})[/dim]"
            )
    console.print()


def _push(client: JiraClient, feature_name: str, stories: list[Story],
          tasks: list[Task], cfg: JiraConfig) -> None:
    project_key = cfg.project_key
    h = cfg.issue_hierarchy

    def _upsert(issue_type: str, summary: str, extra: dict,
                id_label: str) -> tuple[str, bool]:
        existing = client.find_by_label(project_key, id_label)
        labels = cfg.labels + [id_label]
        fields = {
            "project":   {"key": project_key},
            "issuetype": {"name": issue_type},
            "summary":   summary,
            "labels":    labels,
            **extra,
        }
        if existing:
            key = existing["key"]
            client.update_issue(key, fields)
            return key, False
        result = client.create_issue(fields)
        return result["key"], True

    # ── Feature ───────────────────────────────────────────────────────────────
    feature_key, created = _upsert(
        h["feature"], feature_name, {},
        f"sdd-feature:{feature_name}",
    )
    _log(h["feature"], feature_key, feature_name, created)

    # ── Stories ───────────────────────────────────────────────────────────────
    story_key_map: dict[str, str] = {}
    for story in stories:
        extra: dict = {
            "priority": {"name": cfg.priority_map.get(story.moscow, "Medium")},
        }
        if story.story_points and "story_points" in cfg.custom_fields:
            extra[cfg.custom_fields["story_points"]] = story.story_points
        if story.acceptance_criteria and "acceptance_criteria" in cfg.custom_fields:
            extra[cfg.custom_fields["acceptance_criteria"]] = "\n".join(
                story.acceptance_criteria
            )

        key, created = _upsert(
            h["story"],
            f"{story.id} — {story.title}",
            extra,
            f"sdd:{story.id}",
        )
        story_key_map[story.id] = key

        # Link Story → Feature
        try:
            client.set_parent(key, feature_key, cfg.parent_field)
        except Exception:
            pass  # not all Jira project types support parent on Story

        pts = f"  {story.story_points}sp" if story.story_points else ""
        _log(h["story"], key, f"{story.id}: {story.title} ({story.moscow}{pts})", created)

    # ── Tasks ─────────────────────────────────────────────────────────────────
    for task in tasks:
        extra = {}
        if task.description:
            extra["description"] = {
                "type": "doc", "version": 1,
                "content": [{"type": "paragraph", "content": [
                    {"type": "text", "text": task.description}
                ]}],
            }

        key, created = _upsert(
            h["task"],
            f"{task.id} — {task.title}",
            extra,
            f"sdd:{task.id}",
        )

        # Link Task → Story
        if task.story_id and task.story_id in story_key_map:
            try:
                client.set_parent(key, story_key_map[task.story_id], cfg.parent_field)
            except Exception:
                pass

        story_ref = (
            f"  [dim]→ {story_key_map.get(task.story_id, '?')}[/dim]"
            if task.story_id else ""
        )
        _log(h["task"], key, f"{task.id}: {task.title}{story_ref}", created)

    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("  [bold green]Jira push complete![/bold green]")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()


def _log(issue_type: str, key: str, title: str, created: bool) -> None:
    action = "[green]created[/green]" if created else "[dim]updated[/dim]"
    console.print(f"  {action}  [{issue_type}] {key} — {title}")


# ── sdd jira sync ─────────────────────────────────────────────────────────────

@jira_command.command("sync")
@click.option("--profile", default=None)
@click.option("--feature", default=None)
def jira_sync(profile, feature):
    """Pull Jira issue statuses back and show alongside task IDs."""
    console.print()
    console.print("  [bold cyan]SDD ← Jira[/bold cyan]  (status pull-back)")
    console.print()

    try:
        cfg     = load_integrations()
        prof    = load_profile(profile or cfg.profile)
        session = build_session(prof)
    except Exception as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)

    manifest     = read_manifest() or {}
    feature_name = feature or (manifest.get("project") or {}).get("feature", "")
    features_dir = Path(".specify") / "features" / feature_name

    tasks   = parse_tasks(features_dir)
    client  = JiraClient(session, prof.base_url)
    project_key = cfg.jira.project_key  # type: ignore[union-attr]

    console.print(f"  {'TASK ID':<12} {'Jira Key':<14} Status")
    console.print(f"  {'─'*12} {'─'*14} {'─'*20}")

    for task in tasks:
        issue = client.find_by_label(project_key, f"sdd:{task.id}")
        if issue:
            status = (
                issue.get("fields", {}).get("status", {}).get("name", "Unknown")
            )
            console.print(f"  {task.id:<12} {issue['key']:<14} [cyan]{status}[/cyan]")
        else:
            console.print(f"  {task.id:<12} {'—':<14} [dim]not pushed[/dim]")

    console.print()
