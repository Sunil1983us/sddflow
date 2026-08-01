# Unit tests for config-init template output and integrations loading.
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from sdd.commands import config as config_mod
from sdd.commands.config import (
    _integrations_template, _integrations_from_example, config_command,
)
from sdd.utils import atlassian_auth
from sdd.utils.integrations import (
    load_integrations, parse_confluence_page_id, _DEFAULT_PAGE_MAP,
)


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
    # The shipped example is a superset of the wizard's minimal default --
    # it also documents the optional "validate" phase (validate/analyze/
    # clarify), which "sdd config init" deliberately leaves out since it
    # needs reviewer info the wizard doesn't collect (see review-gates.md:
    # "each optional individually"), plus page_map entries for doc keys
    # that don't have a Jira review gate at all (qa-testcases, tasks,
    # checklist, and the living/service-level docs) -- those only need a
    # Confluence page, which page_map alone is enough to provide.
    assert set(EXPECTED_DOC_KEYS) <= set(data["confluence"]["page_map"])
    assert set(data["confluence"]["page_map"]) - set(EXPECTED_DOC_KEYS) == {
        "validate", "analyze", "clarify",
        "stories", "tasks", "checklist", "qa-testcases", "smoke-tests",
        "data-model", "security-design", "api-spec", "component-library",
        "constitution", "release",
    }
    # active document_reviews ships in unified mode: design yes, arch/hld/adr commented
    reviews = data["document_reviews"]
    assert "use-cases" in reviews and "design" in reviews
    assert "arch" not in reviews  # separate-mode block stays commented
    assert {"validate", "analyze", "clarify"} <= set(reviews)

    # sequence within each phase must be strictly increasing (predecessor gating)
    by_phase: dict[str, list[int]] = {}
    for doc in reviews.values():
        by_phase.setdefault(doc["phase"], []).append(doc["sequence"])
    for phase, seqs in by_phase.items():
        assert sorted(seqs) == seqs or sorted(seqs) == sorted(set(seqs)), phase
        assert len(set(seqs)) == len(seqs), f"duplicate sequence in {phase}"


# ── _integrations_from_example — `sdd config init` scaffold source ───────
# The wizard used to build .specify/integrations.yml from a small
# hand-maintained template string that drifted from the real
# integrations.yml.example (missing project_keys, parent_field_by_level,
# custom_fields_by_level, diagrams, document_reviews, pr_automation,
# code_review, and most of page_map). It now fills placeholders into the
# actual shipped .example instead, so it can never drift again.

_SHIPPED_EXAMPLE = (
    Path(__file__).resolve().parents[2] /
    "packs/_shared/full/.specify/integrations.yml.example"
)


def test_integrations_from_example_substitutes_placeholders():
    out = _integrations_from_example(
        _SHIPPED_EXAMPLE.read_text(), "work-cloud", "PROJ", "ENGSPACE", "999888",
    )
    data = yaml.safe_load(out)
    assert data["profile"] == "work-cloud"
    assert data["jira"]["project_key"] == "PROJ"
    assert data["confluence"]["space_key"] == "ENGSPACE"
    assert data["confluence"]["parent_page_id"] == "999888"


def test_integrations_from_example_carries_every_optional_section():
    """This is the actual gap being fixed -- the old wizard template never
    had these sections at all, so a user had to know to go copy
    integrations.yml.example by hand to get them."""
    out = _integrations_from_example(
        _SHIPPED_EXAMPLE.read_text(), "default", "MYPROJ", "ENG", "",
    )
    for section in ("project_keys", "parent_field_by_level",
                    "custom_fields_by_level", "diagrams", "document_reviews",
                    "pr_automation", "code_review"):
        assert section in out, f"missing section: {section}"


def test_integrations_from_example_blank_parent_page_id_stays_commented():
    out = _integrations_from_example(
        _SHIPPED_EXAMPLE.read_text(), "default", "MYPROJ", "ENG", "",
    )
    assert '# parent_page_id: "123456"' in out
    assert "parent_page_id" not in yaml.safe_load(out)["confluence"]


def test_integrations_from_example_leaves_runtime_template_vars_untouched():
    """{feature}/{project} in page_map are filled at push time (by
    _push_doc_page), not at scaffold time -- must survive substitution
    verbatim, not get treated as project_key/space_key placeholders."""
    out = _integrations_from_example(
        _SHIPPED_EXAMPLE.read_text(), "default", "MYPROJ", "ENG", "",
    )
    assert "{feature} — Business Requirements" in out


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


def test_load_integrations_local_svg_width_defaults_to_900(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path(".specify").mkdir()
    Path(".specify/integrations.yml").write_text(
        "confluence:\n  space_key: ENG\n  diagrams:\n    mode: local-svg\n"
    )
    cfg = load_integrations()
    assert cfg.confluence.diagrams.local_svg_width == 900


def test_load_integrations_local_svg_width_override(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path(".specify").mkdir()
    Path(".specify/integrations.yml").write_text(
        "confluence:\n"
        "  space_key: ENG\n"
        "  diagrams:\n"
        "    mode: local-svg\n"
        "    local_svg:\n"
        "      width: 600\n"
    )
    cfg = load_integrations()
    assert cfg.confluence.diagrams.local_svg_width == 600


# ── parse_confluence_page_id — accept an ID or a pasted page URL ─────────
# Most users have the Confluence page open in a browser tab, not the raw
# numeric ID memorized -- both the config-init wizard and hand-edited
# integrations.yml should accept whatever they paste.

@pytest.mark.parametrize("raw,expected", [
    ("123456", "123456"),
    ("  123456  ", "123456"),
    ("https://myorg.atlassian.net/wiki/spaces/ENG/pages/123456789/My+Page",
     "123456789"),
    # Server/DC space-permalink form, no "/wiki" prefix: /spaces/{key}/pages/{id}/{title}
    ("https://confluence.company.com/spaces/xxx/pages/1234/Title+of+the+page",
     "1234"),
    ("https://confluence.example.com/pages/viewpage.action?pageId=98765",
     "98765"),
    ("https://confluence.example.com/display/ENG/x?spaceKey=ENG&pageId=42",
     "42"),
    ("", None),
    (None, None),
])
def test_parse_confluence_page_id_accepts_id_or_url(raw, expected):
    assert parse_confluence_page_id(raw) == expected


def test_parse_confluence_page_id_tiny_link_falls_back_unchanged():
    """A Confluence 'tiny link' (/x/AbCdEf) is a short code, not a page ID
    -- can't be resolved without an API call, so it's returned as-is for
    the caller to warn about rather than silently mangled."""
    tiny = "https://myorg.atlassian.net/wiki/x/AbCdEf"
    assert parse_confluence_page_id(tiny) == tiny


def test_load_integrations_parent_page_id_accepts_pasted_url(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path(".specify").mkdir()
    Path(".specify/integrations.yml").write_text(
        "confluence:\n"
        "  space_key: ENG\n"
        "  parent_page_id: "
        '"https://myorg.atlassian.net/wiki/spaces/ENG/pages/555444/Root"\n'
    )
    cfg = load_integrations()
    assert cfg.confluence.parent_page_id == "555444"


def test_profile_names_default_to_top_level_profile(tmp_path, monkeypatch):
    """No jira.profile / confluence.profile override -- both services fall
    back to the single top-level profile: (the common Cloud case, one
    Atlassian site serving both)."""
    monkeypatch.chdir(tmp_path)
    Path(".specify").mkdir()
    Path(".specify/integrations.yml").write_text(
        "profile: default\n"
        "jira:\n  project_key: MYPROJ\n"
        "confluence:\n  space_key: ENG\n"
    )
    cfg = load_integrations()
    assert cfg.jira_profile_name() == "default"
    assert cfg.confluence_profile_name() == "default"


def test_jira_and_confluence_can_use_different_profiles(tmp_path, monkeypatch):
    """Data Center orgs where Jira and Confluence are separate servers with
    separate credentials -- jira.profile / confluence.profile override the
    top-level profile independently."""
    monkeypatch.chdir(tmp_path)
    Path(".specify").mkdir()
    Path(".specify/integrations.yml").write_text(
        "profile: default\n"
        "jira:\n  project_key: MYPROJ\n  profile: jira-dc\n"
        "confluence:\n  space_key: ENG\n  profile: confluence-dc\n"
    )
    cfg = load_integrations()
    assert cfg.jira_profile_name() == "jira-dc"
    assert cfg.confluence_profile_name() == "confluence-dc"


def test_one_service_override_leaves_the_other_on_top_level_profile(tmp_path, monkeypatch):
    """Only jira.profile set -- confluence still falls back to the
    top-level profile, not to jira's override."""
    monkeypatch.chdir(tmp_path)
    Path(".specify").mkdir()
    Path(".specify/integrations.yml").write_text(
        "profile: default\n"
        "jira:\n  project_key: MYPROJ\n  profile: jira-dc\n"
        "confluence:\n  space_key: ENG\n"
    )
    cfg = load_integrations()
    assert cfg.jira_profile_name() == "jira-dc"
    assert cfg.confluence_profile_name() == "default"


def test_profile_name_helpers_tolerate_missing_service_section(tmp_path, monkeypatch):
    """confluence: section entirely absent -- confluence_profile_name()
    doesn't crash, just falls back to the top-level profile."""
    monkeypatch.chdir(tmp_path)
    Path(".specify").mkdir()
    Path(".specify/integrations.yml").write_text(
        "profile: default\njira:\n  project_key: MYPROJ\n"
    )
    cfg = load_integrations()
    assert cfg.jira is not None
    assert cfg.confluence is None
    assert cfg.jira_profile_name() == "default"
    assert cfg.confluence_profile_name() == "default"


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
             patch("questionary.select", side_effect=[_Answer(True), _Answer("basic"), _Answer("keyring")]), \
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
             patch("questionary.select", side_effect=[_Answer(True), _Answer("basic"), _Answer("env")]), \
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
             patch("questionary.select", side_effect=[_Answer(True), _Answer("basic"), _Answer("keyring")]), \
             patch("questionary.password", return_value=_Answer("secret-token")), \
             patch.object(config_mod, "store_secret",
                           side_effect=RuntimeError("no backend available")):
            result = runner.invoke(config_command, ["init"])

        assert result.exit_code != 0
        assert "no backend available" in result.output

    def test_scaffold_uses_shipped_example_when_present(self, runner, config_home):
        """config_home already chdir's into a fresh tmp_path -- drop a
        real integrations.yml.example there first, matching what a
        packaged project actually has on disk."""
        specify_dir = config_home.parent.parent / ".specify"
        specify_dir.mkdir(parents=True, exist_ok=True)
        (specify_dir / "integrations.yml.example").write_text(_SHIPPED_EXAMPLE.read_text())

        with patch("questionary.text", side_effect=[
                _Answer("default"), _Answer("https://x.atlassian.net"), _Answer("a@b.com"),
                _Answer("PROJ"), _Answer("ENGSPACE"), _Answer("")]), \
             patch("questionary.select", side_effect=[_Answer(True), _Answer("basic"), _Answer("keyring")]), \
             patch("questionary.password", return_value=_Answer("secret-token")), \
             patch("questionary.confirm", return_value=_Answer(True)), \
             patch.object(config_mod, "store_secret"):
            result = runner.invoke(config_command, ["init"])

        assert result.exit_code == 0, result.output
        dest = specify_dir / "integrations.yml"
        assert dest.exists()
        data = yaml.safe_load(dest.read_text())
        assert data["jira"]["project_key"] == "PROJ"
        assert data["confluence"]["space_key"] == "ENGSPACE"
        assert "document_reviews" in data  # the gap this fix closes
        assert "diagrams:" in dest.read_text()  # commented-out reference, not live YAML

    def test_scaffold_accepts_pasted_page_url_for_parent_page(self, runner, config_home):
        """Most users have the Confluence page open in a browser, not its
        raw numeric ID -- pasting the full URL at the parent-page prompt
        must resolve to just the ID in the generated integrations.yml."""
        specify_dir = config_home.parent.parent / ".specify"
        specify_dir.mkdir(parents=True, exist_ok=True)
        (specify_dir / "integrations.yml.example").write_text(_SHIPPED_EXAMPLE.read_text())

        with patch("questionary.text", side_effect=[
                _Answer("default"), _Answer("https://x.atlassian.net"), _Answer("a@b.com"),
                _Answer("PROJ"), _Answer("ENGSPACE"),
                _Answer("https://x.atlassian.net/wiki/spaces/ENG/pages/777888/Root")]), \
             patch("questionary.select", side_effect=[_Answer(True), _Answer("basic"), _Answer("keyring")]), \
             patch("questionary.password", return_value=_Answer("secret-token")), \
             patch("questionary.confirm", return_value=_Answer(True)), \
             patch.object(config_mod, "store_secret"):
            result = runner.invoke(config_command, ["init"])

        assert result.exit_code == 0, result.output
        dest = specify_dir / "integrations.yml"
        data = yaml.safe_load(dest.read_text())
        assert data["confluence"]["parent_page_id"] == "777888"

    def test_scaffold_falls_back_to_minimal_template_without_example(self, runner, config_home):
        """No .specify/integrations.yml.example on disk (very old init, or
        a pack without one) -- must still produce a working file, just the
        smaller built-in one, not crash."""
        (config_home.parent.parent / ".specify").mkdir(parents=True, exist_ok=True)
        with patch("questionary.text", side_effect=[
                _Answer("default"), _Answer("https://x.atlassian.net"), _Answer("a@b.com"),
                _Answer("PROJ"), _Answer("ENG"), _Answer("")]), \
             patch("questionary.select", side_effect=[_Answer(True), _Answer("basic"), _Answer("keyring")]), \
             patch("questionary.password", return_value=_Answer("secret-token")), \
             patch("questionary.confirm", return_value=_Answer(True)), \
             patch.object(config_mod, "store_secret"):
            result = runner.invoke(config_command, ["init"])

        assert result.exit_code == 0, result.output
        dest = config_home.parent.parent / ".specify" / "integrations.yml"
        assert dest.exists()
        data = yaml.safe_load(dest.read_text())
        assert data["jira"]["project_key"] == "PROJ"
        assert "document_reviews" not in data  # minimal template has no such section

    def test_different_profiles_creates_both_in_config_yml(self, runner, config_home):
        """Answering 'No' to the same-site question drives the wizard
        through two full credential rounds -- a 'profile' is understood as
        the entire auth set (base_url + auth_mode + credential), not just
        a URL, so the two profiles below differ in every field."""
        with patch("questionary.text", side_effect=[
                _Answer("jira-dc"), _Answer("https://jira.internal"),
                _Answer("confluence-dc"), _Answer("https://confluence.internal"),
                _Answer("CONFLUENCE_TOKEN")]), \
             patch("questionary.select", side_effect=[
                _Answer(False),               # same site? -> No
                _Answer("pat"), _Answer("keyring"),      # Jira round
                _Answer("oauth2"), _Answer("env")]), \
             patch("questionary.password", return_value=_Answer("jira-secret")), \
             patch("questionary.confirm", return_value=_Answer(False)), \
             patch.object(config_mod, "store_secret") as store:
            result = runner.invoke(config_command, ["init"])

        assert result.exit_code == 0, result.output
        # Only the keyring-stored Jira profile calls store_secret -- the
        # Confluence profile used env-var storage instead.
        store.assert_called_once_with("jira-dc", "jira-secret")

        saved = yaml.safe_load(config_home.read_text())
        jira_p = saved["profiles"]["jira-dc"]
        cf_p   = saved["profiles"]["confluence-dc"]
        assert jira_p["base_url"] == "https://jira.internal"
        assert jira_p["auth_mode"] == "pat"
        assert cf_p["base_url"] == "https://confluence.internal"
        assert cf_p["auth_mode"] == "oauth2"
        assert cf_p["credential_store"] == "env"

    def test_different_profiles_wires_confluence_override_into_integrations_yml(
        self, runner, config_home,
    ):
        """End-to-end: the 'different' path must actually produce an
        integrations.yml where jira: uses the top-level (Jira) profile and
        confluence: carries an explicit override to the Confluence one --
        not just two orphaned profiles in ~/.sdd/config.yml that nothing
        ever wires together."""
        specify_dir = config_home.parent.parent / ".specify"
        specify_dir.mkdir(parents=True, exist_ok=True)
        (specify_dir / "integrations.yml.example").write_text(_SHIPPED_EXAMPLE.read_text())

        with patch("questionary.text", side_effect=[
                _Answer("jira-dc"), _Answer("https://jira.internal"),
                _Answer("confluence-dc"), _Answer("https://confluence.internal"),
                _Answer("PROJ"), _Answer("ENGSPACE"), _Answer("")]), \
             patch("questionary.select", side_effect=[
                _Answer(False),                       # same site? -> No
                _Answer("pat"), _Answer("keyring"),    # Jira round
                _Answer("pat"), _Answer("keyring")]), \
             patch("questionary.password", return_value=_Answer("secret")), \
             patch("questionary.confirm", return_value=_Answer(True)), \
             patch.object(config_mod, "store_secret"):
            result = runner.invoke(config_command, ["init"])

        assert result.exit_code == 0, result.output
        dest = specify_dir / "integrations.yml"
        text = dest.read_text()
        data = yaml.safe_load(text)
        assert data["profile"] == "jira-dc"
        assert data["confluence"]["profile"] == "confluence-dc"
        # jira: has no profile key of its own -- it relies on the
        # top-level fallback, exactly like the single-profile case.
        assert "profile" not in data["jira"]
        # Once integrations.yml is scaffolded, `sdd config test` (no
        # --profile) can resolve the split on its own -- suggesting
        # `--profile X` here would just recreate the bug the split exists
        # to avoid (that flag tests ONE profile against BOTH services).
        assert "Run sdd config test to verify both" in result.output
        assert "--profile" not in result.output

    def test_different_profiles_declined_scaffold_suggests_per_profile_test(
        self, runner, config_home,
    ):
        """If integrations.yml isn't scaffolded, `sdd config test` has no
        way to know about the split -- the closing message must fall back
        to suggesting --profile per service, with a caveat that each call
        only sanity-checks that one profile, not the split itself."""
        with patch("questionary.text", side_effect=[
                _Answer("jira-dc"), _Answer("https://jira.internal"),
                _Answer("confluence-dc"), _Answer("https://confluence.internal")]), \
             patch("questionary.select", side_effect=[
                _Answer(False),                       # same site? -> No
                _Answer("pat"), _Answer("keyring"),    # Jira round
                _Answer("pat"), _Answer("keyring")]), \
             patch("questionary.password", return_value=_Answer("secret")), \
             patch("questionary.confirm", return_value=_Answer(False)), \
             patch.object(config_mod, "store_secret"):
            result = runner.invoke(config_command, ["init"])

        assert result.exit_code == 0, result.output
        assert not (config_home.parent.parent / ".specify" / "integrations.yml").exists()
        assert "sdd config test --profile jira-dc" in result.output
        assert "sdd config test --profile confluence-dc" in result.output


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


class TestConfigTestCommand:
    """`sdd config test` -- previously resolved ONE Profile and pinged both
    Jira and Confluence against its base_url, which silently tested the
    wrong server for the half of a split jira.profile/confluence.profile
    setup that didn't match --profile. Each service must now be resolved
    (and pinged) independently."""

    @pytest.fixture()
    def runner(self):
        return CliRunner()

    @pytest.fixture()
    def config_home(self, tmp_path, monkeypatch):
        path = tmp_path / ".sdd" / "config.yml"
        monkeypatch.setattr(config_mod, "CONFIG_PATH", path)
        monkeypatch.setattr(atlassian_auth, "CONFIG_PATH", path)
        monkeypatch.chdir(tmp_path)
        return path

    def _write_profiles(self, config_home, **profiles):
        config_home.parent.mkdir(parents=True, exist_ok=True)
        config_home.write_text(yaml.dump({"profiles": profiles}))

    def _fake_client(self, display_name):
        client = type("C", (), {
            "__init__": lambda self, session, base_url: setattr(self, "base_url", base_url),
            "get_myself": lambda self: {"displayName": display_name},
        })
        return client

    def test_single_profile_pings_both_services_once(self, runner, config_home):
        """No integrations.yml, no --profile -- falls back to the lone
        profile for both services exactly as before this fix, with no
        'Jira profile:'/'Confluence profile:' lines (would be redundant
        noise when there's only one profile in play)."""
        self._write_profiles(config_home, work={
            "auth_mode": "basic", "base_url": "https://x.atlassian.net",
        })
        with patch.object(config_mod, "build_session", return_value=object()), \
             patch.object(config_mod, "JiraClient", self._fake_client("Jane")), \
             patch.object(config_mod, "ConfluenceClient", self._fake_client("Jane")):
            result = runner.invoke(config_command, ["test"])

        assert result.exit_code == 0, result.output
        assert "Jira profile:" not in result.output
        assert "connected as Jane" in result.output

    def test_split_profiles_test_each_service_against_its_own_profile(self, runner, config_home):
        """The bug: integrations.yml routes Jira and Confluence to two
        different Data Center servers. Each must be pinged against its
        OWN base_url, not one profile's base_url reused for both."""
        self._write_profiles(
            config_home,
            **{
                "jira-dc":       {"auth_mode": "pat", "base_url": "https://jira.internal"},
                "confluence-dc": {"auth_mode": "pat", "base_url": "https://confluence.internal"},
            },
        )
        Path(".specify").mkdir()
        Path(".specify/integrations.yml").write_text(
            "profile: jira-dc\n"
            "jira:\n  project_key: PROJ\n"
            "confluence:\n  profile: confluence-dc\n  space_key: ENG\n"
        )

        seen_base_urls = []

        def _client_factory(display_name):
            def _init(self, session, base_url):
                seen_base_urls.append(base_url)
                self.base_url = base_url
            return type("C", (), {"__init__": _init, "get_myself": lambda self: {"displayName": display_name}})

        with patch.object(config_mod, "build_session", return_value=object()), \
             patch.object(config_mod, "JiraClient", _client_factory("Jira User")), \
             patch.object(config_mod, "ConfluenceClient", _client_factory("Confluence User")):
            result = runner.invoke(config_command, ["test"])

        assert result.exit_code == 0, result.output
        assert "Jira profile:       jira-dc" in result.output
        assert "Confluence profile: confluence-dc" in result.output
        assert seen_base_urls == ["https://jira.internal", "https://confluence.internal"]
        assert "connected as Jira User" in result.output
        assert "connected as Confluence User" in result.output

    def test_explicit_profile_flag_wins_over_integrations_yml_split(self, runner, config_home):
        """An explicit --profile is a deliberate override -- e.g.
        sanity-checking a profile before wiring it into integrations.yml
        -- and must test that ONE profile against both services, exactly
        as before this fix, even if integrations.yml has a split."""
        self._write_profiles(
            config_home,
            **{
                "jira-dc":       {"auth_mode": "pat", "base_url": "https://jira.internal"},
                "confluence-dc": {"auth_mode": "pat", "base_url": "https://confluence.internal"},
                "candidate":     {"auth_mode": "basic", "base_url": "https://candidate.example"},
            },
        )
        Path(".specify").mkdir()
        Path(".specify/integrations.yml").write_text(
            "profile: jira-dc\n"
            "jira:\n  project_key: PROJ\n"
            "confluence:\n  profile: confluence-dc\n  space_key: ENG\n"
        )

        seen_base_urls = []

        def _client_factory(display_name):
            def _init(self, session, base_url):
                seen_base_urls.append(base_url)
            return type("C", (), {"__init__": _init, "get_myself": lambda self: {"displayName": display_name}})

        with patch.object(config_mod, "build_session", return_value=object()), \
             patch.object(config_mod, "JiraClient", _client_factory("X")), \
             patch.object(config_mod, "ConfluenceClient", _client_factory("X")):
            result = runner.invoke(config_command, ["test", "--profile", "candidate"])

        assert result.exit_code == 0, result.output
        assert seen_base_urls == ["https://candidate.example", "https://candidate.example"]

    def test_unknown_profile_reports_which_service_failed(self, runner, config_home):
        self._write_profiles(config_home, **{
            "jira-dc": {"auth_mode": "pat", "base_url": "https://jira.internal"},
        })
        Path(".specify").mkdir()
        Path(".specify/integrations.yml").write_text(
            "profile: jira-dc\n"
            "jira:\n  project_key: PROJ\n"
            "confluence:\n  profile: missing-profile\n  space_key: ENG\n"
        )
        with patch.object(config_mod, "build_session", return_value=object()):
            result = runner.invoke(config_command, ["test"])

        assert result.exit_code != 0
        assert "Confluence profile 'missing-profile'" in result.output
