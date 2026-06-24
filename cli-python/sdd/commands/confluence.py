from __future__ import annotations
import json
from pathlib import Path
import click
from rich.console import Console

from sdd.utils.atlassian_auth import load_profile, build_session
from sdd.utils.integrations import load_integrations
from sdd.utils.confluence_client import ConfluenceClient
from sdd.utils.md_to_cf import md_to_storage
from sdd.utils.cf_to_md import cf_to_md
from sdd.utils.manifest import read_manifest

console = Console()

_DRAFTS_FILE = Path(".specify") / ".confluence-drafts.json"

_CONTEXT_PAGE_TITLE = "{project} — Context: {feature}"


def _load_drafts() -> dict:
    if _DRAFTS_FILE.exists():
        return json.loads(_DRAFTS_FILE.read_text())
    return {}


def _save_drafts(drafts: dict) -> None:
    _DRAFTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _DRAFTS_FILE.write_text(json.dumps(drafts, indent=2))


def _resolve_doc_path(doc: str, feature: str) -> Path:
    """Return local file path for a doc key."""
    if doc == "context":
        return Path(".specify") / "contexts" / f"{feature}.md"
    return Path(".specify") / "features" / feature / f"{doc}.md"


def _resolve_page_title(doc: str, project_name: str, feature: str,
                         page_map: dict) -> str:
    if doc == "context":
        return _CONTEXT_PAGE_TITLE.replace("{project}", project_name).replace("{feature}", feature)
    template = page_map.get(doc, f"{{project}} — {doc.upper()}")
    return template.replace("{project}", project_name)


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


@confluence_command.command("draft")
@click.option("--doc", required=True,
              help="Document type: context, brd, uc, srd, design, lld, security, ...")
@click.option("--profile", default=None)
@click.option("--feature", default=None, help="Feature name (default: from manifest.yml)")
@click.option("--dry-run", is_flag=True, help="Print title and path without calling the API")
def confluence_draft(doc, profile, feature, dry_run):
    """Push a draft SDD document to Confluence and print the edit URL.

    The page URL is printed so the user can open it, fill in any
    [MISSING] sections or questions, then run `sdd confluence pull`
    to fetch the updated version back.
    """
    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    label = "  [bold cyan]SDD → Confluence Draft[/bold cyan]"
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
        console.print("  [red]✗  No confluence: section in .specify/integrations.yml[/red]")
        raise SystemExit(1)

    cf_cfg = cfg.confluence
    manifest = read_manifest() or {}
    proj = manifest.get("project") or {}
    project_name = proj.get("name", "Project")
    feature_name = feature or proj.get("feature", "")

    doc_path = _resolve_doc_path(doc, feature_name)
    if not doc_path.exists():
        console.print(f"  [red]✗  File not found: {doc_path}[/red]")
        console.print("  [dim]Generate the document first, then run this command.[/dim]")
        raise SystemExit(1)

    title = _resolve_page_title(doc, project_name, feature_name, cf_cfg.page_map)

    console.print(f"  Doc      : [cyan]{doc}[/cyan]  ({doc_path})")
    console.print(f"  Title    : [cyan]{title}[/cyan]")
    console.print(f"  Space    : [cyan]{cf_cfg.space_key}[/cyan]")
    console.print()

    if dry_run:
        console.print("  [dim]would push draft page to Confluence[/dim]")
        console.print()
        return

    try:
        prof = load_profile(profile or cfg.profile)
        session = build_session(prof)
    except Exception as e:
        console.print(f"  [red]✗  Auth error: {e}[/red]")
        raise SystemExit(1)

    client = ConfluenceClient(session, prof.base_url)
    body = md_to_storage(doc_path.read_text())

    try:
        page, created = client.upsert_page(
            cf_cfg.space_key, title, body, cf_cfg.parent_page_id
        )
    except Exception as e:
        console.print(f"  [red]✗  Confluence error: {e}[/red]")
        raise SystemExit(1)

    page_id = page.get("id", "")
    web_ui = page.get("_links", {}).get("webui", "")
    edit_url = f"{prof.base_url}/wiki{web_ui}" if web_ui else ""

    # Persist page_id so `sdd confluence pull` can find it later
    drafts = _load_drafts()
    drafts[doc] = {"page_id": page_id, "title": title}
    _save_drafts(drafts)

    action = "[green]created[/green]" if created else "[dim]updated[/dim]"
    console.print(f"  {action}  [bold]{title}[/bold]")
    if edit_url:
        console.print(f"  URL      : [underline cyan]{edit_url}[/underline cyan]")
    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("  [bold green]Draft pushed![/bold green]  Open the URL above, fill in any")
    console.print("  [MISSING] sections or answer the questions, then run:")
    console.print()
    console.print(f"      [bold]sdd confluence pull --doc {doc}[/bold]")
    console.print()
    console.print("  to pull your edits back into the local file.")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()


@confluence_command.command("pull")
@click.option("--doc", required=True,
              help="Document type: context, brd, uc, srd, design, lld, security, ...")
@click.option("--profile", default=None)
@click.option("--feature", default=None, help="Feature name (default: from manifest.yml)")
@click.option("--page-id", default=None, help="Confluence page ID (overrides saved value)")
def confluence_pull(doc, profile, feature, page_id):
    """Pull the latest Confluence page content back to the local SDD file.

    Run this after editing the draft page in Confluence to pull your
    changes back so the AI can continue the workflow from the updated doc.
    """
    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("  [bold cyan]Confluence → SDD Pull[/bold cyan]")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()

    try:
        cfg = load_integrations()
    except FileNotFoundError as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)

    if not cfg.confluence:
        console.print("  [red]✗  No confluence: section in .specify/integrations.yml[/red]")
        raise SystemExit(1)

    manifest = read_manifest() or {}
    proj = manifest.get("project") or {}
    feature_name = feature or proj.get("feature", "")

    # Resolve page ID: explicit flag > saved drafts file
    resolved_page_id = page_id
    if not resolved_page_id:
        drafts = _load_drafts()
        entry = drafts.get(doc)
        if entry:
            resolved_page_id = entry.get("page_id")
    if not resolved_page_id:
        console.print(
            f"  [red]✗  No page ID for '{doc}'.[/red]\n"
            "  Run [bold]sdd confluence draft --doc {doc}[/bold] first, "
            "or pass [bold]--page-id[/bold] directly."
        )
        raise SystemExit(1)

    try:
        prof = load_profile(profile or cfg.profile)
        session = build_session(prof)
    except Exception as e:
        console.print(f"  [red]✗  Auth error: {e}[/red]")
        raise SystemExit(1)

    client = ConfluenceClient(session, prof.base_url)

    console.print(f"  Fetching page [cyan]{resolved_page_id}[/cyan] from Confluence...")
    try:
        page = client.get_page_with_body(resolved_page_id)
    except Exception as e:
        console.print(f"  [red]✗  Confluence error: {e}[/red]")
        raise SystemExit(1)

    storage_body = (
        page.get("body", {}).get("storage", {}).get("value", "")
    )
    if not storage_body:
        console.print("  [red]✗  Page body is empty.[/red]")
        raise SystemExit(1)

    markdown = cf_to_md(storage_body)

    # Fetch comments (footer + inline) and append as a section the AI can read
    console.print("  Fetching comments...")
    try:
        footer_comments  = client.get_page_comments(resolved_page_id)
        inline_comments  = client.get_inline_comments(resolved_page_id)
        all_comments     = footer_comments + inline_comments
    except Exception:
        all_comments = []

    if all_comments:
        lines = [
            "",
            "---",
            "",
            "## Confluence Comments",
            "",
            "> These comments were added in Confluence by reviewers or stakeholders.",
            "> The AI will incorporate them into the document — do not edit this section manually.",
            "",
        ]
        for i, c in enumerate(all_comments, 1):
            kind = "inline" if c["type"] == "inline" else "comment"
            lines.append(f"### {kind.capitalize()} {i} — {c['author']} ({c['created']})")
            lines.append("")
            lines.append(c["text"])
            lines.append("")
        markdown = markdown + "\n" + "\n".join(lines)

    doc_path = _resolve_doc_path(doc, feature_name)
    doc_path.parent.mkdir(parents=True, exist_ok=True)

    old_text = doc_path.read_text() if doc_path.exists() else ""
    doc_path.write_text(markdown + "\n")

    body_lines   = len(cf_to_md(storage_body).splitlines())
    comment_count = len(all_comments)
    console.print(f"  [green]✓[/green]  Saved to [bold]{doc_path}[/bold]")
    console.print(f"  Body     : {body_lines} lines")
    if comment_count:
        console.print(f"  Comments : [yellow]{comment_count}[/yellow] (included for AI review)")
    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("  [bold green]Pull complete![/bold green]  The local file is now up to date.")
    if comment_count:
        console.print(f"  [yellow]{comment_count} Confluence comment(s)[/yellow] included —")
        console.print("  tell the AI 'done' and it will incorporate them.")
    if doc == "context":
        console.print("  Say [bold]'done'[/bold] in chat — the AI will read the updates")
        console.print("  and comments, then continue.")
    else:
        console.print(f"  Say [bold]'done'[/bold] in chat to resume the SDD workflow.")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()
