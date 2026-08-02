from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import keyring
import requests
import requests.auth
import yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Every Jira/Confluence API call in this codebase goes through a Session
# built by build_session() below, so configuring resilience once here --
# rather than passing timeout=/wrapping try/except at each of the ~25
# individual call sites across jira_client.py and confluence_client.py --
# covers all of them. Before this, a flaky network blip or an Atlassian
# rate limit turned into a raw, unhandled stack trace mid-workflow.
_DEFAULT_TIMEOUT = 20  # seconds -- generous for a REST call, short enough
# that a hung connection doesn't block an
# interactive CLI command indefinitely


class _TimeoutHTTPAdapter(HTTPAdapter):
    """Applies a default request timeout whenever a call doesn't specify
    its own -- requests.Session has no built-in way to set a session-wide
    default timeout (a well-known library gotcha), so overriding the
    adapter's send() is the standard workaround."""

    def __init__(self, *args, timeout: float = _DEFAULT_TIMEOUT, **kwargs):
        self._timeout = timeout
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = self._timeout
        return super().send(request, **kwargs)


def _retrying_adapter() -> _TimeoutHTTPAdapter:
    """3 retries with exponential backoff (0s/1s/2s/4s between attempts) on
    connection errors and on 429/500/502/503/504 responses, honoring a
    429's Retry-After header when Atlassian sends one. Retries every HTTP
    method, including POST/PUT -- this codebase's writes already lean on
    label-based find-before-create idempotency where duplication would
    matter (see JiraClient.find_by_label), and the alternative (a
    connection blip silently aborting a document approval or a Jira push
    partway through) is worse than the small remaining risk of an
    occasional duplicate retry on a genuinely dropped response."""
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=None,
        respect_retry_after_header=True,
    )
    return _TimeoutHTTPAdapter(max_retries=retry)


CONFIG_PATH = Path.home() / ".sdd" / "config.yml"

# Service name under which credentials are stored in the OS-native secure
# credential store (macOS Keychain / Windows Credential Manager / Linux
# Secret Service) when a profile uses credential_store: keyring. The
# per-profile lookup key is the profile name itself.
KEYRING_SERVICE = "sdd-framework"


@dataclass
class Profile:
    auth_mode: str  # basic | pat | oauth2
    base_url: str
    email: str | None = None
    credential_store: str = "env"  # env | keyring
    api_token_env: str | None = None
    pat_env: str | None = None
    client_id_env: str | None = None
    client_secret_env: str | None = None
    access_token_env: str | None = None
    profile_name: str | None = None  # set by load_profile; the keyring lookup key


def load_profile(name: str | None = None) -> Profile:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            "~/.sdd/config.yml not found. Run 'sdd config init' to create it."
        )
    data = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    profiles = data.get("profiles", {})

    if name is None:
        name = data.get("default_profile")
    if not name:
        if len(profiles) == 1:
            name = next(iter(profiles))
        else:
            raise ValueError(
                "Multiple profiles exist — specify --profile or set "
                "default_profile in ~/.sdd/config.yml"
            )
    if name not in profiles:
        raise KeyError(f"Profile '{name}' not found in ~/.sdd/config.yml")

    p = profiles[name]
    return Profile(
        auth_mode=p["auth_mode"],
        base_url=p["base_url"].rstrip("/"),
        email=p.get("email"),
        credential_store=p.get("credential_store", "env"),
        api_token_env=p.get("api_token_env"),
        pat_env=p.get("pat_env"),
        client_id_env=p.get("client_id_env"),
        client_secret_env=p.get("client_secret_env"),
        access_token_env=p.get("access_token_env"),
        profile_name=name,
    )


def store_secret(profile_name: str, secret: str) -> None:
    """Store a credential in the OS-native secure credential store (macOS
    Keychain / Windows Credential Manager / Linux Secret Service).

    This is what makes credential_store: keyring work in any terminal or
    AI tool without shell setup — the OS keychain is readable by any
    process on the machine, unlike an environment variable, which only
    exists in the shell session that exported it (and its children).

    Raises RuntimeError with an actionable message if no backend is
    available (e.g. headless Linux with no Secret Service running) —
    callers should suggest credential_store: env as the fallback."""
    try:
        keyring.set_password(KEYRING_SERVICE, profile_name, secret)
    except Exception as e:
        raise RuntimeError(
            f"Could not store the credential in the system keychain "
            f"({type(e).__name__}: {e}). This can happen on headless "
            f"Linux systems with no Secret Service running, or minimal "
            f"containers. Re-run 'sdd config init' and choose "
            f"'Environment variable' storage instead."
        ) from e


def _get_keyring_secret(profile_name: str) -> str:
    try:
        token = keyring.get_password(KEYRING_SERVICE, profile_name)
    except Exception as e:
        raise RuntimeError(
            f"Could not read the credential from the system keychain "
            f"({type(e).__name__}: {e}). This can happen on headless "
            f"Linux systems with no Secret Service running, or minimal "
            f"containers. Switch this profile to credential_store: env "
            f"in ~/.sdd/config.yml as a fallback."
        ) from e
    if not token:
        raise OSError(
            f"No credential found in the system keychain for profile "
            f"'{profile_name}'. Run 'sdd config set-secret --profile "
            f"{profile_name}' to store it."
        )
    return token


def _resolve_secret(profile: Profile, env_var_name: str | None, field_name: str) -> str:
    """Fetch the actual secret value for this profile, from whichever
    credential_store it's configured for. env_var_name/field_name are only
    used (and required) in the "env" path — keyring lookups need only the
    profile name."""
    if profile.credential_store == "keyring":
        return _get_keyring_secret(profile.profile_name or "default")

    if not env_var_name:
        raise ValueError(f"credential_store=env requires {field_name} in config")
    token = os.environ.get(env_var_name, "")
    if not token:
        raise OSError(
            f"Environment variable {env_var_name} is not set. Export it "
            f"before running sdd commands, or switch this profile to "
            f"credential_store: keyring (run 'sdd config init') so it "
            f"works in any shell without exporting anything."
        )
    return token


def build_session(profile: Profile) -> requests.Session:
    session = requests.Session()
    session.mount("https://", _retrying_adapter())
    session.mount("http://", _retrying_adapter())
    session.headers["Accept"] = "application/json"
    session.headers["Content-Type"] = "application/json"

    if profile.auth_mode == "basic":
        token = _resolve_secret(profile, profile.api_token_env, "api_token_env")
        session.auth = requests.auth.HTTPBasicAuth(profile.email or "", token)

    elif profile.auth_mode == "pat":
        token = _resolve_secret(profile, profile.pat_env, "pat_env")
        session.headers["Authorization"] = f"Bearer {token}"

    elif profile.auth_mode == "oauth2":
        token = _resolve_secret(profile, profile.access_token_env, "access_token_env")
        session.headers["Authorization"] = f"Bearer {token}"

    else:
        raise ValueError(
            f"Unknown auth_mode: {profile.auth_mode!r}. "
            "Valid values: basic | pat | oauth2"
        )

    return session


def load_jira_session(
    cfg, profile_override: str | None = None
) -> tuple[Profile, requests.Session]:
    """Resolve the Profile + authenticated Session to use for Jira calls.

    Honors integrations.yml's jira.profile override (see
    IntegrationsConfig.jira_profile_name()) before falling back to the
    top-level profile -- so an org running Jira and Confluence as separate
    Data Center servers (different base_url, different credentials) can
    point each service at its own ~/.sdd/config.yml profile instead of the
    single shared one that's correct only when both live on the same
    Atlassian Cloud site. profile_override wins over both (e.g. a command's
    own --profile flag)."""
    prof = load_profile(profile_override or cfg.jira_profile_name())
    return prof, build_session(prof)


def load_confluence_session(
    cfg, profile_override: str | None = None
) -> tuple[Profile, requests.Session]:
    """Resolve the Profile + authenticated Session to use for Confluence
    calls -- see load_jira_session(), which this mirrors for the
    confluence.profile override."""
    prof = load_profile(profile_override or cfg.confluence_profile_name())
    return prof, build_session(prof)


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        "# SDD global config — credentials stored as env var names, or\n"
        "# (credential_store: keyring) in the OS keychain — never as\n"
        "# plaintext values in this file either way\n"
        + yaml.dump(config, default_flow_style=False, allow_unicode=True)
    )
