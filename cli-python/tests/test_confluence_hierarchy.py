# Unit tests for confluence.py's Project -> Feature page-hierarchy helpers.
# Confluence enforces page-title uniqueness per SPACE, not per parent page,
# so nesting is purely a navigation convenience -- these tests confirm the
# nesting itself works AND that it never becomes a substitute for
# collision-safe titles (that's covered separately by the {feature}
# title-substitution tests in test_multi_feature_integrations.py and
# test_review_helpers.py). Run from repo root: pytest cli-python/tests -q
import pytest

from sdd.commands.confluence import (
    _ensure_container_page, resolve_feature_parent_id, resolve_doc_parent_id,
)
from sdd.utils.integrations import ConfluenceConfig


class FakeConfluenceClient:
    """In-memory double -- records ancestry via parent_id so tests can
    assert the actual tree shape, not just that some ID was returned."""
    def __init__(self):
        self.pages_by_title: dict[str, dict] = {}
        self.create_calls: list[tuple[str, str, str | None]] = []
        self._next_id = 1

    def get_page_by_title(self, space_key, title):
        return self.pages_by_title.get(title)

    def create_page(self, space_key, title, body_html, parent_id=None):
        self.create_calls.append((space_key, title, parent_id))
        page = {"id": str(self._next_id), "parent_id": parent_id}
        self._next_id += 1
        self.pages_by_title[title] = page
        return page


class TestEnsureContainerPage:
    def test_creates_page_when_not_found(self):
        client = FakeConfluenceClient()
        page_id = _ensure_container_page(client, "ENG", "MyProject", "ROOT-1")
        assert page_id == "1"
        assert client.create_calls == [("ENG", "MyProject", "ROOT-1")]

    def test_idempotent_second_call_does_not_recreate(self):
        client = FakeConfluenceClient()
        first = _ensure_container_page(client, "ENG", "MyProject", "ROOT-1")
        second = _ensure_container_page(client, "ENG", "MyProject", "ROOT-1")
        assert first == second
        assert len(client.create_calls) == 1


class TestResolveFeatureParentId:
    def _cf_cfg(self, parent_page_id="ROOT-1"):
        return ConfluenceConfig(space_key="ENG", parent_page_id=parent_page_id)

    def test_creates_project_then_feature_page(self):
        client = FakeConfluenceClient()
        feature_page_id = resolve_feature_parent_id(client, self._cf_cfg(), "MyProject", "auth")

        project_page = client.pages_by_title["MyProject"]
        feature_page = client.pages_by_title["auth"]
        assert feature_page_id == feature_page["id"]
        # Feature page's parent is the Project page -- not the config root directly
        assert feature_page["parent_id"] == project_page["id"]
        # Project page's parent is the configured root
        assert project_page["parent_id"] == "ROOT-1"

    def test_idempotent_across_calls_and_features(self):
        client = FakeConfluenceClient()
        resolve_feature_parent_id(client, self._cf_cfg(), "MyProject", "auth")
        resolve_feature_parent_id(client, self._cf_cfg(), "MyProject", "billing")
        # One Project page shared by both features, two distinct Feature pages
        assert len(client.create_calls) == 3
        assert client.pages_by_title["auth"]["parent_id"] == client.pages_by_title["MyProject"]["id"]
        assert client.pages_by_title["billing"]["parent_id"] == client.pages_by_title["MyProject"]["id"]

    def test_works_with_no_configured_root(self):
        client = FakeConfluenceClient()
        resolve_feature_parent_id(client, self._cf_cfg(parent_page_id=None), "MyProject", "auth")
        project_page = client.pages_by_title["MyProject"]
        assert project_page["parent_id"] is None


class TestResolveDocParentId:
    def _cf_cfg(self):
        return ConfluenceConfig(space_key="ENG", parent_page_id="ROOT-1")

    def test_per_feature_doc_nests_under_feature_page(self):
        client = FakeConfluenceClient()
        parent_id = resolve_doc_parent_id(client, self._cf_cfg(), "MyProject", "auth", "brd")
        assert parent_id == client.pages_by_title["auth"]["id"]

    def test_living_service_doc_nests_directly_under_project_page(self):
        client = FakeConfluenceClient()
        parent_id = resolve_doc_parent_id(client, self._cf_cfg(), "MyProject", "auth", "data-model")
        assert parent_id == client.pages_by_title["MyProject"]["id"]
        # No Feature-level container page created for a living doc
        assert "auth" not in client.pages_by_title

    def test_living_service_doc_is_shared_across_features(self):
        client = FakeConfluenceClient()
        p1 = resolve_doc_parent_id(client, self._cf_cfg(), "MyProject", "auth", "security-design")
        p2 = resolve_doc_parent_id(client, self._cf_cfg(), "MyProject", "billing", "security-design")
        assert p1 == p2  # same Project-level parent regardless of which feature pushed it
