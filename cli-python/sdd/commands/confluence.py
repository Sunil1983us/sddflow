from __future__ import annotations
from pathlib import Path
import click
from rich.console import Console

from sdd.utils.atlassian_auth import load_profile, build_session
from sdd.utils.integrations import load_integrations
from sdd.utils.confluence_client import ConfluenceClient
from sdd.utils.md_to_cf import md_to_storage
from sdd.utils.manifest import read_manifest

console = Console()


@click.group()
def confluence_command():
    """Push SDD documents to Confluence."""


@confluence_command.command("push")
@click.option("--profile", default=None)
@click.option("--feature", default=None, help="Feature name (default: from manifest.yml)")
@click.option("--doc",     default=None,
              help="Push a single doc only (e.g. hld, brd, arch, runbook)")
@click.option("--dry-run", is_flag=True, help="Print page titles without calling the API")
def confluence_push(profile, feature, doc, dry_run):
    """Publish SDD documents to Confluence pages (create or update)."""
    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    label = "  [bold cyan]SDD → Confluence[/bold cyan]"
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

    if not cfg.confluence:
        console.print(
            "  [red]✗  No confluence: section in .specify/integrations.yml[/red]"
        )
        raise SystemExit(1)

    cf_cfg       = cfg.confluence
    manifest     = read_manifest() or {}
    proj         = manifest.get("project") or {}
    project_name = proj.get("name", "Project")
    feature_name = feature or proj.get("feature", "")

    features_dir = Path(".specify") / "features" / feature_name
    if not features_dir.exists():
        console.print(f"  [red]✗  Feature directory not found: {features_dir}[/red]")
        raise SystemExit(1)

    # Resolve which docs to push
    page_map    = cf_cfg.page_map
    keys_to_try = [doc] if doc else list(page_map.keys())

    available: list[tuple[str, Path, str]] = []
    for key in keys_to_try:
        md_path = features_dir / f"{key}.md"
        if not md_path.exists():
            console.print(f"  [dim]·[/dim]  {key}.md not found — skipped")
            continue
        title = page_map.get(key, f"{project_name} — {key.upper()}")
        title = title.replace("{project}", project_name)
        available.append((key, md_path, title))

    if not available:
        console.print("  [yellow]  No documents found to push.[/yellow]")
        console.print()
        return

    console.print(f"  Space    : [cyan]{cf_cfg.space_key}[/cyan]")
    console.print(f"  Parent   : [cyan]{cf_cfg.parent_page_id or 'root'}[/cyan]")
    console.print(f"  Docs     : [cyan]{len(available)}[/cyan]")
    console.print()

    if dry_run:
        for key, md_path, title in available:
            console.print(f"  [dim]would push[/dim]  [cyan]{title}[/cyan]  ← {md_path}")
        console.print()
        return

    try:
        prof    = load_profile(profile or cfg.profile)
        session = build_session(prof)
    except Exception as e:
        console.print(f"  [red]✗  Auth error: {e}[/red]")
        raise SystemExit(1)

    client = ConfluenceClient(session, prof.base_url)

    for key, md_path, title in available:
        body = md_to_storage(md_path.read_text())
        try:
            page, created = client.upsert_page(
                cf_cfg.space_key, title, body, cf_cfg.parent_page_id
            )
            action = "[green]created[/green]" if created else "[dim]updated[/dim]"
            console.print(f"  {action}  [cyan]{title}[/cyan]")
            if created:
                web_ui = page.get("_links", {}).get("webui", "")
                if web_ui:
                    console.print(f"          {prof.base_url}/wiki{web_ui}")
        except Exception as e:
            console.print(f"  [red]✗  {title} — {e}[/red]")

    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("  [bold green]Confluence push complete![/bold green]")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()
