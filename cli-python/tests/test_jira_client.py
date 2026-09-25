# Unit tests for jira_client.py's JiraClient.search(). Regression coverage
# for the deprecated-endpoint bug: Atlassian retired GET /rest/api/3/search
# (returns 410 Gone) in favor of POST /rest/api/3/search/jql, discovered
# via a real "sdd review submit" failure during pre-publish testing.
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from sdd.utils.jira_client import JiraClient


def _client_with_mock_session(json_body: dict) -> tuple[JiraClient, MagicMock]:
    session = MagicMock()
    response = MagicMock()
    response.json.return_value = json_body
    response.raise_for_status.return_value = None
    session.post.return_value = response
    client = JiraClient(session, "https://example.atlassian.net")
    return client, session


class TestDeployment:
    """Confirmed against a real Jira Data Center instance: it doesn't
    support REST API v3 at all (v3 is Cloud-only -- JRASERVER-70688, an
    open Atlassian feature request for v3 on Data Center, confirms this).
    Every request built with the hardcoded v3 path this client used
    before `deployment` existed failed against Server/DC, sometimes as a
    200-with-HTML-login-page rather than a clean error."""

    def test_default_deployment_is_cloud_uses_v3(self):
        client = JiraClient(MagicMock(), "https://x.atlassian.net")
        assert client._api("/myself") == "https://x.atlassian.net/rest/api/3/myself"

    def test_explicit_cloud_deployment_uses_v3(self):
        client = JiraClient(MagicMock(), "https://x.atlassian.net", deployment="cloud")
        assert client._api("/myself") == "https://x.atlassian.net/rest/api/3/myself"

    def test_server_deployment_uses_v2_not_v3(self):
        client = JiraClient(MagicMock(), "https://jira.internal", deployment="server")
        assert client._api("/myself") == "https://jira.internal/rest/api/2/myself"


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


class TestSearchServerDeployment:
    """Regression: /search/jql is Cloud-only -- Server/Data Center never
    got it (its classic /rest/api/2/search endpoint was never deprecated).
    Before this fix, search() always posted to .../search/jql regardless
    of deployment, so every idempotency lookup (--level epic/story/task/chg)
    404'd against a real Server/DC instance. Reported live: a user's
    `sdd jira push --level epic` failed with HTTP 404."""

    def test_server_deployment_posts_to_plain_search_not_search_jql(self):
        session = MagicMock()
        response = MagicMock()
        response.json.return_value = {"issues": []}
        response.raise_for_status.return_value = None
        session.post.return_value = response
        client = JiraClient(session, "https://jira.internal", deployment="server")
        client.search("project = MYPROJ")
        url = session.post.call_args.args[0]
        assert url == "https://jira.internal/rest/api/2/search"

    def test_cloud_deployment_still_posts_to_search_jql(self):
        client, session = _client_with_mock_session({"issues": []})
        client.search("project = MYPROJ")
        url = session.post.call_args.args[0]
        assert url == "https://example.atlassian.net/rest/api/3/search/jql"


class TestFindByLabel:
    def test_builds_jql_with_project_and_label(self):
        client, session = _client_with_mock_session({"issues": []})
        client.find_by_label("MYPROJ", "sdd-feature:auth")
        body = session.post.call_args.kwargs["json"]
        assert 'project = "MYPROJ"' in body["jql"]
        assert 'labels = "sdd-feature:auth"' in body["jql"]

    def test_returns_first_match_or_none(self):
        client, _session = _client_with_mock_session(
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


class TestCreateIssue:
    def test_posts_to_issue_endpoint(self):
        client, session = _client_with_mock_session({"key": "PROJ-1"})
        client.create_issue({"summary": "Title", "project": {"key": "PROJ"}})
        url = session.post.call_args.args[0]
        assert url == "https://example.atlassian.net/rest/api/3/issue"

    def test_fields_wrapped_under_fields_key_not_sent_flat(self):
        """Jira's create-issue contract requires the whole payload nested
        under a top-level "fields" key -- sending the field dict flat is a
        real, easy-to-make mistake that silently produces a 400."""
        client, session = _client_with_mock_session({"key": "PROJ-1"})
        fields = {"summary": "Title", "project": {"key": "PROJ"}}
        client.create_issue(fields)
        body = session.post.call_args.kwargs["json"]
        assert body == {"fields": fields}

    def test_returns_the_created_issue(self):
        client, _ = _client_with_mock_session({"key": "PROJ-1", "id": "10001"})
        result = client.create_issue({"summary": "Title"})
        assert result == {"key": "PROJ-1", "id": "10001"}

    def test_400_error_surfaces_jira_validation_body(self):
        """Regression: reported live as a user's Jira Epic bootstrap
        failing 'HTTP 400' with no further detail visible anywhere --
        create_issue() must let the actual validation reason (e.g. a
        required custom field) reach the caller, not just the status
        code."""
        client, session = _client_with_mock_session({})
        response = session.post.return_value
        response.text = (
            '{"errorMessages":[],"errors":'
            '{"customfield_10011":"Epic Name is required."}}'
        )
        response.raise_for_status.side_effect = requests.HTTPError(
            "400 Client Error", response=response
        )
        with pytest.raises(requests.HTTPError) as excinfo:
            client.create_issue({"summary": "Title"})
        assert "Epic Name is required" in str(excinfo.value)


def _client_with_mock_put(
    json_body: dict | None = None,
) -> tuple[JiraClient, MagicMock]:
    session = MagicMock()
    response = MagicMock()
    response.json.return_value = json_body or {}
    response.raise_for_status.return_value = None
    session.put.return_value = response
    client = JiraClient(session, "https://example.atlassian.net")
    return client, session


class TestUpdateIssue:
    def test_puts_to_issue_key_endpoint(self):
        client, session = _client_with_mock_put()
        client.update_issue("PROJ-1", {"summary": "New title"})
        url = session.put.call_args.args[0]
        assert url == "https://example.atlassian.net/rest/api/3/issue/PROJ-1"

    def test_fields_wrapped_under_fields_key(self):
        client, session = _client_with_mock_put()
        client.update_issue("PROJ-1", {"summary": "New title"})
        body = session.put.call_args.kwargs["json"]
        assert body == {"fields": {"summary": "New title"}}


class TestSetParent:
    """set_parent() has two genuinely different payload shapes depending
    on parent_field -- easy to get backwards, since only one of the two
    branches is exercised by any given real Jira project's configuration
    (company-managed projects use the "parent" field; some team-managed/
    classic setups use a custom Epic Link field name instead)."""

    def test_default_parent_field_sends_nested_key_object(self):
        client, session = _client_with_mock_put()
        client.set_parent("PROJ-2", "PROJ-1")
        body = session.put.call_args.kwargs["json"]
        assert body == {"fields": {"parent": {"key": "PROJ-1"}}}

    def test_custom_parent_field_sends_the_key_flat(self):
        client, session = _client_with_mock_put()
        client.set_parent("PROJ-2", "PROJ-1", parent_field="customfield_10014")
        body = session.put.call_args.kwargs["json"]
        assert body == {"fields": {"customfield_10014": "PROJ-1"}}


class TestAddComment:
    def test_posts_to_issue_comment_endpoint(self):
        client, session = _client_with_mock_session({"id": "1"})
        client.add_comment("PROJ-1", "hello")
        url = session.post.call_args.args[0]
        assert url == "https://example.atlassian.net/rest/api/3/issue/PROJ-1/comment"

    def test_body_uses_atlassian_document_format(self):
        """A malformed ADF body is rejected by Jira Cloud with a 400 that
        gives little clue what's wrong -- this pins the exact envelope
        shape the API requires."""
        client, session = _client_with_mock_session({"id": "1"})
        client.add_comment("PROJ-1", "hello world")
        body = session.post.call_args.kwargs["json"]
        assert body == {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "hello world"}],
                    }
                ],
            }
        }

    def test_returns_the_created_comment(self):
        client, _ = _client_with_mock_session({"id": "1", "body": "hello"})
        result = client.add_comment("PROJ-1", "hello")
        assert result == {"id": "1", "body": "hello"}

    def test_server_deployment_sends_plain_string_body_not_adf(self):
        """Regression: ADF is Cloud-only -- Server/Data Center has no ADF
        support at all and rejects the same envelope as a field-type
        mismatch. Every comment this CLI posted against a Server/DC
        instance (review status updates, PR-created notifications) was
        broken until this was caught."""
        client, session = _client_with_mock_session({"id": "1"})
        client.deployment = "server"
        client.add_comment("PROJ-1", "hello world")
        body = session.post.call_args.kwargs["json"]
        assert body == {"body": "hello world"}


def _client_with_mock_get(json_body: dict) -> tuple[JiraClient, MagicMock]:
    session = MagicMock()
    response = MagicMock()
    response.json.return_value = json_body
    response.raise_for_status.return_value = None
    session.get.return_value = response
    client = JiraClient(session, "https://example.atlassian.net")
    return client, session


class TestGetMyself:
    def test_gets_myself_endpoint(self):
        client, session = _client_with_mock_get({"displayName": "Ada"})
        client.get_myself()
        url = session.get.call_args.args[0]
        assert url == "https://example.atlassian.net/rest/api/3/myself"

    def test_returns_the_response_body(self):
        client, _ = _client_with_mock_get({"displayName": "Ada", "accountId": "abc"})
        assert client.get_myself() == {"displayName": "Ada", "accountId": "abc"}


class TestGetFields:
    def test_gets_field_endpoint(self):
        client, session = _client_with_mock_get([])
        client.get_fields()
        url = session.get.call_args.args[0]
        assert url == "https://example.atlassian.net/rest/api/3/field"

    def test_returns_the_field_list_directly_not_wrapped(self):
        """Unlike most list endpoints here, /field returns a bare JSON
        array, not an envelope with a named key -- easy to accidentally
        add a ["fields"] unwrap that would break this one."""
        fields = [{"id": "customfield_10014", "name": "Epic Link"}]
        client, _ = _client_with_mock_get(fields)
        assert client.get_fields() == fields


class TestGetIssueTypes:
    def test_gets_project_statuses_endpoint(self):
        client, session = _client_with_mock_get([])
        client.get_issue_types("PROJ")
        url = session.get.call_args.args[0]
        assert url == "https://example.atlassian.net/rest/api/3/project/PROJ/statuses"

    def test_returns_the_response_directly_not_wrapped(self):
        statuses = [{"name": "Story", "statuses": []}]
        client, _ = _client_with_mock_get(statuses)
        assert client.get_issue_types("PROJ") == statuses


class TestGetComments:
    def test_gets_issue_comment_endpoint(self):
        client, session = _client_with_mock_get({"comments": []})
        client.get_comments("PROJ-1")
        url = session.get.call_args.args[0]
        assert url == "https://example.atlassian.net/rest/api/3/issue/PROJ-1/comment"

    def test_returns_comments_list_from_response(self):
        comments = [{"id": "1", "body": "hi"}]
        client, _ = _client_with_mock_get({"comments": comments})
        assert client.get_comments("PROJ-1") == comments

    def test_missing_comments_key_returns_empty_list(self):
        client, _ = _client_with_mock_get({})
        assert client.get_comments("PROJ-1") == []


class TestGetTransitions:
    def test_gets_transitions_endpoint(self):
        client, session = _client_with_mock_get({"transitions": []})
        client.get_transitions("PROJ-1")
        url = session.get.call_args.args[0]
        assert (
            url == "https://example.atlassian.net/rest/api/3/issue/PROJ-1/transitions"
        )

    def test_returns_transitions_list(self):
        transitions = [{"id": "21", "to": {"name": "In Review"}}]
        client, _ = _client_with_mock_get({"transitions": transitions})
        assert client.get_transitions("PROJ-1") == transitions

    def test_missing_transitions_key_returns_empty_list(self):
        client, _ = _client_with_mock_get({})
        assert client.get_transitions("PROJ-1") == []


class TestTransitionIssue:
    """transition_issue() -- the reopen/re-review nudge sdd review apply
    uses (opt-in via integrations.yml's reopen_status) when a document
    changes after its Jira review ticket was already moved to Done/Closed."""

    def _client_with_transitions(self, transitions: list[dict]):
        session = MagicMock()
        get_response = MagicMock()
        get_response.json.return_value = {"transitions": transitions}
        get_response.raise_for_status.return_value = None
        session.get.return_value = get_response
        post_response = MagicMock()
        post_response.raise_for_status.return_value = None
        session.post.return_value = post_response
        client = JiraClient(session, "https://example.atlassian.net")
        return client, session

    def test_executes_matching_transition(self):
        client, session = self._client_with_transitions(
            [{"id": "21", "to": {"name": "In Review"}}]
        )
        result = client.transition_issue("PROJ-1", "In Review")
        assert result is True
        url = session.post.call_args.args[0]
        assert (
            url == "https://example.atlassian.net/rest/api/3/issue/PROJ-1/transitions"
        )
        body = session.post.call_args.kwargs["json"]
        assert body == {"transition": {"id": "21"}}

    def test_match_is_case_insensitive(self):
        client, _session = self._client_with_transitions(
            [{"id": "21", "to": {"name": "in review"}}]
        )
        assert client.transition_issue("PROJ-1", "In Review") is True

    def test_no_matching_transition_returns_false_without_posting(self):
        """A ticket already in the target status (Jira offers no self-
        transition) or a workflow with no path to it from the current
        state -- both must be silent no-ops, never an error."""
        client, session = self._client_with_transitions(
            [{"id": "31", "to": {"name": "Done"}}]
        )
        result = client.transition_issue("PROJ-1", "In Review")
        assert result is False
        session.post.assert_not_called()

    def test_empty_transitions_list_returns_false(self):
        client, session = self._client_with_transitions([])
        assert client.transition_issue("PROJ-1", "In Review") is False
        session.post.assert_not_called()


class TestAssigneeField:
    """Regression coverage for a bug where every assignee call site
    hardcoded {"accountId": ...} regardless of deployment. accountId is
    a Cloud-only construct (introduced with Atlassian's GDPR changes);
    Server/Data Center identifies users by `name` instead. Sending
    accountId to Data Center doesn't error -- the create call can come
    back 2xx with the issue simply left unassigned -- which is how this
    went unnoticed until a real Data Center push was checked."""

    def test_server_deployment_uses_name(self):
        client = JiraClient(
            MagicMock(), "https://jira.example.net", deployment="server"
        )
        assert client.assignee_field("JIRAUSER10100") == {"name": "JIRAUSER10100"}

    def test_cloud_deployment_uses_account_id(self):
        client = JiraClient(MagicMock(), "https://x.atlassian.net", deployment="cloud")
        assert client.assignee_field("5c7b8a2d0f3e1a4b9d6c8f21") == {
            "accountId": "5c7b8a2d0f3e1a4b9d6c8f21"
        }

    def test_default_deployment_is_cloud(self):
        client = JiraClient(MagicMock(), "https://x.atlassian.net")
        assert client.assignee_field("someuser") == {"accountId": "someuser"}


def _mock_response(*, status_code: int, json_body, raises: bool = False):
    """A MagicMock standing in for a requests.Response, wired the way
    create_issue()'s retry logic actually reads a response: .status_code
    for the retry gate, .json() for _assignee_creation_error(), and
    .raise_for_status()/.text for raise_for_status_with_body()."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_body
    response.text = str(json_body)
    if raises:
        response.raise_for_status.side_effect = requests.HTTPError(
            f"{status_code} Client Error", response=response
        )
    else:
        response.raise_for_status.return_value = None
    return response


class TestCreateIssueAssigneeFallback:
    """Reported live: reviewer_jira_user in integrations.yml is hand-
    typed with nothing to validate it against at config time. Jira's
    create-issue endpoint validates the whole fields payload atomically
    -- before this fix, a typo'd username, a reviewer who left the org,
    or a Cloud/Server accountId-vs-name mismatch (see TestAssigneeField
    above) failed the ENTIRE review/CR ticket, over a field that has no
    bearing on whether the document itself is trackable. create_issue()
    now retries once without "assignee" when Jira's own error body
    blames that field specifically, and reports it via a
    "_assignee_dropped_reason" key on the returned dict rather than
    failing."""

    def test_assignee_rejected_retries_without_it_and_succeeds(self):
        session = MagicMock()
        first = _mock_response(
            status_code=400,
            json_body={
                "errorMessages": [],
                "errors": {"assignee": "User 'baduser' does not exist."},
            },
            raises=True,
        )
        second = _mock_response(status_code=201, json_body={"key": "PROJ-1"})
        session.post.side_effect = [first, second]
        client = JiraClient(session, "https://x.atlassian.net")

        result = client.create_issue(
            {"summary": "Title", "assignee": {"accountId": "baduser"}}
        )

        assert session.post.call_count == 2
        # The retry must not carry the field that got it rejected.
        retry_fields = session.post.call_args_list[1].kwargs["json"]["fields"]
        assert "assignee" not in retry_fields
        assert result["key"] == "PROJ-1"
        assert result["_assignee_dropped_reason"] == "User 'baduser' does not exist."

    def test_no_assignee_in_fields_never_retries(self):
        """The retry gate is `"assignee" in fields`, not just status_code
        == 400 -- an unrelated 400 (e.g. a missing required custom
        field) on a request that never had an assignee must not trigger
        a pointless second call."""
        session = MagicMock()
        session.post.return_value = _mock_response(
            status_code=400,
            json_body={"errors": {"customfield_10011": "Epic Name is required."}},
            raises=True,
        )
        client = JiraClient(session, "https://x.atlassian.net")

        with pytest.raises(requests.HTTPError):
            client.create_issue({"summary": "Title"})
        assert session.post.call_count == 1

    def test_non_assignee_400_error_does_not_retry(self):
        """assignee IS in fields, but Jira's error blames a different
        field -- retrying would just waste a call and still fail; the
        original error (naming the real problem) must surface as-is."""
        session = MagicMock()
        session.post.return_value = _mock_response(
            status_code=400,
            json_body={"errors": {"customfield_10011": "Epic Name is required."}},
            raises=True,
        )
        client = JiraClient(session, "https://x.atlassian.net")

        with pytest.raises(requests.HTTPError) as excinfo:
            client.create_issue(
                {"summary": "Title", "assignee": {"accountId": "someuser"}}
            )
        assert session.post.call_count == 1
        assert "Epic Name is required" in str(excinfo.value)

    def test_retry_also_fails_surfaces_the_retrys_own_error(self):
        """assignee wasn't the only problem: the retry (now without
        assignee) still fails, this time over a genuinely blocking
        field. That error -- not the original assignee complaint --
        must be what reaches the caller, since assignee is no longer
        part of the request they'd need to fix."""
        session = MagicMock()
        first = _mock_response(
            status_code=400,
            json_body={"errors": {"assignee": "User 'baduser' does not exist."}},
            raises=True,
        )
        second = _mock_response(
            status_code=400,
            json_body={"errors": {"customfield_10011": "Epic Name is required."}},
            raises=True,
        )
        session.post.side_effect = [first, second]
        client = JiraClient(session, "https://x.atlassian.net")

        with pytest.raises(requests.HTTPError) as excinfo:
            client.create_issue(
                {"summary": "Title", "assignee": {"accountId": "baduser"}}
            )
        assert session.post.call_count == 2
        assert "Epic Name is required" in str(excinfo.value)

    def test_malformed_400_body_does_not_retry(self):
        """A reverse proxy in front of Jira can return HTML for a 400
        rather than Jira's own JSON error shape -- _assignee_creation_
        error() must treat that as no signal, not license to guess and
        retry regardless."""
        session = MagicMock()
        response = MagicMock()
        response.status_code = 400
        response.json.side_effect = ValueError("not JSON")
        response.text = "<html>Bad Request</html>"
        response.raise_for_status.side_effect = requests.HTTPError(
            "400 Client Error", response=response
        )
        session.post.return_value = response
        client = JiraClient(session, "https://x.atlassian.net")

        with pytest.raises(requests.HTTPError):
            client.create_issue(
                {"summary": "Title", "assignee": {"accountId": "someuser"}}
            )
        assert session.post.call_count == 1

    def test_normal_success_has_no_dropped_reason_key(self):
        """The common case -- nothing rejected, no retry -- must not
        grow a spurious "_assignee_dropped_reason" key that callers
        would then misread as a warning to print."""
        session = MagicMock()
        session.post.return_value = _mock_response(
            status_code=201, json_body={"key": "PROJ-9"}
        )
        client = JiraClient(session, "https://x.atlassian.net")

        result = client.create_issue(
            {"summary": "Title", "assignee": {"accountId": "gooduser"}}
        )

        assert session.post.call_count == 1
        assert result == {"key": "PROJ-9"}
        assert "_assignee_dropped_reason" not in result


class TestAssigneeCreationErrorParsing:
    """Direct coverage for _assignee_creation_error()'s body parsing,
    independent of create_issue()'s retry orchestration above."""

    def _response(self, json_body):
        response = MagicMock()
        response.json.return_value = json_body
        return response

    def test_extracts_the_assignee_specific_message(self):
        from sdd.utils.jira_client import _assignee_creation_error

        response = self._response(
            {"errorMessages": [], "errors": {"assignee": "User 'x' does not exist."}}
        )
        assert _assignee_creation_error(response) == "User 'x' does not exist."

    def test_none_when_errors_has_no_assignee_key(self):
        from sdd.utils.jira_client import _assignee_creation_error

        response = self._response({"errors": {"customfield_10011": "required"}})
        assert _assignee_creation_error(response) is None

    def test_none_when_errors_key_missing_entirely(self):
        from sdd.utils.jira_client import _assignee_creation_error

        response = self._response({"errorMessages": ["Something else broke"]})
        assert _assignee_creation_error(response) is None

    def test_none_when_errors_is_not_a_dict(self):
        from sdd.utils.jira_client import _assignee_creation_error

        response = self._response({"errors": "not a dict"})
        assert _assignee_creation_error(response) is None

    def test_none_when_body_is_not_a_dict(self):
        from sdd.utils.jira_client import _assignee_creation_error

        response = self._response(["not", "a", "dict"])
        assert _assignee_creation_error(response) is None

    def test_none_when_assignee_value_is_not_a_string(self):
        """Defensive: Jira's documented shape is field -> string reason,
        but don't crash (or wrongly signal a fallback) on a value that
        isn't one."""
        from sdd.utils.jira_client import _assignee_creation_error

        response = self._response({"errors": {"assignee": {"nested": "object"}}})
        assert _assignee_creation_error(response) is None

    def test_none_when_body_is_not_json(self):
        from sdd.utils.jira_client import _assignee_creation_error

        response = MagicMock()
        response.json.side_effect = ValueError("not JSON")
        assert _assignee_creation_error(response) is None
