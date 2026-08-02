# Real-socket tests for sdd/commands/dashboard.py's _Handler (do_GET/do_POST).
# Spins up the actual ThreadingHTTPServer on an ephemeral localhost port and
# drives it with real HTTP requests, complementing test_dashboard.py (which
# calls the helper functions directly without a live server).
import json
import threading
from http.client import HTTPConnection
from pathlib import Path

import pytest

import sdd.commands.dashboard as dashboard_mod
from sdd.commands.dashboard import _Handler
from http.server import ThreadingHTTPServer


def _scaffold_feature(root: Path, feature: str = "payments", doc: str = "brd") -> None:
    feature_dir = root / ".specify" / "features" / feature
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / f"{doc}.md").write_text(f"# {doc.upper()}\n> Status: Draft | Date: 2026-07-09\n")


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd, tmp_path
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _get(port, path):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    resp = conn.getresponse()
    body = resp.read()
    conn.close()
    return resp.status, resp.getheader("Content-Type"), body


def _post(port, path, payload):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    body = json.dumps(payload).encode("utf-8")
    conn.request("POST", path, body=body, headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    resp_body = resp.read()
    conn.close()
    return resp.status, resp_body


def test_get_index_serves_html(server):
    httpd, _ = server
    status, content_type, body = _get(httpd.server_address[1], "/")
    assert status == 200
    assert content_type.startswith("text/html")
    assert b"SDD Dashboard" in body


def test_get_api_status_returns_json(server):
    httpd, _ = server
    status, content_type, body = _get(httpd.server_address[1], "/api/status")
    assert status == 200
    assert content_type == "application/json"
    data = json.loads(body)
    assert "project" in data


def test_get_api_status_returns_json_error_instead_of_crashing_on_exception(server, monkeypatch):
    """Regression: a real user's dashboard died with a bare connection
    reset (raw traceback in the server log, frontend stuck on stale data)
    when a malformed docs/jira/{feature}/keys.yml caused build_project_status
    to raise. /api/status must degrade to a JSON error response instead."""
    import sdd.commands.dashboard as dashboard_mod

    def _boom(root):
        raise AttributeError("'str' object has no attribute 'get'")

    monkeypatch.setattr(dashboard_mod, "build_project_status", _boom)
    httpd, _ = server
    status, content_type, body = _get(httpd.server_address[1], "/api/status")
    assert status == 500
    assert content_type == "application/json"
    data = json.loads(body)
    assert "AttributeError" in data["error"]


def test_get_api_doc_valid_feature_returns_content(server):
    httpd, tmp_path = server
    _scaffold_feature(tmp_path)
    status, _, body = _get(httpd.server_address[1], "/api/doc?feature=payments&doc=brd")
    assert status == 200
    data = json.loads(body)
    assert "content" in data


def test_get_api_doc_missing_doc_returns_404(server):
    httpd, _ = server
    status, _, body = _get(httpd.server_address[1], "/api/doc?feature=payments&doc=brd")
    assert status == 404


def test_get_api_doc_rejects_path_traversal(server):
    httpd, _ = server
    status, _, body = _get(httpd.server_address[1], "/api/doc?feature=..%2F..%2Fetc&doc=passwd")
    assert status == 400
    assert json.loads(body)["error"]


def test_get_api_review_links_rejects_invalid_feature(server):
    httpd, _ = server
    status, _, body = _get(httpd.server_address[1], "/api/review-links?feature=..%2Fescape")
    assert status == 400


def test_get_unknown_path_returns_404(server):
    httpd, _ = server
    status, _, _ = _get(httpd.server_address[1], "/nope")
    assert status == 404


def test_post_api_approve_valid_returns_200(server):
    httpd, tmp_path = server
    _scaffold_feature(tmp_path)
    status, body = _post(httpd.server_address[1], "/api/approve",
                          {"feature": "payments", "doc": "brd", "by": "Jane", "note": "lgtm"})
    assert status == 200
    data = json.loads(body)
    assert data["local_approval"] is True


def test_post_api_approve_rejects_invalid_feature(server):
    httpd, _ = server
    status, body = _post(httpd.server_address[1], "/api/approve",
                          {"feature": "../escape", "doc": "brd", "by": "Jane", "note": ""})
    assert status == 400
    assert json.loads(body)["error"]


def test_post_api_comment_valid_returns_200(server):
    httpd, tmp_path = server
    _scaffold_feature(tmp_path)
    status, body = _post(httpd.server_address[1], "/api/comment",
                          {"feature": "payments", "doc": "brd", "by": "Jane", "text": "please clarify"})
    assert status == 200
    data = json.loads(body)
    assert "error" not in data


def test_post_invalid_json_body_returns_400(server):
    httpd, _ = server
    conn = HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
    conn.request("POST", "/api/approve", body=b"not json",
                 headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    body = resp.read()
    conn.close()
    assert resp.status == 400
    assert json.loads(body)["error"]


def test_post_unknown_path_returns_404(server):
    httpd, _ = server
    status, _ = _post(httpd.server_address[1], "/api/nope",
                       {"feature": "payments", "doc": "brd"})
    assert status == 404


# --- Non-loopback access control (session token, Origin check, read-only) --

def _post_with_headers(port, path, payload, headers=None):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    body = json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    req_headers.update(headers or {})
    conn.request("POST", path, body=body, headers=req_headers)
    resp = conn.getresponse()
    resp_body = resp.read()
    conn.close()
    return resp.status, resp_body


@pytest.fixture
def access_override():
    """Temporarily overrides the module-level _ACCESS dict (set for real by
    dashboard_command() before serve_forever() -- these tests bypass that
    and drive _Handler directly, same as the `server` fixture above) and
    restores the original (safe/local) values afterward, so this doesn't
    leak into other tests in this file that assume the default local-open
    behavior."""
    original = dict(dashboard_mod._ACCESS)
    yield dashboard_mod._ACCESS
    dashboard_mod._ACCESS.clear()
    dashboard_mod._ACCESS.update(original)


def test_default_access_is_local_and_open(server):
    """Sanity check on the fixture-default state every other test in this
    file relies on -- if this ever fails, every other test's "unaffected by
    the access-control change" assumption is void."""
    assert dashboard_mod._ACCESS["is_local"] is True
    assert dashboard_mod._ACCESS["writes_enabled"] is True
    httpd, _ = server
    status, _content_type, body = _get(httpd.server_address[1], "/api/dashboard-info")
    assert status == 200
    data = json.loads(body)
    assert data == {"is_local": True, "writes_enabled": True}


def test_dashboard_info_reflects_read_only_non_local_state(server, access_override):
    access_override.update(is_local=False, writes_enabled=False, token=None, allowed_origins=set())
    httpd, _ = server
    status, _content_type, body = _get(httpd.server_address[1], "/api/dashboard-info")
    assert status == 200
    assert json.loads(body) == {"is_local": False, "writes_enabled": False}


def test_post_rejected_when_read_only(server, access_override):
    access_override.update(is_local=False, writes_enabled=False, token=None, allowed_origins=set())
    httpd, tmp_path = server
    _scaffold_feature(tmp_path)
    status, body = _post(httpd.server_address[1], "/api/approve",
                          {"feature": "payments", "doc": "brd", "by": "Jane", "note": ""})
    assert status == 403
    assert "read-only" in json.loads(body)["error"].lower()


def test_post_rejected_without_token_when_writes_enabled_non_local(server, access_override):
    httpd, tmp_path = server
    _scaffold_feature(tmp_path)
    port = httpd.server_address[1]
    access_override.update(
        is_local=False, writes_enabled=True, token="secret-token-value",
        allowed_origins={f"http://127.0.0.1:{port}"},
    )
    status, body = _post(port, "/api/approve",
                          {"feature": "payments", "doc": "brd", "by": "Jane", "note": ""})
    assert status == 403
    assert "token" in json.loads(body)["error"].lower()


def test_post_succeeds_with_correct_token_when_writes_enabled_non_local(server, access_override):
    httpd, tmp_path = server
    _scaffold_feature(tmp_path)
    port = httpd.server_address[1]
    access_override.update(
        is_local=False, writes_enabled=True, token="secret-token-value",
        allowed_origins={f"http://127.0.0.1:{port}"},
    )
    status, body = _post_with_headers(
        port, "/api/approve", {"feature": "payments", "doc": "brd", "by": "Jane", "note": ""},
        headers={"X-SDD-Token": "secret-token-value"},
    )
    assert status == 200
    assert "error" not in json.loads(body)


def test_post_rejected_on_origin_mismatch_even_with_correct_token(server, access_override):
    httpd, tmp_path = server
    _scaffold_feature(tmp_path)
    port = httpd.server_address[1]
    access_override.update(
        is_local=False, writes_enabled=True, token="secret-token-value",
        allowed_origins={f"http://127.0.0.1:{port}"},
    )
    status, body = _post_with_headers(
        port, "/api/approve", {"feature": "payments", "doc": "brd", "by": "Jane", "note": ""},
        headers={"X-SDD-Token": "secret-token-value", "Origin": "http://evil.example.com"},
    )
    assert status == 403
    assert "origin" in json.loads(body)["error"].lower()


def test_post_allowed_with_matching_origin_and_token(server, access_override):
    httpd, tmp_path = server
    _scaffold_feature(tmp_path)
    port = httpd.server_address[1]
    access_override.update(
        is_local=False, writes_enabled=True, token="secret-token-value",
        allowed_origins={f"http://127.0.0.1:{port}"},
    )
    status, body = _post_with_headers(
        port, "/api/approve", {"feature": "payments", "doc": "brd", "by": "Jane", "note": ""},
        headers={"X-SDD-Token": "secret-token-value", "Origin": f"http://127.0.0.1:{port}"},
    )
    assert status == 200
    assert "error" not in json.loads(body)


# --- Concurrent-write race (the _WRITE_LOCK fix) ---------------------------

def test_concurrent_comments_all_persist(server):
    """Before the write lock, near-simultaneous POST /api/comment requests
    could race on _COMMENTS_FILE's read-modify-write and silently drop one.
    Fires N concurrent comment submissions and asserts all N land -- flaky
    without the lock, reliable with it."""
    httpd, tmp_path = server
    _scaffold_feature(tmp_path)
    port = httpd.server_address[1]
    n = 12
    results = [None] * n

    def submit(i):
        status, body = _post(port, "/api/comment",
                              {"feature": "payments", "doc": "brd", "by": f"user{i}", "text": f"comment {i}"})
        results[i] = (status, body)

    threads = [threading.Thread(target=submit, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert all(r is not None for r in results), "a thread never completed"
    assert all(status == 200 for status, _ in results)

    comments_file = tmp_path / ".specify" / ".dashboard-comments.json"
    saved = json.loads(comments_file.read_text())
    assert len(saved["payments/brd"]) == n, (
        f"expected all {n} concurrent comments to persist, got {len(saved['payments/brd'])} "
        "-- a lost update means the write lock isn't working"
    )
