from __future__ import annotations

import json
import re
from pathlib import Path

import click
import requests
import yaml
from rich.console import Console

from sdd.utils.atlassian_auth import (
    CONFIG_PATH,
    build_session,
    load_profile,
    save_config,
    store_secret,
)
from sdd.utils.confluence_client import ConfluenceClient
from sdd.utils.integrations import parse_confluence_page_id
from sdd.utils.jira_client import JiraClient

console = Console()


@click.group()
def config_command():
    """Configure Atlassian credentials and project integration."""


def _collect_and_save_profile(default_name: str) -> str:
    """Interactively collect one profile's full auth set — base_url,
    auth_mode, and its credential (email+token, PAT, or OAuth2 token),
    stored via credential_store — and save it into ~/.sdd/config.yml.
    Returns the profile name used. A "profile" here is the entire
    authentication set, not just a URL: two profiles pointed at the same
    base_url but different tokens are still two distinct profiles."""
    import questionary

    profile_name = questionary.text("Profile name:", default=default_name).ask()
    base_url = questionary.text(
        "Atlassian base URL:", default="https://myco.atlassian.net"
    ).ask()
    auth_mode = questionary.select(
        "Auth mode:",
        choices=[
            questionary.Choice("basic  — Cloud (email + API token)", value="basic"),
            questionary.Choice(
                "pat    — Server/DC (Personal Access Token)", value="pat"
            ),
            questionary.Choice(
                "oauth2 — Cloud CI/CD (OAuth 2.0 Bearer token)", value="oauth2"
            ),
        ],
    ).ask()

    credential_store = questionary.select(
        "How should the credential be stored?",
        choices=[
            questionary.Choice(
                "System keychain (recommended — works in any terminal or "
                "AI tool, no shell setup)",
                value="keyring",
            ),
            questionary.Choice(
                "Environment variable (manual shell setup required)", value="env"
            ),
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
            console.print(
                f"\n  [dim]Export [cyan]{api_token_env}[/cyan] before running sdd commands.[/dim]"
            )

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
            console.print(
                f"\n  [dim]Export [cyan]{pat_env}[/cyan] before running sdd commands.[/dim]"
            )

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
            console.print(
                f"\n  [dim]Export [cyan]{access_token_env}[/cyan] before running sdd commands.[/dim]"
            )

    # Merge into existing config
    if CONFIG_PATH.exists():
        existing = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    else:
        existing = {"version": "1", "profiles": {}}

    existing.setdefault("profiles", {})[profile_name] = profile
    existing.setdefault("default_profile", profile_name)

    save_config(existing)
    console.print(
        f"\n  [green]✓[/green]  Profile [cyan]{profile_name}[/cyan] saved → {CONFIG_PATH}"
    )
    return profile_name


@config_command.command("init")
def config_init():
    """Interactively create ~/.sdd/config.yml and .specify/integrations.yml."""
    import questionary

    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("  [bold cyan]SDD Config[/bold cyan] — Atlassian setup")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()

    same_profile = questionary.select(
        "Do Jira and Confluence share the same site and credentials?",
        choices=[
            questionary.Choice(
                "Yes — same Atlassian site, one set of credentials "
                "(the common Cloud case)",
                value=True,
            ),
            questionary.Choice(
                "No — separate servers with separate credentials "
                "(typical for Server/Data Center)",
                value=False,
            ),
        ],
    ).ask()

    confluence_profile_name = None
    if same_profile:
        profile_name = _collect_and_save_profile("default")
    else:
        console.print()
        console.print("[bold]── Jira credentials ──[/bold]")
        jira_profile_name = _collect_and_save_profile("jira")
        console.print()
        console.print("[bold]── Confluence credentials ──[/bold]")
        confluence_profile_name = _collect_and_save_profile("confluence")
        # The top-level `profile:` in integrations.yml is Jira's — Confluence
        # gets an explicit confluence.profile override below (see
        # _scaffold_integrations). A "profile" is the whole auth set (URL +
        # auth mode + credential), so these are never assumed to overlap
        # even if, say, the base_url happened to match.
        profile_name = jira_profile_name

    # Optionally scaffold .specify/integrations.yml
    if questionary.confirm(
        "\n  Set up .specify/integrations.yml for this project?", default=True
    ).ask():
        scaffolded = _scaffold_integrations(profile_name, confluence_profile_name)
    else:
        scaffolded = False

    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    if confluence_profile_name:
        if scaffolded:
            # `sdd config test` (no --profile) resolves Jira and Confluence
            # independently via integrations.yml's jira.profile/
            # confluence.profile -- a single command now verifies both
            # servers correctly. Suggesting `--profile X` here would be
            # wrong: that flag tests ONE profile against BOTH services,
            # which is exactly the bug this split exists to avoid.
            console.print(
                "  [bold green]Config complete![/bold green]  Two profiles saved and "
                "wired into integrations.yml.\n"
                "  Run [cyan]sdd config test[/cyan] to verify both."
            )
        else:
            console.print(
                "  [bold green]Config complete![/bold green]  Two profiles saved, but "
                "integrations.yml wasn't scaffolded — [cyan]sdd config test[/cyan] can't "
                "tell them apart yet without it. Verify each profile directly instead:\n"
                f"    [cyan]sdd config test --profile {profile_name}[/cyan]\n"
                f"    [cyan]sdd config test --profile {confluence_profile_name}[/cyan]\n"
                "  [dim](each call tests both Jira and Confluence against that one "
                "profile's server, so expect one check to fail per call until "
                "integrations.yml wires the split.)[/dim]"
            )
    else:
        console.print(
            "  [bold green]Config complete![/bold green]  "
            "Run [cyan]sdd config test[/cyan] to verify."
        )
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()


def _scaffold_integrations(
    profile_name: str, confluence_profile_name: str | None = None
) -> bool:
    """Returns True iff .specify/integrations.yml was actually written --
    False if the user declined to overwrite an existing one, so the
    caller's closing message can tell whether `sdd config test` will
    actually be able to resolve a jira.profile/confluence.profile split
    (it can't without the file)."""
    import questionary

    from sdd.utils.manifest import read_manifest

    dest = Path(".specify/integrations.yml")
    if (
        dest.exists()
        and not questionary.confirm(
            f"  {dest} already exists — overwrite?", default=False
        ).ask()
    ):
        return False

    project_key = questionary.text("Jira project key (e.g. MYPROJ):").ask()
    space_key = questionary.text("Confluence space key (e.g. ENG):").ask()
    parent_page_raw = (
        questionary.text(
            "Confluence parent page — paste its URL or numeric ID (blank = root):",
            default="",
        )
        .ask()
        .strip()
    )
    parent_page_id = parse_confluence_page_id(parent_page_raw) or ""
    if (
        parent_page_raw
        and parent_page_id == parent_page_raw
        and not parent_page_raw.isdigit()
    ):
        console.print(
            "  [yellow]![/yellow]  Couldn't find a numeric page ID in that — "
            "using it as-is. If it's a Confluence 'tiny link' (…/x/AbCdEf), "
            "open the page and copy the full URL or the ID from "
            "[dim]···  Page Information[/dim] instead."
        )

    manifest = read_manifest() or {}
    project_name = (manifest.get("project") or {}).get("name", "{project}")

    example = Path(".specify/integrations.yml.example")
    if example.exists():
        # Base the scaffold on the pack's own shipped example rather than a
        # second, hand-maintained template string in this file -- the two
        # drifted apart before (project_keys, parent_field_by_level,
        # custom_fields_by_level, diagrams, document_reviews, pr_automation,
        # code_review, and most of page_map were only ever in the .example,
        # never in the old built-in template). Substituting into the real
        # file means every section this pack version supports is always
        # present, commented exactly as the pack author intended.
        content = _integrations_from_example(
            example.read_text(),
            profile_name,
            project_key,
            space_key,
            parent_page_id,
            confluence_profile_name,
        )
        dest.write_text(content)
        console.print(
            f"  [green]✓[/green]  {dest} created (from your pack's integrations.yml.example)"
        )
        if confluence_profile_name:
            console.print(
                f"  [dim]jira: uses profile [cyan]{profile_name}[/cyan] (the top-level "
                f"default); confluence: overridden to profile "
                f"[cyan]{confluence_profile_name}[/cyan].[/dim]"
            )
        console.print(
            "  [dim]Every optional section (project_keys, diagrams, pr_automation, "
            "code_review, ...) is included — most start commented out; "
            "uncomment what you need.[/dim]"
        )
        console.print(
            "  [yellow]![/yellow]  [dim]document_reviews: below has placeholder Jira "
            "accountIds (from the example) — replace them with real reviewers, "
            "or delete entries you don't want routed through Jira, before "
            "running [cyan]sdd review submit[/cyan].[/dim]"
        )
    else:
        # No .example shipped in this project (very old init, or a pack
        # without Jira/Confluence integration, e.g. sdd-micro) -- fall back
        # to the minimal built-in scaffold so config init still works.
        dest.write_text(
            _integrations_template(
                profile_name,
                project_key,
                space_key,
                parent_page_id,
                project_name,
                confluence_profile_name,
            )
        )
        console.print(
            f"  [green]✓[/green]  {dest} created (minimal built-in template — "
            "no integrations.yml.example found in this project)"
        )

    console.print(
        "  [dim]Edit [cyan]custom_fields[/cyan] to match your Jira instance.  "
        "Run [cyan]sdd config fields[/cyan] to discover IDs.[/dim]"
    )
    return True


def _integrations_from_example(
    text: str,
    profile: str,
    project_key: str,
    space_key: str,
    parent_page_id: str,
    confluence_profile: str | None = None,
) -> str:
    """Fills the profile/project_key/space_key/parent_page_id placeholders
    into a pack's shipped integrations.yml.example verbatim, leaving every
    other section (including the {feature}/{project} page_map templates,
    which are runtime substitutions, not scaffold-time ones) untouched.

    confluence_profile, when given, uncomments and fills confluence:'s own
    `profile:` override -- Jira and Confluence use separate ~/.sdd/config.yml
    profiles (separate base_url + credentials), the top-level profile:
    above being Jira's. When None (the common case, one shared profile),
    that line is left commented out exactly as shipped."""
    text = re.sub(
        r"^profile: default$", f"profile: {profile}", text, count=1, flags=re.MULTILINE
    )
    if project_key:
        text = re.sub(
            r"^(  project_key: )MYPROJ$",
            rf"\g<1>{project_key}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    if space_key:
        text = re.sub(
            r"^(  space_key: )ENG$",
            rf"\g<1>{space_key}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    if parent_page_id:
        text = re.sub(
            r'^  # parent_page_id: "123456"$',
            f'  parent_page_id: "{parent_page_id}"',
            text,
            count=1,
            flags=re.MULTILINE,
        )
    if confluence_profile:
        text = re.sub(
            r"^  # profile: confluence-dc$",
            f"  profile: {confluence_profile}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    return text


@config_command.command("set-secret")
@click.option("--profile", required=True, help="Profile name from ~/.sdd/config.yml")
def config_set_secret(profile):
    """Store or rotate a keychain-stored credential for an existing profile.

    Only for profiles using credential_store: keyring — for env-var
    profiles, just export the new value in your shell instead."""
    import questionary

    if not CONFIG_PATH.exists():
        console.print(
            "  [red]✗  ~/.sdd/config.yml not found. Run 'sdd config init' first.[/red]"
        )
        raise SystemExit(1)

    data = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    profiles = data.get("profiles", {})
    if profile not in profiles:
        console.print(
            f"  [red]✗  Profile '{profile}' not found in ~/.sdd/config.yml[/red]"
        )
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
    """Ping Jira and Confluence to verify credentials.

    An explicit --profile always tests that one profile against both
    services (e.g. sanity-checking a profile before wiring it into
    integrations.yml). Without --profile, Jira and Confluence are each
    resolved through integrations.yml's jira.profile/confluence.profile
    (falling back to the top-level profile:) independently -- so an org
    running them as separate Data Center servers gets each service
    tested against its OWN base_url/credential, not one profile's
    base_url used for both (which silently fails the "wrong" service
    whenever they differ). Falls back to the single default profile,
    exactly as before this existed, when integrations.yml doesn't exist
    yet (e.g. testing right after `sdd config init`, before scaffolding
    a project)."""
    console.print()

    cfg = None
    if profile is None:
        from sdd.utils.integrations import IntegrationsConfigError, load_integrations

        try:
            cfg = load_integrations()
        except (FileNotFoundError, IntegrationsConfigError):
            pass

    jira_name = profile or (cfg.jira_profile_name() if cfg else None)
    cf_name = profile or (cfg.confluence_profile_name() if cfg else None)

    try:
        jira_prof = load_profile(jira_name)
        jira_session = build_session(jira_prof)
    except Exception as e:
        console.print(
            f"  [red]✗  Config error (Jira profile "
            f"'{jira_name or 'default'}'): {e}[/red]"
        )
        raise SystemExit(1)

    if cf_name == jira_name:
        cf_prof, cf_session = jira_prof, jira_session
    else:
        try:
            cf_prof = load_profile(cf_name)
            cf_session = build_session(cf_prof)
        except Exception as e:
            console.print(
                f"  [red]✗  Config error (Confluence profile "
                f"'{cf_name or 'default'}'): {e}[/red]"
            )
            raise SystemExit(1)
        console.print(f"  [dim]Jira profile:       {jira_name}[/dim]")
        console.print(f"  [dim]Confluence profile: {cf_name}[/dim]")
        console.print()

    _probe_service(
        "Jira",
        lambda: JiraClient(
            jira_session, jira_prof.base_url, deployment=jira_prof.deployment
        ).get_myself(),
        ("displayName", "emailAddress"),
    )
    _probe_service(
        "Confluence",
        lambda: ConfluenceClient(
            cf_session, cf_prof.base_url, deployment=cf_prof.deployment
        ).get_myself(),
        ("displayName", "username"),
    )

    console.print()


def _probe_service(label: str, get_myself_fn, name_keys: tuple[str, ...]) -> None:
    """Runs a get_myself()-style connectivity probe and prints one status
    line -- never lets it crash the whole `sdd config test` command.

    Three failure modes, told apart because each points at a different
    fix:
    - HTTPError: the server itself said no (4xx/5xx) -- its status code
      and body are the most useful thing to show.
    - JSONDecodeError (raised by response.json() on a 200-but-non-JSON
      body -- caught as the bare stdlib class since older `requests`
      versions raise that directly, and as InvalidJSONError to also
      catch requests>=2.27's own subclass that wraps it): most commonly
      means base_url points at an SSO/login redirect page or the wrong
      path entirely, not the real API root -- a raw "Expecting value:
      line 1 column 1" message (what this looks like uncaught) gives the
      user no clue what actually went wrong.
    - Any other RequestException (connection refused, DNS failure,
      timeout, TLS error, malformed URL): whatever requests' own message
      says is usually clear enough on its own.
    """
    try:
        me = get_myself_fn()
        name = next((me.get(k) for k in name_keys if me.get(k)), "?")
        console.print(
            f"  [green]✓[/green]  {label:<10} — connected as [cyan]{name}[/cyan]"
        )
    except requests.exceptions.HTTPError as e:
        console.print(
            f"  [red]✗  {label:<10} — HTTP {e.response.status_code}: "
            f"{e.response.text[:120]}[/red]"
        )
    except (json.JSONDecodeError, requests.exceptions.InvalidJSONError):
        console.print(
            f"  [red]✗  {label:<10} — got a response, but it wasn't "
            f"JSON.[/red]\n"
            f"      [dim]Check base_url points at the API root (not a "
            f"login/SSO redirect page), and that the PAT/token is "
            f"still valid.[/dim]"
        )
    except requests.exceptions.RequestException as e:
        console.print(f"  [red]✗  {label:<10} — {e}[/red]")


@config_command.command("fields")
@click.option("--profile", default=None)
@click.option("--project", default=None, help="Jira project key")
def config_fields(profile, project):
    """List Jira custom fields to help fill integrations.yml custom_fields."""
    # integrations.yml may not exist yet (this command is often run first, to
    # discover field IDs before writing it) -- load it best-effort so a
    # jira.profile override is honored when present, without requiring the
    # file to exist.
    cfg = None
    try:
        from sdd.utils.integrations import IntegrationsConfigError, load_integrations

        cfg = load_integrations()
    except (FileNotFoundError, IntegrationsConfigError):
        pass

    try:
        prof = load_profile(profile or (cfg.jira_profile_name() if cfg else None))
        session = build_session(prof)
    except Exception as e:
        console.print(f"  [red]✗  {e}[/red]")
        raise SystemExit(1)

    if project is None and cfg is not None:
        project = cfg.jira.project_key if cfg.jira else None
    if not project:
        console.print(
            "  [red]✗  No project key. Use --project KEY or set it in "
            ".specify/integrations.yml[/red]"
        )
        raise SystemExit(1)

    fields = JiraClient(session, prof.base_url, deployment=prof.deployment).get_fields()
    custom = sorted(
        [f for f in fields if f.get("custom")],
        key=lambda f: f.get("name", ""),
    )

    console.print(f"\n  [bold]Custom fields ({len(custom)} found):[/bold]\n")
    console.print(f"  {'ID':<30} {'Name':<40} Type")
    console.print(f"  {'─' * 30} {'─' * 40} {'─' * 20}")
    for f in custom:
        ftype = (f.get("schema") or {}).get("type", "")
        console.print(
            f"  [cyan]{f['id']:<30}[/cyan] {f.get('name', ''):<40} [dim]{ftype}[/dim]"
        )
    console.print()


def _integrations_template(
    profile: str,
    project_key: str,
    space_key: str,
    parent_page_id: str,
    project_name: str,
    confluence_profile: str | None = None,
) -> str:
    parent_line = (
        f'  parent_page_id: "{parent_page_id}"'
        if parent_page_id
        else '  # parent_page_id: "123456"   # optional'
    )
    confluence_profile_line = (
        f"  profile: {confluence_profile}   # separate from jira's profile above\n"
        if confluence_profile
        else ""
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
{confluence_profile_line}  space_key: {space_key}
{parent_line}

  # Page title templates — {{feature}} substituted with the active feature
  # (or --feature override) at push time; {{project}} with project name
  # from manifest. Keep {{feature}} in every per-feature entry below --
  # `sdd confluence push` nests pages under a Project -> Feature page
  # hierarchy automatically, but that nesting alone does not stop two
  # features colliding on the same title (Confluence enforces title
  # uniqueness per SPACE, not per parent page) -- only {{feature}} in the
  # title text itself does. See integrations.yml.example for the fuller
  # reference (more doc keys: validate, analyze, tasks, etc.)
  # design applies in unified plan_mode; arch/hld/adr in separate plan_mode
  page_map:
    brd:       "{{feature}} — Business Requirements"
    use-cases: "{{feature}} — Use Cases"
    srd:       "{{feature}} — System Requirements"
    design:    "{{feature}} — Design"
    arch:      "{{feature}} — Architecture Overview"
    hld:       "{{feature}} — High-Level Design"
    adr:       "{{feature}} — Architecture Decisions"
    lld:       "{{feature}} — Low-Level Design"
    runbook:   "{project_name} — Runbook"
    # Title here is ignored (always "{{project}} — Constitution") -- this
    # key's only job is making a bare "sdd confluence push" (no --doc)
    # include the Constitution page; remove the line to opt out
    constitution: "{project_name} — Constitution"
    # Same deal as constitution above -- title ignored (always
    # "{{feature}} — Context"), this key only controls whether a bare
    # push includes it; remove the line to opt out
    context: "{{feature}} — Context"

# For the Jira review workflow (sdd review submit/check/apply), add a
# document_reviews: section — see .specify/integrations.yml.example for the
# full plan_mode-aware reference.
"""
