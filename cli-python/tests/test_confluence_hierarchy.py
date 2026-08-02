# Unit tests for confluence.py's Project -> Feature page-hierarchy helpers.
# Confluence enforces page-title uniqueness per SPACE, not per parent page,
# so nesting is purely a navigation convenience -- these tests confirm the
# nesting itself works AND that it never becomes a substitute for
# collision-safe titles (that's covered separately by the {feature}
# title-substitution tests in test_multi_feature_integrations.py and
# test_review_helpers.py). Run from repo root: pytest cli-python/tests -q

from sdd.commands.confluence import (
    _ensure_container_page,
    resolve_doc_parent_id,
    resolve_feature_parent_id,
    upload_diagram_attachments,
)
from sdd.utils.integrations import ConfluenceConfig


class FakeConfluenceClient:
    """In-memory double -- records ancestry via parent_id so tests can
    assert the actual tree shape, not just that some ID was returned."""

    def __init__(self):
        self.pages_by_title: dict[str, dict] = {}
        self.create_calls: list[tuple[str, str, str | None]] = []
        self.uploaded_attachments: list[tuple[str, str, bytes, str]] = []
        self._next_id = 1

    def get_page_by_title(self, space_key, title):
        return self.pages_by_title.get(title)

    def create_page(self, space_key, title, body_html, parent_id=None):
        self.create_calls.append((space_key, title, parent_id))
        page = {"id": str(self._next_id), "parent_id": parent_id}
        self._next_id += 1
        self.pages_by_title[title] = page
        return page

    def upload_attachment(self, page_id, filename, content, media_type="image/svg+xml"):
        self.uploaded_attachments.append((page_id, filename, content, media_type))
        return {"id": f"att-{filename}"}


class RaisingAttachmentClient(FakeConfluenceClient):
    """upload_attachment always fails -- used to confirm a failed upload
    warns rather than raising and aborting the rest of the push."""

    def upload_attachment(self, page_id, filename, content, media_type="image/svg+xml"):
        raise RuntimeError("HTTP 413 — attachment too large")


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
        feature_page_id = resolve_feature_parent_id(
            client, self._cf_cfg(), "MyProject", "auth"
        )

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
        assert (
            client.pages_by_title["auth"]["parent_id"]
            == client.pages_by_title["MyProject"]["id"]
        )
        assert (
            client.pages_by_title["billing"]["parent_id"]
            == client.pages_by_title["MyProject"]["id"]
        )

    def test_works_with_no_configured_root(self):
        client = FakeConfluenceClient()
        resolve_feature_parent_id(
            client, self._cf_cfg(parent_page_id=None), "MyProject", "auth"
        )
        project_page = client.pages_by_title["MyProject"]
        assert project_page["parent_id"] is None


class TestResolveDocParentId:
    def _cf_cfg(self):
        return ConfluenceConfig(space_key="ENG", parent_page_id="ROOT-1")

    def test_per_feature_doc_nests_under_feature_page(self):
        client = FakeConfluenceClient()
        parent_id = resolve_doc_parent_id(
            client, self._cf_cfg(), "MyProject", "auth", "brd"
        )
        assert parent_id == client.pages_by_title["auth"]["id"]

    def test_living_service_doc_nests_directly_under_project_page(self):
        client = FakeConfluenceClient()
        parent_id = resolve_doc_parent_id(
            client, self._cf_cfg(), "MyProject", "auth", "data-model"
        )
        assert parent_id == client.pages_by_title["MyProject"]["id"]
        # No Feature-level container page created for a living doc
        assert "auth" not in client.pages_by_title

    def test_living_service_doc_is_shared_across_features(self):
        client = FakeConfluenceClient()
        p1 = resolve_doc_parent_id(
            client, self._cf_cfg(), "MyProject", "auth", "security-design"
        )
        p2 = resolve_doc_parent_id(
            client, self._cf_cfg(), "MyProject", "billing", "security-design"
        )
        assert (
            p1 == p2
        )  # same Project-level parent regardless of which feature pushed it

    def test_constitution_nests_directly_under_project_page(self):
        client = FakeConfluenceClient()
        parent_id = resolve_doc_parent_id(
            client, self._cf_cfg(), "MyProject", "auth", "constitution"
        )
        assert parent_id == client.pages_by_title["MyProject"]["id"]
        assert "auth" not in client.pages_by_title

    def test_runbook_nests_directly_under_project_page(self):
        """runbook.md is generated by /implement (not /specify-doc) and
        lives at docs/runbook/local-setup.md rather than
        .specify/service/, but its Confluence page should still nest
        under the Project page like every other living/service-level
        doc — it's shared across every feature, not per-feature."""
        client = FakeConfluenceClient()
        parent_id = resolve_doc_parent_id(
            client, self._cf_cfg(), "MyProject", "auth", "runbook"
        )
        assert parent_id == client.pages_by_title["MyProject"]["id"]
        assert "auth" not in client.pages_by_title

    def test_runbook_is_shared_across_features(self):
        client = FakeConfluenceClient()
        p1 = resolve_doc_parent_id(
            client, self._cf_cfg(), "MyProject", "auth", "runbook"
        )
        p2 = resolve_doc_parent_id(
            client, self._cf_cfg(), "MyProject", "billing", "runbook"
        )
        assert p1 == p2


class TestUploadDiagramAttachments:
    """The local-svg mode's attach-after-upsert step: each rendered
    diagram queued by md_to_storage() gets uploaded to the page that was
    just created/updated with a body already referencing its filename."""

    def test_uploads_each_attachment_to_the_given_page(self):
        client = FakeConfluenceClient()
        attachments = [
            ("diagram-1.svg", b"<svg>a</svg>", "image/svg+xml"),
            ("diagram-2.svg", b"<svg>b</svg>", "image/svg+xml"),
        ]
        upload_diagram_attachments(client, "999", attachments)
        assert client.uploaded_attachments == [
            ("999", "diagram-1.svg", b"<svg>a</svg>", "image/svg+xml"),
            ("999", "diagram-2.svg", b"<svg>b</svg>", "image/svg+xml"),
        ]

    def test_empty_attachments_list_is_a_no_op(self):
        client = FakeConfluenceClient()
        upload_diagram_attachments(client, "999", [])
        assert client.uploaded_attachments == []

    def test_a_failed_upload_warns_but_does_not_raise(self, capsys):
        """The document content itself already saved successfully by
        the time attachments are uploaded -- a failed attachment must
        never look like the whole push failed."""
        client = RaisingAttachmentClient()
        upload_diagram_attachments(
            client, "999", [("diagram-1.svg", b"<svg/>", "image/svg+xml")]
        )  # must not raise
        out = capsys.readouterr().out
        assert "diagram-1.svg" in out
        assert "attachment upload failed" in out

    def test_http_error_surfaces_response_body_reason(self, capsys):
        """A bare 'requests.HTTPError: 400 Client Error: Bad Request for
        url: ...' names the status code but never the actual reason --
        that lives in the response body. A user hitting a real 400 (e.g.
        a specific diagram Confluence rejected) needs that reason to
        diagnose it, not just confirmation that something failed."""
        import requests

        class HTTPErrorClient(FakeConfluenceClient):
            def upload_attachment(
                self, page_id, filename, content, media_type="image/svg+xml"
            ):
                response = requests.Response()
                response.status_code = 400
                response._content = (
                    b'{"message": "Cannot add attachment: file too large"}'
                )
                error = requests.exceptions.HTTPError(
                    "400 Client Error: Bad Request for url: https://x/y",
                    response=response,
                )
                raise error

        client = HTTPErrorClient()
        upload_diagram_attachments(
            client, "999", [("diagram-1.svg", b"<svg/>", "image/svg+xml")]
        )
        out = capsys.readouterr().out
        assert "diagram-1.svg" in out
        assert "Cannot add attachment: file too large" in out

    def test_one_failure_does_not_block_the_remaining_uploads(self):
        class PartiallyFailingClient(FakeConfluenceClient):
            def upload_attachment(
                self, page_id, filename, content, media_type="image/svg+xml"
            ):
                if filename == "diagram-1.svg":
                    raise RuntimeError("boom")
                return super().upload_attachment(page_id, filename, content, media_type)

        client = PartiallyFailingClient()
        upload_diagram_attachments(
            client,
            "999",
            [
                ("diagram-1.svg", b"<svg>a</svg>", "image/svg+xml"),
                ("diagram-2.svg", b"<svg>b</svg>", "image/svg+xml"),
            ],
        )
        assert [a[1] for a in client.uploaded_attachments] == ["diagram-2.svg"]
