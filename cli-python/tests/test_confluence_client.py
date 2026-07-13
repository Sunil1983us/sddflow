# Unit tests for confluence_client.py's upload_attachment() -- the
# local-svg diagram-rendering mode's page-attachment upload call.
# Run from repo root: pytest cli-python/tests -q
from __future__ import annotations
from unittest.mock import MagicMock

from sdd.utils.confluence_client import ConfluenceClient


class TestUploadAttachment:
    def _client(self):
        session = MagicMock()
        response = MagicMock()
        response.json.return_value = {"results": [{"id": "att1"}]}
        session.post.return_value = response
        client = ConfluenceClient(session, "https://x.atlassian.net")
        return client, session, response

    def test_posts_to_the_page_attachment_endpoint(self):
        client, session, _ = self._client()
        client.upload_attachment("12345", "diagram-1.svg", b"<svg/>", "image/svg+xml")
        args, kwargs = session.post.call_args
        assert args[0].endswith("/content/12345/child/attachment")

    def test_sends_the_xsrf_bypass_header(self):
        """Confluence's XSRF protection rejects multipart uploads
        without this header -- a real, documented gotcha, not
        optional."""
        client, session, _ = self._client()
        client.upload_attachment("12345", "diagram-1.svg", b"<svg/>", "image/svg+xml")
        _, kwargs = session.post.call_args
        assert kwargs["headers"] == {"X-Atlassian-Token": "nocheck"}

    def test_sends_filename_content_and_media_type_as_multipart_file(self):
        client, session, _ = self._client()
        client.upload_attachment("12345", "diagram-1.svg", b"<svg>data</svg>", "image/svg+xml")
        _, kwargs = session.post.call_args
        assert kwargs["files"] == {
            "file": ("diagram-1.svg", b"<svg>data</svg>", "image/svg+xml")
        }

    def test_raises_on_http_error(self):
        client, session, response = self._client()
        response.raise_for_status.side_effect = RuntimeError("500 Server Error")
        try:
            client.upload_attachment("12345", "diagram-1.svg", b"<svg/>", "image/svg+xml")
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
