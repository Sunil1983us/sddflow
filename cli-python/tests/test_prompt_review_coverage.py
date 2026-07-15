# Structural coverage test: every doc key with an ACTIVE document_reviews
# entry in the shipped integrations.yml.example must have a real
# `sdd review submit --doc {key}` call somewhere in its owning
# .prompt.md file, in every pack.
#
# This is the cheap version of "run the whole pipeline against a mocked
# Jira/Confluence and assert every phase fires a review call" -- prompts
# are markdown instructions for an AI agent, not executable code, so
# there's no way to "run" one in CI. What IS checkable without simulating
# an AI is whether the review-submission call is present in the text at
# all. It would have caught the real bug this test exists because of:
# release.prompt.md and implement.prompt.md's runbook step had zero
# Jira/Confluence wiring despite document_reviews.release/.runbook being
# fully configured in the shipped example (see CHANGELOG 2.7.76).
#
# A prompt can satisfy the check two ways, both used across the packs:
#   - templated:  the file sets `doc_key` = `{key}`. once, then reuses
#                 `sdd review submit --doc {doc_key}` from the shared
#                 submit-for-review-step block (specify-brd, task, ...)
#   - literal:    the file writes `sdd review submit --doc {key}`
#                 directly, no {doc_key} indirection (validate, analyze,
#                 clarify)
from pathlib import Path

import pytest
import yaml

_PACKS_DIR = Path(__file__).resolve().parents[2] / "packs"
_ALL_PACKS = [
    "sdd-backend-service",
    "sdd-frontend-spa",
    "sdd-mobile",
    "sdd-fullstack",
    "sdd-universal",
]

# doc_key -> the .prompt.md file that's responsible for submitting it for review.
_DOC_KEY_TO_PROMPT = {
    "brd":        "specify-brd.prompt.md",
    "use-cases":  "specify-uc.prompt.md",
    "srd":        "specify-srd.prompt.md",
    "design":     "plan-design.prompt.md",
    "validate":   "validate.prompt.md",
    "analyze":    "analyze.prompt.md",
    "clarify":    "clarify.prompt.md",
    "lld":        "plan-lld.prompt.md",
    "tasks":      "task.prompt.md",
    "runbook":    "implement.prompt.md",
    "release":    "release.prompt.md",
}


def _active_document_review_keys(pack: str) -> set[str]:
    example = _PACKS_DIR / pack / ".specify" / "integrations.yml.example"
    data = yaml.safe_load(example.read_text())
    return set(data.get("document_reviews") or {})


def _prompt_submits_doc_for_review(text: str, key: str) -> bool:
    templated = f"`doc_key` = `{key}`." in text and "sdd review submit --doc {doc_key}" in text
    literal = f"sdd review submit --doc {key}" in text
    return templated or literal


def _cases():
    cases = []
    for pack in _ALL_PACKS:
        for key in sorted(_active_document_review_keys(pack)):
            if key not in _DOC_KEY_TO_PROMPT:
                continue  # not every active key maps to a single-command prompt (e.g. arch/hld/adr, plan_mode-conditional)
            cases.append((pack, key))
    return cases


@pytest.mark.parametrize("pack,key", _cases())
def test_active_document_review_key_is_actually_submitted(pack, key):
    prompt_file = _DOC_KEY_TO_PROMPT[key]
    path = _PACKS_DIR / pack / ".github" / "prompts" / prompt_file
    assert path.exists(), f"{pack}: {prompt_file} does not exist for doc key '{key}'"
    text = path.read_text()
    assert _prompt_submits_doc_for_review(text, key), (
        f"{pack}/{prompt_file}: document_reviews.{key} is configured in "
        f"integrations.yml.example, but {prompt_file} has no "
        f"'sdd review submit --doc {key}' call -- this doc key is "
        f"documented as Jira/Confluence-reviewed but the prompt never "
        f"actually submits it."
    )


def test_doc_key_to_prompt_map_covers_every_active_key_across_all_packs():
    """Guards the mapping itself -- if a future integrations.yml.example
    change adds a new document_reviews key, this fails loudly instead of
    the parametrized test above silently skipping the unmapped key."""
    unmapped = set()
    for pack in _ALL_PACKS:
        for key in _active_document_review_keys(pack):
            if key not in _DOC_KEY_TO_PROMPT:
                unmapped.add(key)
    # arch/hld/adr are plan_mode: separate keys, intentionally commented
    # out (inactive) in the shipped unified-mode-default example -- if
    # they ever show up here as "active", the example's default plan_mode
    # assumption has changed and this map needs a matching update.
    assert unmapped <= set(), (
        f"document_reviews key(s) {unmapped} are active in a shipped "
        f"integrations.yml.example but have no entry in "
        f"_DOC_KEY_TO_PROMPT -- add them so this test suite actually "
        f"covers them instead of silently skipping."
    )
