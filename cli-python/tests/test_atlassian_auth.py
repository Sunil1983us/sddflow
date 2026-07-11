# Unit tests for the credential-store abstraction (env var vs. OS keychain).
# keyring.get_password/set_password are always mocked here — CI and many
# sandboxed environments have no working keychain backend at all, so a
# real call would fail for reasons unrelated to the logic under test.
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch

import pytest
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
        _write_config(config_home, {
            "work": {"auth_mode": "basic", "base_url": "https://x.atlassian.net",
                      "email": "a@b.com", "api_token_env": "JIRA_API_TOKEN"}
        }, default_profile="work")
        p = auth.load_profile()
        assert p.credential_store == "env"
        assert p.profile_name == "work"

    def test_explicit_keyring_is_read(self, config_home):
        _write_config(config_home, {
            "work": {"auth_mode": "basic", "base_url": "https://x.atlassian.net",
                      "email": "a@b.com", "credential_store": "keyring"}
        }, default_profile="work")
        p = auth.load_profile()
        assert p.credential_store == "keyring"

    def test_profile_name_set_from_lookup_key_not_config_content(self, config_home):
        _write_config(config_home, {
            "on-prem": {"auth_mode": "pat", "base_url": "https://x.internal",
                         "credential_store": "keyring"}
        }, default_profile="on-prem")
        p = auth.load_profile()
        assert p.profile_name == "on-prem"


class TestResolveSecretEnvPath:
    """The pre-existing env-var behavior must be byte-for-byte unchanged."""

    def test_missing_env_var_name_raises_value_error(self):
        p = auth.Profile(auth_mode="basic", base_url="https://x", credential_store="env")
        with pytest.raises(ValueError, match="api_token_env"):
            auth._resolve_secret(p, None, "api_token_env")

    def test_unset_env_var_raises_environment_error(self, monkeypatch):
        monkeypatch.delenv("SDD_TEST_TOKEN", raising=False)
        p = auth.Profile(auth_mode="basic", base_url="https://x", credential_store="env")
        with pytest.raises(EnvironmentError, match="SDD_TEST_TOKEN"):
            auth._resolve_secret(p, "SDD_TEST_TOKEN", "api_token_env")

    def test_set_env_var_returns_its_value(self, monkeypatch):
        monkeypatch.setenv("SDD_TEST_TOKEN", "secret-123")
        p = auth.Profile(auth_mode="basic", base_url="https://x", credential_store="env")
        assert auth._resolve_secret(p, "SDD_TEST_TOKEN", "api_token_env") == "secret-123"


class TestResolveSecretKeyringPath:
    def test_found_credential_returned(self):
        p = auth.Profile(auth_mode="basic", base_url="https://x",
                          credential_store="keyring", profile_name="work")
        with patch.object(auth.keyring, "get_password", return_value="kc-secret") as m:
            result = auth._resolve_secret(p, None, "api_token_env")
        assert result == "kc-secret"
        m.assert_called_once_with(auth.KEYRING_SERVICE, "work")

    def test_missing_credential_raises_environment_error_with_fix(self):
        p = auth.Profile(auth_mode="basic", base_url="https://x",
                          credential_store="keyring", profile_name="work")
        with patch.object(auth.keyring, "get_password", return_value=None):
            with pytest.raises(EnvironmentError, match="config set-secret --profile work"):
                auth._resolve_secret(p, None, "api_token_env")

    def test_backend_failure_wrapped_as_runtime_error(self):
        """A headless box with no Secret Service running raises something
        keyring-internal (varies by platform) -- must not leak a raw
        traceback, and must suggest the env fallback."""
        p = auth.Profile(auth_mode="basic", base_url="https://x",
                          credential_store="keyring", profile_name="work")
        with patch.object(auth.keyring, "get_password", side_effect=RuntimeError("no backend")):
            with pytest.raises(RuntimeError, match="credential_store: env"):
                auth._resolve_secret(p, None, "api_token_env")

    def test_env_var_name_ignored_for_keyring_profiles(self):
        """A keyring profile has no api_token_env at all -- must not be
        required or even consulted."""
        p = auth.Profile(auth_mode="basic", base_url="https://x",
                          credential_store="keyring", profile_name="work")
        with patch.object(auth.keyring, "get_password", return_value="kc-secret"):
            assert auth._resolve_secret(p, None, "api_token_env") == "kc-secret"


class TestStoreSecret:
    def test_success_calls_keyring_set_password(self):
        with patch.object(auth.keyring, "set_password") as m:
            auth.store_secret("work", "my-token")
        m.assert_called_once_with(auth.KEYRING_SERVICE, "work", "my-token")

    def test_backend_failure_wrapped_as_runtime_error(self):
        with patch.object(auth.keyring, "set_password", side_effect=RuntimeError("no backend")):
            with pytest.raises(RuntimeError, match="Environment variable' storage"):
                auth.store_secret("work", "my-token")


class TestBuildSessionWithKeyring:
    def test_basic_auth_mode_uses_keyring_token(self):
        p = auth.Profile(auth_mode="basic", base_url="https://x.atlassian.net",
                          email="a@b.com", credential_store="keyring", profile_name="work")
        with patch.object(auth.keyring, "get_password", return_value="kc-secret"):
            session = auth.build_session(p)
        assert session.auth.username == "a@b.com"
        assert session.auth.password == "kc-secret"

    def test_pat_auth_mode_uses_keyring_token_as_bearer(self):
        p = auth.Profile(auth_mode="pat", base_url="https://x.internal",
                          credential_store="keyring", profile_name="on-prem")
        with patch.object(auth.keyring, "get_password", return_value="pat-secret"):
            session = auth.build_session(p)
        assert session.headers["Authorization"] == "Bearer pat-secret"

    def test_oauth2_auth_mode_uses_keyring_token_as_bearer(self):
        p = auth.Profile(auth_mode="oauth2", base_url="https://x.atlassian.net",
                          credential_store="keyring", profile_name="ci")
        with patch.object(auth.keyring, "get_password", return_value="oauth-secret"):
            session = auth.build_session(p)
        assert session.headers["Authorization"] == "Bearer oauth-secret"

    def test_env_mode_unaffected_by_keyring_addition(self, monkeypatch):
        """Regression guard: adding credential_store must not change the
        existing env-var code path's behavior at all."""
        monkeypatch.setenv("SDD_TEST_TOKEN2", "env-secret")
        p = auth.Profile(auth_mode="basic", base_url="https://x.atlassian.net",
                          email="a@b.com", credential_store="env",
                          api_token_env="SDD_TEST_TOKEN2")
        session = auth.build_session(p)
        assert session.auth.password == "env-secret"
