# Real-socket tests for sdd/commands/dashboard.py's _Handler (do_GET/do_POST).
# Spins up the actual ThreadingHTTPServer on an ephemeral localhost port and
# drives it with real HTTP requests, complementing test_dashboard.py (which
# calls the helper functions directly without a live server).
import json
import threading
from http.client import HTTPConnection
from pathlib import Path

import pytest

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
