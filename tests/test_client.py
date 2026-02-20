from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from stealth_fetch_mcp.client import FetchError, _create_session, _fetch


class _TestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/html":
            body = "<html><body><h1>OK</h1></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/html")
            self.end_headers()
            self.wfile.write(b"redirect")
            return
        if self.path == "/error":
            body = "server exploded in test"
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return
        if self.path == "/slow":
            time.sleep(0.25)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"slow")
            return
        if self.path == "/large":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(("x" * 200).encode("utf-8"))
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/echo-json":
            length = int(self.headers.get("Content-Length", "0"))
            payload = self.rfile.read(length) if length else b"{}"
            body = json.dumps({"received": json.loads(payload.decode("utf-8"))})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return
        self.send_response(404)
        self.end_headers()


@pytest.fixture()
def test_server_url() -> str:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _TestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


@pytest.mark.asyncio
async def test_create_session_defaults() -> None:
    async with _create_session() as session:
        assert session.impersonate == "chrome"
        assert session.allow_redirects is True


@pytest.mark.asyncio
async def test_fetch_html_success(test_server_url: str) -> None:
    async with _create_session() as session:
        result = await _fetch(session, url=f"{test_server_url}/html")
    assert result.status_code == 200
    assert "<h1>OK</h1>" in result.text


@pytest.mark.asyncio
async def test_fetch_redirect_behavior(test_server_url: str) -> None:
    async with _create_session() as session:
        followed = await _fetch(
            session, url=f"{test_server_url}/redirect", follow_redirects=True
        )
        not_followed = await _fetch(
            session, url=f"{test_server_url}/redirect", follow_redirects=False
        )
    assert followed.status_code == 200
    assert followed.final_url.endswith("/html")
    assert not_followed.status_code == 302


@pytest.mark.asyncio
async def test_fetch_http_error_has_status_and_snippet(test_server_url: str) -> None:
    async with _create_session() as session:
        with pytest.raises(FetchError, match="HTTP 500"):
            await _fetch(session, url=f"{test_server_url}/error")


@pytest.mark.asyncio
async def test_fetch_timeout_actionable_message(test_server_url: str) -> None:
    async with _create_session() as session:
        with pytest.raises(FetchError, match="timed out"):
            await _fetch(session, url=f"{test_server_url}/slow", timeout=0.05)


@pytest.mark.asyncio
async def test_fetch_rejects_non_http_url() -> None:
    async with _create_session() as session:
        with pytest.raises(ValueError, match="Only http/https URLs are supported"):
            await _fetch(session, url="mailto:test@example.com")


@pytest.mark.asyncio
async def test_fetch_post_json_body(test_server_url: str) -> None:
    async with _create_session() as session:
        result = await _fetch(
            session,
            url=f"{test_server_url}/echo-json",
            method="POST",
            body={"hello": "world"},
            headers={"Content-Type": "application/json"},
        )
    assert '"hello": "world"' in result.text


@pytest.mark.asyncio
async def test_fetch_truncates_large_content(test_server_url: str) -> None:
    async with _create_session() as session:
        result = await _fetch(session, url=f"{test_server_url}/large", max_chars=20)
    assert result.text.endswith("[truncated at 20 chars]")
