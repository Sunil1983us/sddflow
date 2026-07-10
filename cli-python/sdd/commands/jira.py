from __future__ import annotations
import re
from pathlib import Path
import click
from rich.console import Console

from sdd.utils.atlassian_auth import load_profile, build_session
from sdd.utils.integrations import load_integrations, JiraConfig
from sdd.utils.jira_client import JiraClient
from sdd.utils.sdd_parser import parse_stories, parse_tasks, Story, Task
from sdd.utils.manifest import read_manifest
from sdd.utils.validate import safe_feature_path

console = Console()


# ── ADF (Atlassian Document Format) helpers ────────────────────────────────────

def _adf_paragraph(text: str) -> dict:
    return {"type": "paragraph", "content": [{"type": "text", "text": str(text)}]}


def adf_doc(*paragraphs: str, bullet_list: list[str] | None = None) -> dict:
    """Build a minimal ADF doc from plain-text paragraphs plus an optional
    bullet list. Blank/falsy paragraphs are skipped so callers can pass
    conditional lines (e.g. f"Risk: {risk}" if risk else "") directly."""
    content = [_adf_paragraph(p) for p in paragraphs if p and str(p).strip()]
    if bullet_list:
        content.append({
            "type": "bulletList",
            "content": [{"type": "listItem", "content": [_adf_paragraph(item)]}
                        for item in bullet_list if item],
        })
    return {"type": "doc", "version": 1, "content": content or [_adf_paragraph(" ")]}


def parse_brd_objectives(features_dir: Path) -> list[str]:
    """Extract up to 10 BO-NNN objective lines from brd.md, for the
    Feature/Epic issue's description. Returns [] if brd.md doesn't exist
    yet (e.g. called before /specify-brd has run) -- callers fall back to
    a placeholder line rather than failing."""
    path = features_dir / "brd.md"
    if not path.exists():
        return []
    text = path.read_text()
    objectives = []
    for m in re.finditer(r"(BO-\d+[^\n]*)", text):
        line = re.sub(r"[|*`_]", "", m.group(1)).strip()
        if line and len(line) > 5:
            objectives.append(line)
    return objectives[:10]


def feature_extra_fields(features_dir: Path, cfg: JiraConfig, feature_name: str) -> dict:
    """Extra fields for the top-level Feature/Epic issue: a real
    description built from brd.md's Business Objectives (falls back to a
    pointer at brd.md if none are parsed yet), High priority, and the
    Epic Name custom field for classic/company-managed Jira projects
    (only if custom_fields.epic_name is configured)."""
    objectives = parse_brd_objectives(features_dir)
    extra: dict = {
        "description": adf_doc(
            "Business Objectives:",
            bullet_list=objectives if objectives else ["See brd.md for full objectives."],
        ),
        "priority": {"name": "High"},
    }
    epic_name_field = cfg.custom_fields.get("epic_name")
    if epic_name_field:
        extra[epic_name_field] = feature_name
    return extra


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

    try:
        features_dir = safe_feature_path(Path(".specify") / "features", feature_name)
    except ValueError as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)
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
    _push(client, feature_name, features_dir, stories, tasks, jira_cfg)


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


def _item_label(feature_name: str, item_id: str) -> str:
    """Idempotency label for a Story/Task issue, qualified by feature.

    STORY-NNN/TASK-NNN numbering restarts independently per feature (same
    as CR-NNN), so an un-qualified label like "sdd:STORY-001" would let a
    second feature's STORY-001 find and silently overwrite the first
    feature's Jira issue on push. Namespacing by feature_name keeps every
    feature's Story/Task issues distinct, matching the Feature-level
    label (f"sdd-feature:{feature_name}") which was already feature-safe.
    """
    return f"sdd:{feature_name}:{item_id}"


def _upsert_issue(client: JiraClient, project_key: str, issue_type: str,
                   summary: str, extra: dict, id_label: str,
                   base_labels: list[str]) -> tuple[str, bool]:
    """Create or update an issue keyed by an idempotency label. Shared by
    the Feature/Epic, Story, and Task steps below, and by review.py's
    review-ticket Epic bootstrap (same idempotent-upsert contract)."""
    existing = client.find_by_label(project_key, id_label)
    labels = base_labels + [id_label]
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


def _push(client: JiraClient, feature_name: str, features_dir: Path,
          stories: list[Story], tasks: list[Task], cfg: JiraConfig) -> None:
    project_key = cfg.project_key
    h = cfg.issue_hierarchy

    # ── Feature / Epic ───────────────────────────────────────────────────────
    feature_extra = feature_extra_fields(features_dir, cfg, feature_name)
    feature_key, created = _upsert_issue(
        client, project_key, h["feature"], feature_name, feature_extra,
        f"sdd-feature:{feature_name}", cfg.labels,
    )
    _log(h["feature"], feature_key, feature_name, created)

    # ── Stories ───────────────────────────────────────────────────────────────
    story_key_map: dict[str, str] = {}
    for story in stories:
        ac_text = "; ".join(story.acceptance_criteria) if story.acceptance_criteria else ""
        description = adf_doc(
            story.description,
            f"Satisfies: {', '.join(story.satisfies)}" if story.satisfies else "",
            f"Acceptance Criteria: {ac_text}" if ac_text else "",
        )
        extra: dict = {
            "priority": {"name": cfg.priority_map.get(story.moscow, "Medium")},
            "description": description,
        }
        if story.story_points and "story_points" in cfg.custom_fields:
            extra[cfg.custom_fields["story_points"]] = story.story_points
        if ac_text and "acceptance_criteria" in cfg.custom_fields:
            extra[cfg.custom_fields["acceptance_criteria"]] = ac_text

        key, created = _upsert_issue(
            client, project_key, h["story"],
            f"{story.id} — {story.title}",
            extra,
            _item_label(feature_name, story.id),
            cfg.labels,
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
        ac_text = "; ".join(task.acceptance_criteria) if task.acceptance_criteria else ""
        description = adf_doc(
            task.description,
            f"Satisfies: {', '.join(task.satisfies)}" if task.satisfies else "",
            f"Acceptance Criteria: {ac_text}" if ac_text else "",
        )
        extra = {"description": description}
        if ac_text and "acceptance_criteria" in cfg.custom_fields:
            extra[cfg.custom_fields["acceptance_criteria"]] = ac_text

        key, created = _upsert_issue(
            client, project_key, h["task"],
            f"{task.id} — {task.title}",
            extra,
            _item_label(feature_name, task.id),
            cfg.labels,
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

    if not cfg.jira:
        console.print("  [red]✗  No jira: section in .specify/integrations.yml[/red]")
        raise SystemExit(1)

    try:
        features_dir = safe_feature_path(Path(".specify") / "features", feature_name)
    except ValueError as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)

    tasks   = parse_tasks(features_dir)
    client  = JiraClient(session, prof.base_url)
    project_key = cfg.jira.project_key

    console.print(f"  {'TASK ID':<12} {'Jira Key':<14} Status")
    console.print(f"  {'─'*12} {'─'*14} {'─'*20}")

    for task in tasks:
        issue = client.find_by_label(project_key, _item_label(feature_name, task.id))
        if issue:
            status = (
                issue.get("fields", {}).get("status", {}).get("name", "Unknown")
            )
            console.print(f"  {task.id:<12} {issue['key']:<14} [cyan]{status}[/cyan]")
        else:
            console.print(f"  {task.id:<12} {'—':<14} [dim]not pushed[/dim]")

    console.print()
