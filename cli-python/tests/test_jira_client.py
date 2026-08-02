# Unit tests for jira_client.py's JiraClient.search(). Regression coverage
# for the deprecated-endpoint bug: Atlassian retired GET /rest/api/3/search
# (returns 410 Gone) in favor of POST /rest/api/3/search/jql, discovered
# via a real "sdd review submit" failure during pre-publish testing.
from __future__ import annotations
from unittest.mock import MagicMock

from sdd.utils.jira_client import JiraClient


def _client_with_mock_session(json_body: dict) -> tuple[JiraClient, MagicMock]:
    session = MagicMock()
    response = MagicMock()
    response.json.return_value = json_body
    response.raise_for_status.return_value = None
    session.post.return_value = response
    client = JiraClient(session, "https://example.atlassian.net")
    return client, session


class TestSearch:
    def test_posts_to_search_jql_not_deprecated_search(self):
        client, session = _client_with_mock_session({"issues": []})
        client.search("project = MYPROJ")
        session.post.assert_called_once()
        url = session.post.call_args.args[0]
        assert url == "https://example.atlassian.net/rest/api/3/search/jql"

    def test_never_calls_get(self):
        """Regression: the old code used session.get(...) against the
        endpoint Atlassian removed. Must not fall back to GET either."""
        client, session = _client_with_mock_session({"issues": []})
        client.search("project = MYPROJ")
        session.get.assert_not_called()

    def test_jql_and_max_results_sent_in_json_body(self):
        client, session = _client_with_mock_session({"issues": []})
        client.search("project = MYPROJ", max_results=25)
        body = session.post.call_args.kwargs["json"]
        assert body["jql"] == "project = MYPROJ"
        assert body["maxResults"] == 25

    def test_fields_sent_as_list_not_comma_string(self):
        """Regression: the old GET-based code joined fields into a comma
        string for a query param; the new JSON body expects a real list."""
        client, session = _client_with_mock_session({"issues": []})
        client.search("project = MYPROJ", fields=["summary", "status"])
        body = session.post.call_args.kwargs["json"]
        assert body["fields"] == ["summary", "status"]

    def test_fields_omitted_when_not_provided(self):
        client, session = _client_with_mock_session({"issues": []})
        client.search("project = MYPROJ")
        body = session.post.call_args.kwargs["json"]
        assert "fields" not in body

    def test_returns_issues_list_from_response(self):
        client, _ = _client_with_mock_session({"issues": [{"key": "PROJ-1"}]})
        result = client.search("project = MYPROJ")
        assert result == [{"key": "PROJ-1"}]

    def test_missing_issues_key_returns_empty_list(self):
        client, _ = _client_with_mock_session({})
        assert client.search("project = MYPROJ") == []


class TestFindByLabel:
    def test_builds_jql_with_project_and_label(self):
        client, session = _client_with_mock_session({"issues": []})
        client.find_by_label("MYPROJ", "sdd-feature:auth")
        body = session.post.call_args.kwargs["json"]
        assert 'project = "MYPROJ"' in body["jql"]
        assert 'labels = "sdd-feature:auth"' in body["jql"]

    def test_returns_first_match_or_none(self):
        client, session = _client_with_mock_session(
            {"issues": [{"key": "PROJ-1"}, {"key": "PROJ-2"}]}
        )
        assert client.find_by_label("MYPROJ", "sdd-feature:auth") == {"key": "PROJ-1"}

        client2, _ = _client_with_mock_session({"issues": []})
        assert client2.find_by_label("MYPROJ", "sdd-feature:auth") is None


class TestLinkIssues:
    """link_issues() -- the cross-project fallback used when a true
    parent-child link (set_parent) fails, most commonly because the two
    issues live in different Jira projects (a Jira platform limitation
    that parent/Epic-Link cannot work around; plain issue links can)."""

    def test_posts_to_issue_link_endpoint(self):
        client, session = _client_with_mock_session({})
        client.link_issues("TEMPT-2", "TEMP-1")
        url = session.post.call_args.args[0]
        assert url == "https://example.atlassian.net/rest/api/3/issueLink"

    def test_default_link_type_is_relates(self):
        client, session = _client_with_mock_session({})
        client.link_issues("TEMPT-2", "TEMP-1")
        body = session.post.call_args.kwargs["json"]
        assert body["type"] == {"name": "Relates"}
        assert body["inwardIssue"] == {"key": "TEMPT-2"}
        assert body["outwardIssue"] == {"key": "TEMP-1"}

    def test_custom_link_type_honored(self):
        client, session = _client_with_mock_session({})
        client.link_issues("TEMPT-2", "TEMP-1", link_type="Blocks")
        body = session.post.call_args.kwargs["json"]
        assert body["type"] == {"name": "Blocks"}

    def test_raises_on_http_error(self):
        client, session = _client_with_mock_session({})
        session.post.return_value.raise_for_status.side_effect = Exception(
            "400 Bad Request"
        )
        try:
            client.link_issues("TEMPT-2", "TEMP-1")
            assert False, "expected an exception"
        except Exception as e:
            assert "400" in str(e)
