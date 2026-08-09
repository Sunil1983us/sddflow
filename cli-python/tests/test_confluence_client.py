# Unit tests for confluence_client.py's upload_attachment() -- the
# local-svg diagram-rendering mode's page-attachment upload call.
# Run from repo root: pytest cli-python/tests -q
from __future__ import annotations

from unittest.mock import MagicMock

import requests

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


class TestUpsertPage409Retry:
    """upsert_page() -- reported by a user during real /plan-lld testing:
    a second push (review_submit's own "stamp the Jira status banner on"
    re-push, right after a burst of ~19 diagram-attachment uploads on the
    same page) got a 409 Conflict, and a manual retry hit the exact same
    409 again -- because a blind resend carries the same stale version
    number. The fix re-fetches the page's current version before
    retrying, which these tests verify directly."""

    def _conflict_response(self) -> MagicMock:
        response = MagicMock()
        response.status_code = 409
        return response

    def _get_response(self, page_id: str, version: int) -> MagicMock:
        r = MagicMock()
        r.json.return_value = {
            "results": [{"id": page_id, "version": {"number": version}}]
        }
        return r

    def _put_conflict(self) -> MagicMock:
        r = MagicMock()
        r.raise_for_status.side_effect = requests.HTTPError(
            response=self._conflict_response()
        )
        return r

    def _put_success(self, version: int) -> MagicMock:
        r = MagicMock()
        r.raise_for_status.return_value = None
        r.json.return_value = {"id": "999", "version": {"number": version}}
        return r

    def test_retries_with_refetched_version_after_409(self):
        session = MagicMock()
        # Initial read sees version 1; the re-fetch after the 409 sees
        # version 2 -- what actually moved server-side in between.
        session.get.side_effect = [
            self._get_response("999", 1),
            self._get_response("999", 2),
        ]
        # First PUT (stale version 1 -> tries to write 2) conflicts;
        # second PUT (re-fetched version 2 -> writes 3) succeeds.
        session.put.side_effect = [self._put_conflict(), self._put_success(3)]

        client = ConfluenceClient(session, "https://x.atlassian.net")
        page, created = client.upsert_page("ENG", "My Page", "<p>body</p>")

        assert created is False
        assert page["version"]["number"] == 3
        assert session.get.call_count == 2
        assert session.put.call_count == 2
        # The retried PUT must carry the RE-FETCHED version (2 + 1 = 3),
        # not a blind resend of the original stale one (1 + 1 = 2) --
        # that distinction is the entire fix.
        retried_body = session.put.call_args_list[1].kwargs["json"]
        assert retried_body["version"]["number"] == 3

    def test_exhausts_retries_and_raises_last_409(self):
        session = MagicMock()
        session.get.side_effect = [self._get_response("999", n) for n in (1, 2, 3, 4)]
        session.put.side_effect = [self._put_conflict() for _ in range(3)]

        client = ConfluenceClient(session, "https://x.atlassian.net")
        try:
            client.upsert_page("ENG", "My Page", "<p>body</p>")
            assert False, "expected an HTTPError"
        except requests.HTTPError as e:
            assert e.response.status_code == 409
        assert session.put.call_count == 3  # max_attempts, no more

    def test_non_409_error_is_not_retried(self):
        """A generic HTTP-layer retry already covers 429/5xx (see
        atlassian_auth.py); upsert_page's own retry loop must only ever
        special-case 409 -- anything else should raise immediately, not
        loop and re-fetch pointlessly."""
        session = MagicMock()
        session.get.return_value = self._get_response("999", 1)
        server_error_response = MagicMock()
        server_error_response.status_code = 500
        put_fail = MagicMock()
        put_fail.raise_for_status.side_effect = requests.HTTPError(
            response=server_error_response
        )
        session.put.return_value = put_fail

        client = ConfluenceClient(session, "https://x.atlassian.net")
        try:
            client.upsert_page("ENG", "My Page", "<p>body</p>")
            assert False, "expected an HTTPError"
        except requests.HTTPError as e:
            assert e.response.status_code == 500
        assert session.put.call_count == 1  # no retry loop for this

    def test_success_on_first_attempt_never_re_fetches(self):
        session = MagicMock()
        session.get.return_value = self._get_response("999", 1)
        session.put.return_value = self._put_success(2)

        client = ConfluenceClient(session, "https://x.atlassian.net")
        page, created = client.upsert_page("ENG", "My Page", "<p>body</p>")

        assert created is False
        assert page["version"]["number"] == 2
        assert session.get.call_count == 1
        assert session.put.call_count == 1
