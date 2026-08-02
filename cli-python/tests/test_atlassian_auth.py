# Unit tests for the credential-store abstraction (env var vs. OS keychain).
# keyring.get_password/set_password are always mocked here — CI and many
# sandboxed environments have no working keychain backend at all, so a
# real call would fail for reasons unrelated to the logic under test.
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar
from unittest.mock import patch

import pytest
import requests
import yaml

from sdd.utils import atlassian_auth as auth


@pytest.fixture()
def config_home(tmp_path, monkeypatch):
    """Point CONFIG_PATH at a throwaway file for this test."""
    monkeypatch.setattr(auth, "CONFIG_PATH", tmp_path / ".sdd" / "config.yml")
    return tmp_path


def _write_config(config_home, profiles: dict, default_profile: str | None = None):
    path = auth.CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"version": "1", "profiles": profiles}
    if default_profile:
        data["default_profile"] = default_profile
    path.write_text(yaml.dump(data))


class TestLoadProfileCredentialStore:
    def test_defaults_to_env_when_field_absent(self, config_home):
        """Profiles written before this feature existed have no
        credential_store field at all — must default to 'env', the
        pre-existing behavior, not silently switch to keyring."""
        _write_config(
            config_home,
            {
                "work": {
                    "auth_mode": "basic",
                    "base_url": "https://x.atlassian.net",
                    "email": "a@b.com",
                    "api_token_env": "JIRA_API_TOKEN",
                }
            },
            default_profile="work",
        )
        p = auth.load_profile()
        assert p.credential_store == "env"
        assert p.profile_name == "work"

    def test_explicit_keyring_is_read(self, config_home):
        _write_config(
            config_home,
            {
                "work": {
                    "auth_mode": "basic",
                    "base_url": "https://x.atlassian.net",
                    "email": "a@b.com",
                    "credential_store": "keyring",
                }
            },
            default_profile="work",
        )
        p = auth.load_profile()
        assert p.credential_store == "keyring"

    def test_profile_name_set_from_lookup_key_not_config_content(self, config_home):
        _write_config(
            config_home,
            {
                "on-prem": {
                    "auth_mode": "pat",
                    "base_url": "https://x.internal",
                    "credential_store": "keyring",
                }
            },
            default_profile="on-prem",
        )
        p = auth.load_profile()
        assert p.profile_name == "on-prem"


class TestResolveSecretEnvPath:
    """The pre-existing env-var behavior must be byte-for-byte unchanged."""

    def test_missing_env_var_name_raises_value_error(self):
        p = auth.Profile(
            auth_mode="basic", base_url="https://x", credential_store="env"
        )
        with pytest.raises(ValueError, match="api_token_env"):
            auth._resolve_secret(p, None, "api_token_env")

    def test_unset_env_var_raises_environment_error(self, monkeypatch):
        monkeypatch.delenv("SDD_TEST_TOKEN", raising=False)
        p = auth.Profile(
            auth_mode="basic", base_url="https://x", credential_store="env"
        )
        with pytest.raises(EnvironmentError, match="SDD_TEST_TOKEN"):
            auth._resolve_secret(p, "SDD_TEST_TOKEN", "api_token_env")

    def test_set_env_var_returns_its_value(self, monkeypatch):
        monkeypatch.setenv("SDD_TEST_TOKEN", "secret-123")
        p = auth.Profile(
            auth_mode="basic", base_url="https://x", credential_store="env"
        )
        assert (
            auth._resolve_secret(p, "SDD_TEST_TOKEN", "api_token_env") == "secret-123"
        )


class TestResolveSecretKeyringPath:
    def test_found_credential_returned(self):
        p = auth.Profile(
            auth_mode="basic",
            base_url="https://x",
            credential_store="keyring",
            profile_name="work",
        )
        with patch.object(auth.keyring, "get_password", return_value="kc-secret") as m:
            result = auth._resolve_secret(p, None, "api_token_env")
        assert result == "kc-secret"
        m.assert_called_once_with(auth.KEYRING_SERVICE, "work")

    def test_missing_credential_raises_environment_error_with_fix(self):
        p = auth.Profile(
            auth_mode="basic",
            base_url="https://x",
            credential_store="keyring",
            profile_name="work",
        )
        with (
            patch.object(auth.keyring, "get_password", return_value=None),
            pytest.raises(EnvironmentError, match="config set-secret --profile work"),
        ):
            auth._resolve_secret(p, None, "api_token_env")

    def test_backend_failure_wrapped_as_runtime_error(self):
        """A headless box with no Secret Service running raises something
        keyring-internal (varies by platform) -- must not leak a raw
        traceback, and must suggest the env fallback."""
        p = auth.Profile(
            auth_mode="basic",
            base_url="https://x",
            credential_store="keyring",
            profile_name="work",
        )
        with (
            patch.object(
                auth.keyring, "get_password", side_effect=RuntimeError("no backend")
            ),
            pytest.raises(RuntimeError, match="credential_store: env"),
        ):
            auth._resolve_secret(p, None, "api_token_env")

    def test_env_var_name_ignored_for_keyring_profiles(self):
        """A keyring profile has no api_token_env at all -- must not be
        required or even consulted."""
        p = auth.Profile(
            auth_mode="basic",
            base_url="https://x",
            credential_store="keyring",
            profile_name="work",
        )
        with patch.object(auth.keyring, "get_password", return_value="kc-secret"):
            assert auth._resolve_secret(p, None, "api_token_env") == "kc-secret"


class TestStoreSecret:
    def test_success_calls_keyring_set_password(self):
        with patch.object(auth.keyring, "set_password") as m:
            auth.store_secret("work", "my-token")
        m.assert_called_once_with(auth.KEYRING_SERVICE, "work", "my-token")

    def test_backend_failure_wrapped_as_runtime_error(self):
        with (
            patch.object(
                auth.keyring, "set_password", side_effect=RuntimeError("no backend")
            ),
            pytest.raises(RuntimeError, match="Environment variable' storage"),
        ):
            auth.store_secret("work", "my-token")


class TestBuildSessionWithKeyring:
    def test_basic_auth_mode_uses_keyring_token(self):
        p = auth.Profile(
            auth_mode="basic",
            base_url="https://x.atlassian.net",
            email="a@b.com",
            credential_store="keyring",
            profile_name="work",
        )
        with patch.object(auth.keyring, "get_password", return_value="kc-secret"):
            session = auth.build_session(p)
        assert session.auth.username == "a@b.com"
        assert session.auth.password == "kc-secret"

    def test_pat_auth_mode_uses_keyring_token_as_bearer(self):
        p = auth.Profile(
            auth_mode="pat",
            base_url="https://x.internal",
            credential_store="keyring",
            profile_name="on-prem",
        )
        with patch.object(auth.keyring, "get_password", return_value="pat-secret"):
            session = auth.build_session(p)
        assert session.headers["Authorization"] == "Bearer pat-secret"

    def test_oauth2_auth_mode_uses_keyring_token_as_bearer(self):
        p = auth.Profile(
            auth_mode="oauth2",
            base_url="https://x.atlassian.net",
            credential_store="keyring",
            profile_name="ci",
        )
        with patch.object(auth.keyring, "get_password", return_value="oauth-secret"):
            session = auth.build_session(p)
        assert session.headers["Authorization"] == "Bearer oauth-secret"

    def test_env_mode_unaffected_by_keyring_addition(self, monkeypatch):
        """Regression guard: adding credential_store must not change the
        existing env-var code path's behavior at all."""
        monkeypatch.setenv("SDD_TEST_TOKEN2", "env-secret")
        p = auth.Profile(
            auth_mode="basic",
            base_url="https://x.atlassian.net",
            email="a@b.com",
            credential_store="env",
            api_token_env="SDD_TEST_TOKEN2",
        )
        session = auth.build_session(p)
        assert session.auth.password == "env-secret"


class _FakeCfg:
    """Duck-types the two IntegrationsConfig methods load_jira_session()/
    load_confluence_session() actually call -- avoids a real
    integrations.yml just to test profile resolution."""

    def __init__(self, jira_profile, confluence_profile):
        self._jira_profile = jira_profile
        self._confluence_profile = confluence_profile

    def jira_profile_name(self):
        return self._jira_profile

    def confluence_profile_name(self):
        return self._confluence_profile


class TestLoadJiraAndConfluenceSession:
    """Jira and Confluence resolve independently -- the Data Center case
    where they're separate servers with separate credentials, not the
    single-Atlassian-Cloud-site assumption a single shared profile made."""

    def test_different_profiles_resolve_to_different_base_urls(self, config_home):
        _write_config(
            config_home,
            {
                "jira-dc": {
                    "auth_mode": "pat",
                    "base_url": "https://jira.internal",
                    "credential_store": "keyring",
                },
                "confluence-dc": {
                    "auth_mode": "pat",
                    "base_url": "https://confluence.internal",
                    "credential_store": "keyring",
                },
            },
        )
        cfg = _FakeCfg(jira_profile="jira-dc", confluence_profile="confluence-dc")
        with patch.object(auth.keyring, "get_password", return_value="secret"):
            jira_prof, _ = auth.load_jira_session(cfg)
            cf_prof, _ = auth.load_confluence_session(cfg)
        assert jira_prof.base_url == "https://jira.internal"
        assert cf_prof.base_url == "https://confluence.internal"
        assert jira_prof.profile_name == "jira-dc"
        assert cf_prof.profile_name == "confluence-dc"

    def test_same_profile_when_no_override_set(self, config_home):
        """The common Cloud case -- both services share one profile."""
        _write_config(
            config_home,
            {
                "default": {
                    "auth_mode": "basic",
                    "base_url": "https://x.atlassian.net",
                    "email": "a@b.com",
                    "credential_store": "keyring",
                },
            },
        )
        cfg = _FakeCfg(jira_profile="default", confluence_profile="default")
        with patch.object(auth.keyring, "get_password", return_value="secret"):
            jira_prof, _ = auth.load_jira_session(cfg)
            cf_prof, _ = auth.load_confluence_session(cfg)
        assert jira_prof.base_url == cf_prof.base_url == "https://x.atlassian.net"

    def test_explicit_override_wins_over_cfg_resolution(self, config_home):
        """A command's own --profile flag beats integrations.yml entirely --
        same precedence the old single-profile load_profile(profile or
        cfg.profile) call had."""
        _write_config(
            config_home,
            {
                "jira-dc": {
                    "auth_mode": "pat",
                    "base_url": "https://jira.internal",
                    "credential_store": "keyring",
                },
                "manual": {
                    "auth_mode": "pat",
                    "base_url": "https://manual.internal",
                    "credential_store": "keyring",
                },
            },
        )
        cfg = _FakeCfg(jira_profile="jira-dc", confluence_profile="jira-dc")
        with patch.object(auth.keyring, "get_password", return_value="secret"):
            jira_prof, _ = auth.load_jira_session(cfg, profile_override="manual")
        assert jira_prof.base_url == "https://manual.internal"


# --- Network resilience: timeout + retry/backoff on every Jira/Confluence
# call, mounted once in build_session() rather than at each of the ~25
# individual call sites in jira_client.py/confluence_client.py -----------


class TestBuildSessionResilience:
    def _profile(self):
        return auth.Profile(
            auth_mode="basic",
            base_url="https://x.atlassian.net",
            email="a@b.com",
            credential_store="env",
            api_token_env="SDD_TEST_RESILIENCE_TOKEN",
        )

    def test_retrying_adapter_mounted_on_https_and_http(self, monkeypatch):
        monkeypatch.setenv("SDD_TEST_RESILIENCE_TOKEN", "x")
        session = auth.build_session(self._profile())
        assert isinstance(
            session.get_adapter("https://x.atlassian.net/foo"), auth._TimeoutHTTPAdapter
        )
        assert isinstance(
            session.get_adapter("http://x.atlassian.net/foo"), auth._TimeoutHTTPAdapter
        )

    def test_retry_policy_covers_connection_errors_and_5xx_and_429(self, monkeypatch):
        monkeypatch.setenv("SDD_TEST_RESILIENCE_TOKEN", "x")
        session = auth.build_session(self._profile())
        retry = session.get_adapter("https://x.atlassian.net/foo").max_retries
        assert retry.total == 3
        assert set(retry.status_forcelist) == {429, 500, 502, 503, 504}
        assert retry.respect_retry_after_header is True

    def test_default_timeout_is_20_seconds(self, monkeypatch):
        monkeypatch.setenv("SDD_TEST_RESILIENCE_TOKEN", "x")
        session = auth.build_session(self._profile())
        assert session.get_adapter("https://x.atlassian.net/foo")._timeout == 20


class _FlakyThenOKHandler(BaseHTTPRequestHandler):
    """Fails with 503 the first N times a given path is hit, then returns
    200 -- lets the retry test prove real end-to-end behavior (a request
    that would have raised actually succeeds) instead of only inspecting
    config values."""

    fail_count: ClassVar[
        dict
    ] = {}  # path -> remaining failures, reset per test via class patching

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        remaining = _FlakyThenOKHandler.fail_count.get(self.path, 0)
        if remaining > 0:
            _FlakyThenOKHandler.fail_count[self.path] = remaining - 1
            self.send_response(503)
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok": true}')


@pytest.fixture
def flaky_server():
    _FlakyThenOKHandler.fail_count = {}
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _FlakyThenOKHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def test_session_retries_through_transient_503s_and_succeeds(flaky_server, monkeypatch):
    monkeypatch.setenv("SDD_TEST_RESILIENCE_TOKEN", "x")
    port = flaky_server.server_address[1]
    profile = auth.Profile(
        auth_mode="basic",
        base_url=f"http://127.0.0.1:{port}",
        email="a@b.com",
        credential_store="env",
        api_token_env="SDD_TEST_RESILIENCE_TOKEN",
    )
    session = auth.build_session(profile)
    _FlakyThenOKHandler.fail_count["/flaky"] = 2  # fails twice, succeeds on the 3rd try

    resp = session.get(f"http://127.0.0.1:{port}/flaky")

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_plain_session_without_retry_would_fail_on_the_same_server(
    flaky_server, monkeypatch
):
    """Control case proving the test server itself genuinely fails without
    a retrying adapter -- so the pass above is attributable to
    build_session()'s retry config, not to the server being lenient."""
    port = flaky_server.server_address[1]
    plain = requests.Session()
    _FlakyThenOKHandler.fail_count["/flaky"] = 2

    resp = plain.get(f"http://127.0.0.1:{port}/flaky")

    assert resp.status_code == 503
