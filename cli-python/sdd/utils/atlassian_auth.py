from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
import yaml
import requests
import requests.auth

CONFIG_PATH = Path.home() / ".sdd" / "config.yml"


@dataclass
class Profile:
    auth_mode: str        # basic | pat | oauth2
    base_url: str
    email: str | None = None
    api_token_env: str | None = None
    pat_env: str | None = None
    client_id_env: str | None = None
    client_secret_env: str | None = None
    access_token_env: str | None = None


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
        api_token_env=p.get("api_token_env"),
        pat_env=p.get("pat_env"),
        client_id_env=p.get("client_id_env"),
        client_secret_env=p.get("client_secret_env"),
        access_token_env=p.get("access_token_env"),
    )


def build_session(profile: Profile) -> requests.Session:
    session = requests.Session()
    session.headers["Accept"] = "application/json"
    session.headers["Content-Type"] = "application/json"

    if profile.auth_mode == "basic":
        if not profile.api_token_env:
            raise ValueError("auth_mode=basic requires api_token_env in config")
        token = os.environ.get(profile.api_token_env, "")
        if not token:
            raise EnvironmentError(
                f"Environment variable {profile.api_token_env} is not set. "
                "Export it before running sdd commands."
            )
        session.auth = requests.auth.HTTPBasicAuth(profile.email or "", token)

    elif profile.auth_mode == "pat":
        if not profile.pat_env:
            raise ValueError("auth_mode=pat requires pat_env in config")
        token = os.environ.get(profile.pat_env, "")
        if not token:
            raise EnvironmentError(
                f"Environment variable {profile.pat_env} is not set."
            )
        session.headers["Authorization"] = f"Bearer {token}"

    elif profile.auth_mode == "oauth2":
        if not profile.access_token_env:
            raise ValueError("auth_mode=oauth2 requires access_token_env in config")
        token = os.environ.get(profile.access_token_env, "")
        if not token:
            raise EnvironmentError(
                f"Environment variable {profile.access_token_env} is not set."
            )
        session.headers["Authorization"] = f"Bearer {token}"

    else:
        raise ValueError(
            f"Unknown auth_mode: {profile.auth_mode!r}. "
            "Valid values: basic | pat | oauth2"
        )

    return session


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        "# SDD global config — credentials stored as env var names, never values\n"
        + yaml.dump(config, default_flow_style=False, allow_unicode=True)
    )
