from __future__ import annotations
import re
from pathlib import Path
import click
import yaml
from rich.console import Console

from sdd.utils.atlassian_auth import load_profile, build_session
from sdd.utils.integrations import load_integrations, JiraConfig
from sdd.utils.jira_client import JiraClient
from sdd.utils.sdd_parser import parse_stories, parse_tasks, Story, Task
from sdd.utils.manifest import read_manifest
from sdd.utils.validate import safe_feature_path

console = Console()

_LEVELS = ["epic", "story", "task", "chg", "all"]


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


def parse_changeset(features_dir: Path, cr_id: str) -> list[dict]:
    """Parse the §4 CHG-NNN implementation-tasks table from a changeset
    record (.specify/features/{feature}/changesets/{cr_id}.md), written by
    /change Step 7. Returns a list of dicts: sdd_id, description,
    satisfies, est_lines. Raises FileNotFoundError if the changeset
    doesn't exist -- callers turn that into a clean CLI error."""
    path = features_dir / "changesets" / f"{cr_id}.md"
    if not path.exists():
        raise FileNotFoundError(f"Changeset not found: {path}")
    text = path.read_text()
    chg_tasks = []
    for m in re.finditer(
        r"\|\s*(CHG-\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*~?(\d+)[^|]*\|",
        text,
    ):
        chg_tasks.append({
            "sdd_id":      m.group(1).strip(),
            "description": m.group(2).strip(),
            "satisfies":   m.group(3).strip(),
            "est_lines":   int(m.group(4)),
        })
    return chg_tasks


@click.group()
def jira_command():
    """Push SDD tasks and stories to Jira (Feature → Story → Task)."""


@jira_command.command("push")
@click.option("--profile", default=None, help="Profile from ~/.sdd/config.yml")
@click.option("--feature", default=None, help="Feature name (default: from manifest.yml)")
@click.option("--level", type=click.Choice(_LEVELS), default="all",
              help="SDD level to push (default: all -- Feature/Epic, Story, and Task)")
@click.option("--cr", default=None, metavar="CR-NNN",
              help="Change request ID -- required when --level chg")
@click.option("--dry-run", is_flag=True, help="Print plan without calling the API")
def jira_push(profile, feature, level, cr, dry_run):
    """Create or update Jira issues from stories.md and tasks.md.

    --level lets you push progressively at each SDLC stage, matching
    /jira-push's staged workflow (epic after BRD, story after Use
    Cases/SRD, task after /task, chg after /change) instead of always
    pushing everything at once. Parent links for a level pushed on its
    own are found live via Jira labels -- no local state file is needed
    for correctness; run --level epic before --level story before
    --level task for parent links to attach, or just use --level all.
    """
    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    label = "  [bold cyan]SDD → Jira[/bold cyan]"
    if level != "all":
        label += f"  [dim](level: {level})[/dim]"
    if dry_run:
        label += "  [yellow](dry run)[/yellow]"
    console.print(label)
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()

    if level == "chg" and not cr:
        console.print("  [red]✗  --cr CR-NNN is required when --level chg[/red]")
        raise SystemExit(1)

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

    if level == "chg":
        try:
            chg_tasks = parse_changeset(features_dir, cr)
        except FileNotFoundError as e:
            console.print(f"  [red]✗  {e}[/red]")
            raise SystemExit(1)
        if not chg_tasks:
            console.print(f"  [red]✗  No CHG tasks found in changesets/{cr}.md §4.[/red]")
            raise SystemExit(1)

    stories = parse_stories(features_dir)
    tasks   = parse_tasks(features_dir)

    if level in ("story", "task", "all") and not stories and not tasks:
        console.print("  [yellow]  No stories or tasks found — run /task first.[/yellow]")
        console.print()
        return

    jira_cfg = cfg.jira
    h = jira_cfg.issue_hierarchy
    console.print(f"  Project  : [cyan]{project_name}[/cyan]")
    console.print(f"  Feature  : [cyan]{feature_name}[/cyan]")
    if level in ("story", "all"):
        console.print(f"  Stories  : [cyan]{len(stories)}[/cyan]")
    if level in ("task", "all"):
        console.print(f"  Tasks    : [cyan]{len(tasks)}[/cyan]")
    if level == "chg":
        console.print(f"  CHG      : [cyan]{len(chg_tasks)}[/cyan]  [dim]({cr})[/dim]")
    console.print(
        f"  Jira     : [cyan]{jira_cfg.project_key}[/cyan]  "
        f"[dim]{h['feature']} → {h['story']} → {h['task']}[/dim]"
    )
    console.print()

    if dry_run:
        _print_dry_run(feature_name, stories, tasks, jira_cfg, level,
                        chg_tasks if level == "chg" else None)
        return

    try:
        prof    = load_profile(profile or cfg.profile)
        session = build_session(prof)
    except Exception as e:
        console.print(f"  [red]✗  Auth error: {e}[/red]")
        raise SystemExit(1)

    client = JiraClient(session, prof.base_url)
    _push(client, feature_name, features_dir, stories, tasks, jira_cfg, level=level, cr=cr)


def _print_dry_run(feature_name: str, stories: list[Story], tasks: list[Task],
                    cfg: JiraConfig, level: str, chg_tasks: list[dict] | None) -> None:
    h = cfg.issue_hierarchy
    console.print("  [bold]Would create:[/bold]")

    if level == "chg":
        console.print(f"  ┌── [{h.get('chg', h['task'])}] CHG tasks")
        for chg in (chg_tasks or []):
            console.print(f"  │   └── {chg['sdd_id']} — {chg['description']}  "
                           f"[dim](Satisfies: {chg['satisfies']})[/dim]")
        console.print()
        return

    if level == "epic":
        console.print(f"  └── [{h['feature']}] {feature_name}")
        console.print()
        return

    console.print(f"  ┌── [{h['feature']}] {feature_name}")
    if level in ("story", "all"):
        for story in stories:
            pts = f"  {story.story_points}sp" if story.story_points else ""
            console.print(
                f"  │   ├── [{h['story']}] {story.id} — {story.title} "
                f"[dim]({story.moscow}{pts})[/dim]"
            )
            if level == "all":
                for task in [t for t in tasks if t.story_id == story.id]:
                    console.print(f"  │   │   └── [{h['task']}] {task.id} — {task.title}")
    if level == "task":
        for task in tasks:
            console.print(f"  │   └── [{h['task']}] {task.id} — {task.title}  "
                           f"[dim](Story: {task.story_id or '—'})[/dim]")
    if level == "all":
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
    """Idempotency label for a Story/Task/CHG issue, qualified by feature.

    STORY-NNN/TASK-NNN numbering restarts independently per feature (same
    as CR-NNN), so an un-qualified label like "sdd:STORY-001" would let a
    second feature's STORY-001 find and silently overwrite the first
    feature's Jira issue on push. Namespacing by feature_name keeps every
    feature's Story/Task/CHG issues distinct, matching the Feature-level
    label (f"sdd-feature:{feature_name}") which was already feature-safe.
    """
    return f"sdd:{feature_name}:{item_id}"


def _upsert_issue(client: JiraClient, project_key: str, issue_type: str,
                   summary: str, extra: dict, id_label: str,
                   base_labels: list[str]) -> tuple[str, bool]:
    """Create or update an issue keyed by an idempotency label. Shared by
    the Feature/Epic, Story, Task, and CHG steps below, and by review.py's
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


def _find_feature_key(client: JiraClient, project_key: str, feature_name: str) -> str | None:
    issue = client.find_by_label(project_key, f"sdd-feature:{feature_name}")
    return issue["key"] if issue else None


def _find_story_key(client: JiraClient, project_key: str, feature_name: str, story_id: str) -> str | None:
    issue = client.find_by_label(project_key, _item_label(feature_name, story_id))
    return issue["key"] if issue else None


def _push_epic(client: JiraClient, feature_name: str, features_dir: Path, cfg: JiraConfig) -> str:
    feature_extra = feature_extra_fields(features_dir, cfg, feature_name)
    key, created = _upsert_issue(
        client, cfg.project_key, cfg.issue_hierarchy["feature"], feature_name,
        feature_extra, f"sdd-feature:{feature_name}", cfg.labels,
    )
    _log(cfg.issue_hierarchy["feature"], key, feature_name, created)
    return key


def _push_stories(client: JiraClient, feature_name: str, stories: list[Story],
                   cfg: JiraConfig, epic_key: str | None) -> dict[str, str]:
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
        if story.satisfies and "fr_reference" in cfg.custom_fields:
            extra[cfg.custom_fields["fr_reference"]] = ", ".join(story.satisfies)
        if "moscow_priority" in cfg.custom_fields:
            extra[cfg.custom_fields["moscow_priority"]] = story.moscow

        key, created = _upsert_issue(
            client, cfg.project_key, cfg.issue_hierarchy["story"],
            f"{story.id} — {story.title}",
            extra,
            _item_label(feature_name, story.id),
            cfg.labels,
        )
        story_key_map[story.id] = key

        if epic_key:
            try:
                client.set_parent(key, epic_key, cfg.parent_field)
            except Exception:
                pass  # not all Jira project types support parent on Story

        pts = f"  {story.story_points}sp" if story.story_points else ""
        _log(cfg.issue_hierarchy["story"], key, f"{story.id}: {story.title} ({story.moscow}{pts})", created)

    return story_key_map


def _push_tasks(client: JiraClient, feature_name: str, tasks: list[Task],
                 cfg: JiraConfig, story_key_map: dict[str, str]) -> dict[str, str]:
    task_key_map: dict[str, str] = {}
    for task in tasks:
        ac_text = "; ".join(task.acceptance_criteria) if task.acceptance_criteria else ""
        description = adf_doc(
            task.description,
            f"Satisfies: {', '.join(task.satisfies)}" if task.satisfies else "",
            f"Acceptance Criteria: {ac_text}" if ac_text else "",
        )
        extra: dict = {"description": description}
        if ac_text and "acceptance_criteria" in cfg.custom_fields:
            extra[cfg.custom_fields["acceptance_criteria"]] = ac_text
        if task.satisfies and "fr_reference" in cfg.custom_fields:
            extra[cfg.custom_fields["fr_reference"]] = ", ".join(task.satisfies)

        key, created = _upsert_issue(
            client, cfg.project_key, cfg.issue_hierarchy["task"],
            f"{task.id} — {task.title}",
            extra,
            _item_label(feature_name, task.id),
            cfg.labels,
        )
        task_key_map[task.id] = key

        parent_key = story_key_map.get(task.story_id) if task.story_id else None
        if parent_key:
            try:
                client.set_parent(key, parent_key, cfg.parent_field)
            except Exception:
                pass

        story_ref = f"  [dim]→ {parent_key or '?'}[/dim]" if task.story_id else ""
        _log(cfg.issue_hierarchy["task"], key, f"{task.id}: {task.title}{story_ref}", created)

    return task_key_map


def _push_chg(client: JiraClient, feature_name: str, cfg: JiraConfig, cr_id: str,
              features_dir: Path, stories: list[Story],
              story_key_map: dict[str, str], epic_key: str | None) -> dict[str, str]:
    chg_tasks = parse_changeset(features_dir, cr_id)

    # FR-NNN -> Story Jira key, from whichever stories we know keys for
    # (either just pushed this run, or looked up live from Jira labels).
    fr_to_story: dict[str, str] = {}
    for s in stories:
        key = story_key_map.get(s.id)
        if key:
            for fr in s.satisfies:
                fr_to_story[fr] = key

    chg_issue_type = cfg.issue_hierarchy.get("chg", cfg.issue_hierarchy["task"])
    chg_key_map: dict[str, str] = {}

    for chg in chg_tasks:
        satisfies = chg["satisfies"]
        parent_key = next(
            (fr_to_story[fr] for fr in re.findall(r"FR-\d+", satisfies) if fr in fr_to_story),
            epic_key,
        )
        description = adf_doc(
            f"Change Request: {cr_id}",
            f"Satisfies: {satisfies}",
            f"Description: {chg['description']}",
        )
        extra: dict = {"description": description, "priority": {"name": "Medium"}}
        if "fr_reference" in cfg.custom_fields:
            extra[cfg.custom_fields["fr_reference"]] = satisfies

        key, created = _upsert_issue(
            client, cfg.project_key, chg_issue_type, chg["description"],
            extra, _item_label(feature_name, chg["sdd_id"]), cfg.labels,
        )
        chg_key_map[chg["sdd_id"]] = key

        if parent_key:
            try:
                client.set_parent(key, parent_key, cfg.parent_field)
            except Exception:
                pass  # not all Jira project types support parent on this issue type

        _log(chg_issue_type, key, f"{chg['sdd_id']}: {chg['description']}", created)

    return chg_key_map


def _push(client: JiraClient, feature_name: str, features_dir: Path,
          stories: list[Story], tasks: list[Task], cfg: JiraConfig,
          level: str = "all", cr: str | None = None) -> None:
    levels   = ["epic", "story", "task"] if level == "all" else [level]
    do_epic  = "epic" in levels
    do_story = "story" in levels
    do_task  = "task" in levels
    do_chg   = level == "chg"

    epic_key: str | None = None
    story_key_map: dict[str, str] = {}
    task_key_map: dict[str, str] = {}
    chg_key_map: dict[str, str] = {}

    # ── Feature / Epic ───────────────────────────────────────────────────────
    if do_epic:
        epic_key = _push_epic(client, feature_name, features_dir, cfg)
    elif do_story or do_chg:
        epic_key = _find_feature_key(client, cfg.project_key, feature_name)
        if not epic_key and do_story:
            console.print(
                "  [yellow]!  Feature/Epic not found — Stories will be created "
                "without a parent link. Run --level epic first.[/yellow]"
            )

    # ── Stories ───────────────────────────────────────────────────────────────
    if do_story:
        story_key_map = _push_stories(client, feature_name, stories, cfg, epic_key)
    elif do_task or do_chg:
        for story in stories:
            key = _find_story_key(client, cfg.project_key, feature_name, story.id)
            if key:
                story_key_map[story.id] = key

    # ── Tasks ─────────────────────────────────────────────────────────────────
    if do_task:
        task_key_map = _push_tasks(client, feature_name, tasks, cfg, story_key_map)

    # ── CHG (change-request tasks) ───────────────────────────────────────────
    if do_chg:
        chg_key_map = _push_chg(client, feature_name, cfg, cr, features_dir,
                                 stories, story_key_map, epic_key)

    _save_keys_summary(feature_name, epic_key, story_key_map, task_key_map, cr, chg_key_map)

    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("  [bold green]Jira push complete![/bold green]")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()


def _keys_path(feature_name: str) -> Path:
    return Path("docs") / "jira" / feature_name / "keys.yml"


def _save_keys_summary(feature_name: str, epic_key: str | None,
                        story_key_map: dict[str, str], task_key_map: dict[str, str],
                        cr: str | None, chg_key_map: dict[str, str]) -> None:
    """Best-effort human-readable snapshot of the Jira keys created for this
    feature so far -- for reference only (e.g. skimming without a live
    Jira query, or for tooling that wants a local index). Never read back
    by `sdd jira push` itself: every parent-link and idempotency decision
    is always re-derived live from Jira's sdd-feature:*/sdd:* labels, so a
    stale or deleted keys.yml never affects a future push's correctness.
    A write failure here (e.g. read-only filesystem) is swallowed rather
    than failing an otherwise-successful Jira push."""
    if not (epic_key or story_key_map or task_key_map or chg_key_map):
        return
    path = _keys_path(feature_name)
    existing: dict = {}
    if path.exists():
        try:
            existing = yaml.safe_load(path.read_text()) or {}
        except Exception:
            existing = {}
    if epic_key:
        existing["epic"] = epic_key
    if story_key_map:
        stories = existing.get("stories") or {}
        stories.update(story_key_map)
        existing["stories"] = stories
    if task_key_map:
        task_d = existing.get("tasks") or {}
        task_d.update(task_key_map)
        existing["tasks"] = task_d
    if chg_key_map:
        chg_d = existing.setdefault("chg_tasks", {})
        chg_d.setdefault(cr, {}).update(chg_key_map)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Local record of Jira keys created by `sdd jira push` -- for human/\n"
            "# tooling reference only. Not read by sdd jira push itself: parent-\n"
            "# linking and idempotency are always re-derived live from Jira's\n"
            "# sdd-feature:*/sdd:* labels, so this file can be deleted or go stale\n"
            "# without affecting future pushes.\n"
            + yaml.dump(existing, default_flow_style=False, sort_keys=False, allow_unicode=True)
        )
    except Exception:
        pass


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
