# Unit tests for config-init template output and integrations loading.
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from sdd.commands import config as config_mod
from sdd.commands.config import _integrations_template, config_command
from sdd.utils import atlassian_auth
from sdd.utils.integrations import load_integrations, _DEFAULT_PAGE_MAP


EXPECTED_DOC_KEYS = ["brd", "use-cases", "srd", "design",
                     "arch", "hld", "adr", "lld", "runbook"]


def test_config_template_is_valid_yaml_with_current_doc_keys():
    out = _integrations_template("default", "MYPROJ", "ENG", "", "Demo")
    data = yaml.safe_load(out)
    assert list(data["confluence"]["page_map"]) == EXPECTED_DOC_KEYS
    assert data["jira"]["project_key"] == "MYPROJ"


def test_config_template_with_parent_page_id():
    out = _integrations_template("default", "P", "ENG", "12345", "Demo")
    # IDs are deliberately quoted strings — Confluence page IDs are opaque
    assert yaml.safe_load(out)["confluence"]["parent_page_id"] == "12345"


def test_default_page_map_matches_config_template_keys():
    assert list(_DEFAULT_PAGE_MAP) == EXPECTED_DOC_KEYS


def test_shipped_example_parses_and_agrees_with_defaults():
    """The integrations.yml.example shipped in packs must load cleanly and
    use the same doc-key vocabulary as the CLI defaults."""
    example = Path(__file__).resolve().parents[2] / \
        "packs/_shared/full/.specify/integrations.yml.example"
    data = yaml.safe_load(example.read_text())
    assert set(data["confluence"]["page_map"]) == set(EXPECTED_DOC_KEYS)
    # active document_reviews ships in unified mode: design yes, arch/hld/adr commented
    reviews = data["document_reviews"]
    assert "use-cases" in reviews and "design" in reviews
    assert "arch" not in reviews  # separate-mode block stays commented

    # sequence within each phase must be strictly increasing (predecessor gating)
    by_phase: dict[str, list[int]] = {}
    for doc in reviews.values():
        by_phase.setdefault(doc["phase"], []).append(doc["sequence"])
    for phase, seqs in by_phase.items():
        assert sorted(seqs) == seqs or sorted(seqs) == sorted(set(seqs)), phase
        assert len(set(seqs)) == len(seqs), f"duplicate sequence in {phase}"


def test_load_integrations_missing_file_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        load_integrations()


def test_load_integrations_confluence_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path(".specify").mkdir()
    Path(".specify/integrations.yml").write_text(
        "profile: default\nconfluence:\n  space_key: ENG\n"
    )
    cfg = load_integrations()
    assert cfg.jira is None
    assert cfg.confluence.space_key == "ENG"
    assert cfg.confluence.page_map == _DEFAULT_PAGE_MAP


def test_jira_project_keys_default_to_empty_dict(tmp_path, monkeypatch):
    """No project_keys: block -- every level falls back to project_key."""
    monkeypatch.chdir(tmp_path)
    Path(".specify").mkdir()
    Path(".specify/integrations.yml").write_text(
        "jira:\n  project_key: MYPROJ\n"
    )
    cfg = load_integrations()
    assert cfg.jira.project_keys == {}
    for level in ("feature", "story", "task", "chg", "review"):
        assert cfg.jira.key_for(level) == "MYPROJ"


def test_jira_project_keys_override_specific_levels(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path(".specify").mkdir()
    Path(".specify/integrations.yml").write_text(
        "jira:\n"
        "  project_key: SUN\n"
        "  project_keys:\n"
        "    story: SUNT\n"
        "    task: SUNT\n"
    )
    cfg = load_integrations()
    assert cfg.jira.key_for("feature") == "SUN"   # not overridden -- falls back
    assert cfg.jira.key_for("review") == "SUN"    # not overridden -- falls back
    assert cfg.jira.key_for("story") == "SUNT"
    assert cfg.jira.key_for("task") == "SUNT"


def test_jira_custom_fields_by_level_default_to_common_mapping(tmp_path, monkeypatch):
    """No custom_fields_by_level: block -- every level uses the common
    custom_fields mapping unchanged."""
    monkeypatch.chdir(tmp_path)
    Path(".specify").mkdir()
    Path(".specify/integrations.yml").write_text(
        "jira:\n"
        "  project_key: MYPROJ\n"
        "  custom_fields:\n"
        "    story_points: customfield_10016\n"
    )
    cfg = load_integrations()
    assert cfg.jira.custom_fields_by_level == {}
    assert cfg.jira.fields_for("story") == {"story_points": "customfield_10016"}
    assert cfg.jira.fields_for("task") == {"story_points": "customfield_10016"}


def test_jira_custom_fields_by_level_override_wins_per_key(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path(".specify").mkdir()
    Path(".specify/integrations.yml").write_text(
        "jira:\n"
        "  project_key: SUN\n"
        "  project_keys:\n"
        "    story: SUNT\n"
        "  custom_fields:\n"
        "    story_points: customfield_10016\n"
        "    fr_reference: customfield_10020\n"
        "  custom_fields_by_level:\n"
        "    story:\n"
        "      story_points: customfield_99001\n"
    )
    cfg = load_integrations()
    story_fields = cfg.jira.fields_for("story")
    # story_points overridden for the story level ...
    assert story_fields["story_points"] == "customfield_99001"
    # ... but fr_reference isn't listed in the override, so it still
    # falls back to the common mapping
    assert story_fields["fr_reference"] == "customfield_10020"
    # feature level has no override at all -- untouched common mapping
    assert cfg.jira.fields_for("feature") == {
        "story_points": "customfield_10016",
        "fr_reference": "customfield_10020",
    }


def test_jira_team_defaults_to_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path(".specify").mkdir()
    Path(".specify/integrations.yml").write_text(
        "jira:\n  project_key: MYPROJ\n"
    )
    cfg = load_integrations()
    assert cfg.jira.team is None


def test_jira_team_parsed_from_base_fields(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path(".specify").mkdir()
    Path(".specify/integrations.yml").write_text(
        "jira:\n"
        "  project_key: MYPROJ\n"
        "  base_fields:\n"
        "    team: Team Phoenix\n"
    )
    cfg = load_integrations()
    assert cfg.jira.team == "Team Phoenix"


def test_jira_parent_field_by_level_defaults_to_common_value(tmp_path, monkeypatch):
    """No parent_field_by_level: block -- every level uses the common
    parent_field unchanged."""
    monkeypatch.chdir(tmp_path)
    Path(".specify").mkdir()
    Path(".specify/integrations.yml").write_text(
        "jira:\n  project_key: MYPROJ\n"
    )
    cfg = load_integrations()
    assert cfg.jira.parent_field_by_level == {}
    for level in ("feature", "story", "task", "chg", "review"):
        assert cfg.jira.parent_field_for(level) == "parent"


def test_jira_parent_field_by_level_override_wins_per_level(tmp_path, monkeypatch):
    """parent_field_for(level) describes the field on the CHILD issue at
    that level (e.g. level="story" when linking a Story under its Epic)
    -- an org whose Story/Task project (via project_keys) is a classic
    company-managed project needing the Epic Link custom field, while the
    Epic's own project is next-gen, would set this only for "story"."""
    monkeypatch.chdir(tmp_path)
    Path(".specify").mkdir()
    Path(".specify/integrations.yml").write_text(
        "jira:\n"
        "  project_key: SUN\n"
        "  project_keys:\n"
        "    story: SUNT\n"
        "  parent_field: parent\n"
        "  parent_field_by_level:\n"
        "    story: customfield_10014\n"
    )
    cfg = load_integrations()
    assert cfg.jira.parent_field_for("story") == "customfield_10014"
    # task/chg/review are not listed -- fall back to the common value
    assert cfg.jira.parent_field_for("task") == "parent"
    assert cfg.jira.parent_field_for("chg") == "parent"
    assert cfg.jira.parent_field_for("review") == "parent"


class _Answer:
    """Stand-in for questionary's Question object -- .ask() returns a
    canned value instead of driving a real prompt_toolkit UI, which
    doesn't work under CliRunner's plain stdin feeding."""
    def __init__(self, value):
        self._value = value

    def ask(self):
        return self._value


class TestConfigInitCommand:
    """End-to-end test of the `sdd config init` wizard, both credential
    storage paths. Interactive prompts are mocked at the questionary
    function level (not via CliRunner stdin) -- questionary's
    prompt_toolkit UI needs a real TTY-like input source that CliRunner's
    plain stdin feeding doesn't provide."""

    @pytest.fixture()
    def runner(self):
        return CliRunner()

    @pytest.fixture()
    def config_home(self, tmp_path, monkeypatch):
        path = tmp_path / ".sdd" / "config.yml"
        # config_init() reads/checks CONFIG_PATH via the name imported into
        # config.py, but the actual write happens inside save_config() in
        # atlassian_auth.py, which references that module's OWN CONFIG_PATH
        # binding -- both must be patched or save_config() falls through to
        # the real ~/.sdd/config.yml on whatever machine runs this test.
        monkeypatch.setattr(config_mod, "CONFIG_PATH", path)
        monkeypatch.setattr(atlassian_auth, "CONFIG_PATH", path)
        monkeypatch.chdir(tmp_path)
        return path

    def test_keyring_path_stores_secret_and_no_env_field(self, runner, config_home):
        with patch("questionary.text", side_effect=[
                _Answer("work-cloud"), _Answer("https://x.atlassian.net"), _Answer("a@b.com")]), \
             patch("questionary.select", side_effect=[_Answer("basic"), _Answer("keyring")]), \
             patch("questionary.password", return_value=_Answer("secret-token")), \
             patch("questionary.confirm", return_value=_Answer(False)), \
             patch.object(config_mod, "store_secret") as store:
            result = runner.invoke(config_command, ["init"])

        assert result.exit_code == 0, result.output
        store.assert_called_once_with("work-cloud", "secret-token")

        saved = yaml.safe_load(config_home.read_text())
        profile = saved["profiles"]["work-cloud"]
        assert profile["credential_store"] == "keyring"
        assert profile["auth_mode"] == "basic"
        assert profile["email"] == "a@b.com"
        assert "api_token_env" not in profile  # no env var name for a keyring profile

    def test_env_path_stores_env_var_name_not_secret(self, runner, config_home):
        with patch("questionary.text", side_effect=[
                _Answer("work-cloud"), _Answer("https://x.atlassian.net"),
                _Answer("a@b.com"), _Answer("JIRA_API_TOKEN")]), \
             patch("questionary.select", side_effect=[_Answer("basic"), _Answer("env")]), \
             patch("questionary.confirm", return_value=_Answer(False)), \
             patch.object(config_mod, "store_secret") as store:
            result = runner.invoke(config_command, ["init"])

        assert result.exit_code == 0, result.output
        store.assert_not_called()  # env path never touches the keychain

        saved = yaml.safe_load(config_home.read_text())
        profile = saved["profiles"]["work-cloud"]
        assert profile["credential_store"] == "env"
        assert profile["api_token_env"] == "JIRA_API_TOKEN"
        # the actual secret value is never in this file, only the env var name
        assert "secret-token" not in config_home.read_text()

    def test_keyring_storage_failure_exits_nonzero_without_partial_config(self, runner, config_home):
        """If the keychain backend isn't available (e.g. headless Linux),
        the wizard must fail loudly rather than silently falling back to
        an unsaved or half-configured profile."""
        with patch("questionary.text", side_effect=[
                _Answer("work-cloud"), _Answer("https://x.atlassian.net"), _Answer("a@b.com")]), \
             patch("questionary.select", side_effect=[_Answer("basic"), _Answer("keyring")]), \
             patch("questionary.password", return_value=_Answer("secret-token")), \
             patch.object(config_mod, "store_secret",
                           side_effect=RuntimeError("no backend available")):
            result = runner.invoke(config_command, ["init"])

        assert result.exit_code != 0
        assert "no backend available" in result.output


class TestConfigSetSecretCommand:
    """`sdd config set-secret` — the CLI entry point for rotating a
    keychain-stored credential. store_secret() itself (the actual keyring
    call) is covered in test_atlassian_auth.py; these tests cover the
    command's own validation and error paths."""

    @pytest.fixture()
    def runner(self):
        return CliRunner()

    @pytest.fixture()
    def config_home(self, tmp_path, monkeypatch):
        path = tmp_path / ".sdd" / "config.yml"
        monkeypatch.setattr(config_mod, "CONFIG_PATH", path)
        return path

    def test_missing_config_file_exits_nonzero(self, runner, config_home):
        result = runner.invoke(config_command, ["set-secret", "--profile", "work"])
        assert result.exit_code != 0
        assert "config init" in result.output

    def test_unknown_profile_exits_nonzero(self, runner, config_home):
        config_home.parent.mkdir(parents=True)
        config_home.write_text(yaml.dump({"profiles": {"other": {"auth_mode": "basic"}}}))
        result = runner.invoke(config_command, ["set-secret", "--profile", "work"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_env_profile_rejected_with_guidance(self, runner, config_home):
        config_home.parent.mkdir(parents=True)
        config_home.write_text(yaml.dump({
            "profiles": {"work": {"auth_mode": "basic", "credential_store": "env"}}
        }))
        result = runner.invoke(config_command, ["set-secret", "--profile", "work"])
        assert result.exit_code != 0
        assert "credential_store: env" in result.output
        assert "sdd config init" in result.output

    def test_keyring_profile_stores_new_secret(self, runner, config_home):
        config_home.parent.mkdir(parents=True)
        config_home.write_text(yaml.dump({
            "profiles": {"work": {"auth_mode": "basic", "credential_store": "keyring"}}
        }))
        fake_answer = type("Q", (), {"ask": lambda self: "new-secret"})()
        with patch("questionary.password", return_value=fake_answer) as pw, \
             patch.object(config_mod, "store_secret") as store:
            result = runner.invoke(config_command, ["set-secret", "--profile", "work"])
        assert result.exit_code == 0
        assert "✓" in result.output
        store.assert_called_once_with("work", "new-secret")

    def test_keychain_backend_failure_surfaces_and_exits_nonzero(self, runner, config_home):
        config_home.parent.mkdir(parents=True)
        config_home.write_text(yaml.dump({
            "profiles": {"work": {"auth_mode": "basic", "credential_store": "keyring"}}
        }))
        fake_answer = type("Q", (), {"ask": lambda self: "new-secret"})()
        with patch("questionary.password", return_value=fake_answer), \
             patch.object(config_mod, "store_secret",
                           side_effect=RuntimeError("no backend available")):
            result = runner.invoke(config_command, ["set-secret", "--profile", "work"])
        assert result.exit_code != 0
        assert "no backend available" in result.output
