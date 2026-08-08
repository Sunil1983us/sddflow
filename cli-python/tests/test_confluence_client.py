# Unit tests for confluence_client.py's upload_attachment() -- the
# local-svg diagram-rendering mode's page-attachment upload call.
# Run from repo root: pytest cli-python/tests -q
from __future__ import annotations

from unittest.mock import MagicMock

from sdd.utils.confluence_client import ConfluenceClient


class TestUploadAttachment:
    def _client(self, existing_results=None):
        """existing_results simulates get_attachment_by_filename()'s
        lookup -- [] (default) means "no attachment with this name yet",
        matching the common first-push case every pre-existing test in
        this file exercises. Pass e.g. [{"id": "att1"}] to simulate a
        second push that must UPDATE the existing attachment instead."""
        session = MagicMock()
        get_response = MagicMock()
        get_response.json.return_value = {"results": existing_results or []}
        session.get.return_value = get_response
        post_response = MagicMock()
        post_response.json.return_value = {"id": "att1"}
        session.post.return_value = post_response
        client = ConfluenceClient(session, "https://x.atlassian.net")
        return client, session, post_response

    def test_posts_to_the_page_attachment_endpoint(self):
        client, session, _ = self._client()
        client.upload_attachment("12345", "diagram-1.svg", b"<svg/>", "image/svg+xml")
        args, _kwargs = session.post.call_args
        assert args[0].endswith("/content/12345/child/attachment")

    def test_sends_the_xsrf_bypass_header(self):
        """Confluence's XSRF protection rejects multipart uploads
        without this header -- a real, documented gotcha, not
        optional."""
        client, session, _ = self._client()
        client.upload_attachment("12345", "diagram-1.svg", b"<svg/>", "image/svg+xml")
        _, kwargs = session.post.call_args
        assert kwargs["headers"]["X-Atlassian-Token"] == "nocheck"

    def test_unsets_content_type_so_requests_computes_the_multipart_boundary(self):
        """Regression: build_session() sets a blanket "application/json"
        Content-Type on the shared session for every other call this
        client makes. A per-request headers dict merges over that
        session default rather than replacing it, so without explicitly
        clearing it here, requests never computes and sets its own
        multipart/form-data; boundary=... header -- Confluence then
        receives multipart bytes labeled application/json and rejects
        the upload with 415, while the page content itself still saves
        fine (a broken-image placeholder, no error surfaced anywhere).
        Passing Content-Type: None is requests' documented way to
        remove a session-level header for one request."""
        client, session, _ = self._client()
        client.upload_attachment("12345", "diagram-1.svg", b"<svg/>", "image/svg+xml")
        _, kwargs = session.post.call_args
        assert kwargs["headers"]["Content-Type"] is None

    def test_sends_filename_content_and_media_type_as_multipart_file(self):
        client, session, _ = self._client()
        client.upload_attachment(
            "12345", "diagram-1.svg", b"<svg>data</svg>", "image/svg+xml"
        )
        _, kwargs = session.post.call_args
        assert kwargs["files"] == {
            "file": ("diagram-1.svg", b"<svg>data</svg>", "image/svg+xml")
        }

    def test_raises_on_http_error(self):
        client, _session, response = self._client()
        response.raise_for_status.side_effect = RuntimeError("500 Server Error")
        try:
            client.upload_attachment(
                "12345", "diagram-1.svg", b"<svg/>", "image/svg+xml"
            )
            assert False, "expected an exception"
        except RuntimeError:
            pass

    def test_default_media_type_is_svg(self):
        """media_type defaults to image/svg+xml since that's the only
        format local-svg mode currently produces."""
        client, session, _ = self._client()
        client.upload_attachment("12345", "diagram-1.svg", b"<svg/>")
        _, kwargs = session.post.call_args
        assert kwargs["files"]["file"][2] == "image/svg+xml"


class TestGetAttachmentByFilename:
    def _client(self, results):
        session = MagicMock()
        response = MagicMock()
        response.json.return_value = {"results": results}
        session.get.return_value = response
        client = ConfluenceClient(session, "https://x.atlassian.net")
        return client, session

    def test_returns_none_when_no_attachment_exists(self):
        client, _session = self._client([])
        assert client.get_attachment_by_filename("12345", "diagram-1.svg") is None

    def test_returns_the_first_match_when_found(self):
        client, _session = self._client([{"id": "att42", "title": "diagram-1.svg"}])
        result = client.get_attachment_by_filename("12345", "diagram-1.svg")
        assert result == {"id": "att42", "title": "diagram-1.svg"}

    def test_queries_by_filename(self):
        client, session = self._client([])
        client.get_attachment_by_filename("12345", "diagram-1.svg")
        args, kwargs = session.get.call_args
        assert args[0].endswith("/content/12345/child/attachment")
        assert kwargs["params"] == {"filename": "diagram-1.svg"}


class TestUploadAttachmentUpdatesExisting:
    """Regression coverage for a real, 100%-reproducible user-reported
    bug: re-pushing a local-svg diagram page a second time always failed
    with 'BadRequestException: Cannot add a new attachment with same
    file name as an existing attachment' -- upload_attachment() always
    POSTed to the CREATE endpoint, which Confluence Cloud rejects
    outright when an attachment with that filename already exists.
    Updating an existing attachment's content is a different endpoint
    entirely (POST .../child/attachment/{attachmentId}/data), which
    needs the attachment's ID -- hence the lookup-first fix."""

    def _client(self, existing_results):
        session = MagicMock()
        get_response = MagicMock()
        get_response.json.return_value = {"results": existing_results}
        session.get.return_value = get_response
        post_response = MagicMock()
        post_response.json.return_value = {"id": "att1"}
        session.post.return_value = post_response
        client = ConfluenceClient(session, "https://x.atlassian.net")
        return client, session

    def test_no_existing_attachment_uses_the_create_endpoint(self):
        client, session = self._client([])
        client.upload_attachment("12345", "diagram-1.svg", b"<svg/>", "image/svg+xml")
        args, _kwargs = session.post.call_args
        assert args[0].endswith("/content/12345/child/attachment")
        assert "/data" not in args[0]

    def test_existing_attachment_uses_the_update_data_endpoint_not_create(self):
        """The exact bug: this must NOT hit the plain create endpoint a
        second time -- that's precisely what 400s on Confluence Cloud."""
        client, session = self._client([{"id": "att42"}])
        client.upload_attachment("12345", "diagram-1.svg", b"<svg/>", "image/svg+xml")
        args, _kwargs = session.post.call_args
        assert args[0].endswith("/content/12345/child/attachment/att42/data")

    def test_update_path_still_sends_the_same_multipart_file_and_headers(self):
        """The fix must not regress the two gotchas the create path
        already had to handle (XSRF header, Content-Type override)."""
        client, session = self._client([{"id": "att42"}])
        client.upload_attachment(
            "12345", "diagram-1.svg", b"<svg>data</svg>", "image/svg+xml"
        )
        _, kwargs = session.post.call_args
        assert kwargs["headers"]["X-Atlassian-Token"] == "nocheck"
        assert kwargs["headers"]["Content-Type"] is None
        assert kwargs["files"] == {
            "file": ("diagram-1.svg", b"<svg>data</svg>", "image/svg+xml")
        }

    def test_lookup_uses_the_filename_being_uploaded(self):
        client, session = self._client([])
        client.upload_attachment("12345", "diagram-2.svg", b"<svg/>", "image/svg+xml")
        _, kwargs = session.get.call_args
        assert kwargs["params"] == {"filename": "diagram-2.svg"}
