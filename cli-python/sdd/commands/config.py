from __future__ import annotations
from pathlib import Path
import yaml
import click
import requests
from rich.console import Console

from sdd.utils.atlassian_auth import (
    load_profile, build_session, save_config, store_secret, CONFIG_PATH,
)
from sdd.utils.jira_client import JiraClient
from sdd.utils.confluence_client import ConfluenceClient

console = Console()


@click.group()
def config_command():
    """Configure Atlassian credentials and project integration."""


@config_command.command("init")
def config_init():
    """Interactively create ~/.sdd/config.yml and .specify/integrations.yml."""
    import questionary

    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("  [bold cyan]SDD Config[/bold cyan] — Atlassian setup")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()

    profile_name = questionary.text("Profile name:", default="default").ask()
    base_url     = questionary.text(
        "Atlassian base URL:", default="https://myco.atlassian.net"
    ).ask()
    auth_mode = questionary.select(
        "Auth mode:",
        choices=[
            questionary.Choice(
                "basic  — Cloud (email + API token)",  value="basic"),
            questionary.Choice(
                "pat    — Server/DC (Personal Access Token)", value="pat"),
            questionary.Choice(
                "oauth2 — Cloud CI/CD (OAuth 2.0 Bearer token)", value="oauth2"),
        ],
    ).ask()

    credential_store = questionary.select(
        "How should the credential be stored?",
        choices=[
            questionary.Choice(
                "System keychain (recommended — works in any terminal or "
                "AI tool, no shell setup)",
                value="keyring"),
            questionary.Choice(
                "Environment variable (manual shell setup required)",
                value="env"),
        ],
    ).ask()

    profile: dict = {
        "auth_mode": auth_mode,
        "base_url": base_url,
        "credential_store": credential_store,
    }

    if auth_mode == "basic":
        email = questionary.text("Your Atlassian account email:").ask()
        profile["email"] = email
        if credential_store == "keyring":
            secret = questionary.password("Your Atlassian API token:").ask()
            try:
                store_secret(profile_name, secret)
            except RuntimeError as e:
                console.print(f"\n  [red]✗  {e}[/red]")
                raise SystemExit(1)
            console.print(
                "\n  [dim]Token saved to the system keychain — nothing to "
                "export, works from any terminal or AI tool on this "
                "machine.[/dim]"
            )
        else:
            api_token_env = questionary.text(
                "Name of env var holding your API token:", default="JIRA_API_TOKEN"
            ).ask()
            profile["api_token_env"] = api_token_env
            console.print(f"\n  [dim]Export [cyan]{api_token_env}[/cyan] before running sdd commands.[/dim]")

    elif auth_mode == "pat":
        if credential_store == "keyring":
            secret = questionary.password("Your Personal Access Token:").ask()
            try:
                store_secret(profile_name, secret)
            except RuntimeError as e:
                console.print(f"\n  [red]✗  {e}[/red]")
                raise SystemExit(1)
            console.print(
                "\n  [dim]Token saved to the system keychain — nothing to "
                "export, works from any terminal or AI tool on this "
                "machine.[/dim]"
            )
        else:
            pat_env = questionary.text(
                "Name of env var holding your PAT:", default="JIRA_PAT"
            ).ask()
            profile["pat_env"] = pat_env
            console.print(f"\n  [dim]Export [cyan]{pat_env}[/cyan] before running sdd commands.[/dim]")

    elif auth_mode == "oauth2":
        if credential_store == "keyring":
            secret = questionary.password("Your OAuth2 access token:").ask()
            try:
                store_secret(profile_name, secret)
            except RuntimeError as e:
                console.print(f"\n  [red]✗  {e}[/red]")
                raise SystemExit(1)
            console.print(
                "\n  [dim]Token saved to the system keychain — nothing to "
                "export, works from any terminal or AI tool on this "
                "machine.[/dim]"
            )
        else:
            access_token_env = questionary.text(
                "Name of env var holding your OAuth2 access token:",
                default="JIRA_ACCESS_TOKEN",
            ).ask()
            profile["access_token_env"] = access_token_env
            console.print(f"\n  [dim]Export [cyan]{access_token_env}[/cyan] before running sdd commands.[/dim]")

    # Merge into existing config
    if CONFIG_PATH.exists():
        existing = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    else:
        existing = {"version": "1", "profiles": {}}

    existing.setdefault("profiles", {})[profile_name] = profile
    existing.setdefault("default_profile", profile_name)

    save_config(existing)
    console.print(f"\n  [green]✓[/green]  Profile [cyan]{profile_name}[/cyan] saved → {CONFIG_PATH}")

    # Optionally scaffold .specify/integrations.yml
    if questionary.confirm(
        "\n  Set up .specify/integrations.yml for this project?", default=True
    ).ask():
        _scaffold_integrations(profile_name)

    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print(
        "  [bold green]Config complete![/bold green]  "
        "Run [cyan]sdd config test[/cyan] to verify."
    )
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()


def _scaffold_integrations(profile_name: str) -> None:
    import questionary
    from sdd.utils.manifest import read_manifest

    dest = Path(".specify/integrations.yml")
    if dest.exists():
        if not questionary.confirm(
            f"  {dest} already exists — overwrite?", default=False
        ).ask():
            return

    project_key    = questionary.text("Jira project key (e.g. MYPROJ):").ask()
    space_key      = questionary.text("Confluence space key (e.g. ENG):").ask()
    parent_page_id = questionary.text(
        "Confluence parent page ID (blank = root):", default=""
    ).ask().strip()

    manifest     = read_manifest() or {}
    project_name = (manifest.get("project") or {}).get("name", "{project}")

    dest.write_text(
        _integrations_template(profile_name, project_key, space_key,
                                parent_page_id, project_name)
    )
    console.print(f"  [green]✓[/green]  {dest} created")
    console.print(
        "  [dim]Edit [cyan]custom_fields[/cyan] to match your Jira instance.  "
        "Run [cyan]sdd config fields[/cyan] to discover IDs.[/dim]"
    )


@config_command.command("set-secret")
@click.option("--profile", required=True, help="Profile name from ~/.sdd/config.yml")
def config_set_secret(profile):
    """Store or rotate a keychain-stored credential for an existing profile.

    Only for profiles using credential_store: keyring — for env-var
    profiles, just export the new value in your shell instead."""
    import questionary

    if not CONFIG_PATH.exists():
        console.print("  [red]✗  ~/.sdd/config.yml not found. Run 'sdd config init' first.[/red]")
        raise SystemExit(1)

    data     = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    profiles = data.get("profiles", {})
    if profile not in profiles:
        console.print(f"  [red]✗  Profile '{profile}' not found in ~/.sdd/config.yml[/red]")
        raise SystemExit(1)

    store = profiles[profile].get("credential_store", "env")
    if store != "keyring":
        console.print(
            f"  [yellow]!  Profile '{profile}' uses credential_store: {store}, "
            f"not keyring.[/yellow]\n"
            f"     This command only updates keychain-stored credentials — "
            f"for an env-var profile, just export the new value in your "
            f"shell. To switch this profile to keychain storage, re-run "
            f"[cyan]sdd config init[/cyan] with the same profile name."
        )
        raise SystemExit(1)

    secret = questionary.password(f"New credential for profile '{profile}':").ask()
    try:
        store_secret(profile, secret)
    except RuntimeError as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)
    console.print(
        f"  [green]✓[/green]  Credential updated in the system keychain "
        f"for profile [cyan]{profile}[/cyan]"
    )


@config_command.command("test")
@click.option("--profile", default=None, help="Profile name from ~/.sdd/config.yml")
def config_test(profile):
    """Ping Jira and Confluence to verify credentials."""
    console.print()
    try:
        prof    = load_profile(profile)
        session = build_session(prof)
    except Exception as e:
        console.print(f"  [red]✗  Config error: {e}[/red]")
        raise SystemExit(1)

    try:
        me = JiraClient(session, prof.base_url).get_myself()
        name = me.get("displayName") or me.get("emailAddress", "?")
        console.print(f"  [green]✓[/green]  Jira       — connected as [cyan]{name}[/cyan]")
    except requests.HTTPError as e:
        console.print(f"  [red]✗  Jira       — HTTP {e.response.status_code}: "
                      f"{e.response.text[:120]}[/red]")

    try:
        me = ConfluenceClient(session, prof.base_url).get_myself()
        name = me.get("displayName") or me.get("username", "?")
        console.print(f"  [green]✓[/green]  Confluence — connected as [cyan]{name}[/cyan]")
    except requests.HTTPError as e:
        console.print(f"  [red]✗  Confluence — HTTP {e.response.status_code}: "
                      f"{e.response.text[:120]}[/red]")

    console.print()


@config_command.command("fields")
@click.option("--profile", default=None)
@click.option("--project", default=None, help="Jira project key")
def config_fields(profile, project):
    """List Jira custom fields to help fill integrations.yml custom_fields."""
    try:
        prof    = load_profile(profile)
        session = build_session(prof)
    except Exception as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)

    if project is None:
        try:
            from sdd.utils.integrations import load_integrations
            cfg     = load_integrations()
            project = cfg.jira.project_key if cfg.jira else None
        except FileNotFoundError:
            pass
    if not project:
        console.print(
            "  [red]✗  No project key. Use --project KEY or set it in "
            ".specify/integrations.yml[/red]"
        )
        raise SystemExit(1)

    fields = JiraClient(session, prof.base_url).get_fields()
    custom = sorted(
        [f for f in fields if f.get("custom")],
        key=lambda f: f.get("name", ""),
    )

    console.print(f"\n  [bold]Custom fields ({len(custom)} found):[/bold]\n")
    console.print(f"  {'ID':<30} {'Name':<40} Type")
    console.print(f"  {'─'*30} {'─'*40} {'─'*20}")
    for f in custom:
        ftype = (f.get("schema") or {}).get("type", "")
        console.print(
            f"  [cyan]{f['id']:<30}[/cyan] {f.get('name',''):<40} [dim]{ftype}[/dim]"
        )
    console.print()


def _integrations_template(profile: str, project_key: str, space_key: str,
                             parent_page_id: str, project_name: str) -> str:
    parent_line = (
        f'  parent_page_id: "{parent_page_id}"'
        if parent_page_id
        else '  # parent_page_id: "123456"   # optional'
    )
    return f"""\
# SDD Integrations — project-level config (no secrets here)
# Credentials live in ~/.sdd/config.yml as env var names
profile: {profile}

jira:
  project_key: {project_key}

  # Jira issue type names — Feature → Story → Task
  # Use "Epic" instead of "Feature" if your project has no Feature type
  issue_hierarchy:
    feature: Feature
    story: Story
    task: Task

  # Parent link field:
  #   "parent"            — Next-gen / team-managed projects
  #   "customfield_10014" — Classic projects (Epic Link)
  parent_field: parent

  base_fields:
    priority_map:
      must-have:   High
      should-have: Medium
      could-have:  Low
      wont-have:   Lowest
    labels: [sdd-generated]
    # fix_version: v1.0   # optional

  # Custom field IDs — run "sdd config fields" to discover yours
  custom_fields:
    story_points: customfield_10016    # almost universal on Jira Cloud
    # acceptance_criteria: customfield_10021
    # team: customfield_10100

confluence:
  space_key: {space_key}
{parent_line}

  # Page title templates — {{project}} replaced with project name from manifest
  # design applies in unified plan_mode; arch/hld/adr in separate plan_mode
  page_map:
    brd:       "{project_name} — Business Requirements"
    use-cases: "{project_name} — Use Cases"
    srd:       "{project_name} — System Requirements"
    design:    "{project_name} — Design"
    arch:      "{project_name} — Architecture Overview"
    hld:       "{project_name} — High-Level Design"
    adr:       "{project_name} — Architecture Decisions"
    lld:       "{project_name} — Low-Level Design"
    runbook:   "{project_name} — Runbook"

# For the Jira review workflow (sdd review submit/check/apply), add a
# document_reviews: section — see .specify/integrations.yml.example for the
# full plan_mode-aware reference.
"""
