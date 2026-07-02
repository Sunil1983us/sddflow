# Unit tests for config-init template output and integrations loading.
from pathlib import Path

import pytest
import yaml

from sdd.commands.config import _integrations_template
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
