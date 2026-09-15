# Unit tests for raise_for_status_with_body() -- the shared helper that
# folds a Jira/Confluence API's actual response body into the raised
# exception's message. requests.HTTPError's default str() is just "400
# Client Error: Bad Request for url: ..." and never shows WHY the API
# rejected the request; reported live, a user's Jira Epic creation kept
# failing "HTTP 400" with no one -- not the user, not the AI agent
# driving the CLI -- able to say more, because the real reason (a
# Jira-instance-specific required custom field) was sitting in the
# response body the whole time, never surfaced.
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from sdd.utils.http_errors import raise_for_status_with_body


def _response(status_code: int, text: str) -> MagicMock:
    r = MagicMock()
    r.text = text
    r.status_code = status_code
    r.raise_for_status.side_effect = requests.HTTPError(
        f"{status_code} Client Error: Bad Request for url: https://x/rest/api/2/issue",
        response=r,
    )
    return r


def test_success_response_does_not_raise():
    r = MagicMock()
    r.raise_for_status.return_value = None
    raise_for_status_with_body(r)  # must not raise


def test_error_message_includes_response_body():
    body = (
        '{"errorMessages":[],"errors":{"customfield_10011":"Epic Name is required."}}'
    )
    r = _response(400, body)
    with pytest.raises(requests.HTTPError) as excinfo:
        raise_for_status_with_body(r)
    assert body in str(excinfo.value)
    assert "400" in str(excinfo.value)


def test_preserves_response_for_status_code_branching():
    """Callers like ConfluenceClient.upsert_page() branch on
    e.response.status_code (its 409-conflict retry) -- the re-raised
    exception must keep pointing at the original response."""
    r = _response(409, '{"message":"version conflict"}')
    with pytest.raises(requests.HTTPError) as excinfo:
        raise_for_status_with_body(r)
    assert excinfo.value.response is r
    assert excinfo.value.response.status_code == 409


def test_chains_original_exception():
    r = _response(500, "internal error")
    with pytest.raises(requests.HTTPError) as excinfo:
        raise_for_status_with_body(r)
    assert excinfo.value.__cause__ is not None
    assert isinstance(excinfo.value.__cause__, requests.HTTPError)
