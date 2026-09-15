# requests.HTTPError's default str() is just "400 Client Error: Bad
# Request for url: ..." -- it never surfaces WHY the API rejected the
# request. Jira and Confluence both put the actual reason in the response
# body (Jira: {"errorMessages": [...], "errors": {"field": "reason"}};
# Confluence: a "message" field or similar) -- the one thing anyone
# debugging a failure actually needs, and every raise_for_status() call
# in jira_client.py/confluence_client.py silently discarded it.
#
# Reported live: a user's Jira Epic creation kept failing with a bare
# "HTTP 400" -- across three separate reports, neither the user nor the
# AI agent driving the CLI on their behalf could say more than the status
# code, because the real reason (a Jira-instance-specific required custom
# field) was sitting in the response body the whole time, never shown.
from __future__ import annotations

import requests


def raise_for_status_with_body(r: requests.Response) -> None:
    """Like r.raise_for_status(), but folds the response body into the
    exception message.

    Preserves the original exception's `.response` (and chains via
    `from e`), so callers that branch on status code -- e.g.
    ConfluenceClient.upsert_page()'s 409-conflict retry -- keep working
    unchanged."""
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        raise requests.HTTPError(
            f"{e} -- response body: {r.text}", response=e.response
        ) from e
