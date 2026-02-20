from __future__ import annotations

import inspect
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from mcp.types import ToolAnnotations
from pydantic import ValidationError

from stealth_fetch_mcp.server import (
    StealthExtractLinksInput,
    StealthFetchJsonInput,
    StealthFetchPageInput,
    StealthFetchTextInput,
    _stealth_extract_links_impl,
    _stealth_fetch_json_impl,
    _stealth_fetch_page_impl,
    _stealth_fetch_text_impl,
    app_lifespan,
    main,
    mcp,
)


class _ServerHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/page":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><nav>menu</nav><h1>Server</h1><a href='/a'>A</a></body></html>"
            )
            return
        if self.path.startswith("/inspect"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            referer = self.headers.get("Referer", "")
            self.wfile.write(
                (
                    "<html><body>"
                    f"<p>path={self.path}</p>"
                    f"<p>referer={referer}</p>"
                    "</body></html>"
                ).encode("utf-8")
            )
            return
        if self.path == "/json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","items":[1,2,3]}')
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/json":
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return
        self.send_response(404)
        self.end_headers()


@pytest.fixture()
def http_url() -> str:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ServerHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


def test_input_models_validate_constraints() -> None:
    StealthFetchPageInput(url="https://example.com")
    StealthFetchTextInput(url="https://example.com", max_chars=100)
    StealthFetchJsonInput(url="https://example.com", method="GET")
    StealthExtractLinksInput(url="https://example.com", max_results=5)
    StealthFetchPageInput(
        url="https://example.com",
        session_options={"verify": False, "default_headers": False},
        request_options={
            "params": {"q": "x"},
            "referer": "https://example.com/from",
            "quote": False,
            "http_version": "v2",
        },
    )

    with pytest.raises(ValidationError):
        StealthFetchPageInput(url="ftp://example.com")
    with pytest.raises(ValidationError):
        StealthFetchTextInput(url="https://example.com", max_chars=0)
    with pytest.raises(ValidationError):
        StealthExtractLinksInput(url="https://example.com", max_results=0)
    with pytest.raises(ValidationError):
        StealthFetchPageInput(
            url="https://example.com",
            request_options={"stream": True},
        )


def test_tools_are_registered_with_expected_annotations() -> None:
    tools = {tool.name: tool for tool in mcp._tool_manager.list_tools()}
    assert set(tools) >= {
        "stealth_fetch_page",
        "stealth_fetch_text",
        "stealth_fetch_json",
        "stealth_extract_links",
    }

    for name in (
        "stealth_fetch_page",
        "stealth_fetch_text",
        "stealth_fetch_json",
        "stealth_extract_links",
    ):
        annotations = tools[name].annotations
        assert isinstance(annotations, ToolAnnotations)
        assert annotations.readOnlyHint is True
        assert annotations.openWorldHint is True
        assert annotations.idempotentHint is True
        assert annotations.destructiveHint is False


@pytest.mark.asyncio
async def test_lifespan_creates_and_closes_session() -> None:
    async with app_lifespan(mcp) as context:
        assert context.session is not None
        assert getattr(context.session, "_closed") is False
    assert getattr(context.session, "_closed") is True


@pytest.mark.asyncio
async def test_tool_impls_work_with_live_http_server(http_url: str) -> None:
    async with app_lifespan(mcp) as context:
        page = await _stealth_fetch_page_impl(
            StealthFetchPageInput(url=f"{http_url}/page"), context.session
        )
        text = await _stealth_fetch_text_impl(
            StealthFetchTextInput(url=f"{http_url}/page"), context.session
        )
        response_json = await _stealth_fetch_json_impl(
            StealthFetchJsonInput(url=f"{http_url}/json", method="GET"), context.session
        )
        links = await _stealth_extract_links_impl(
            StealthExtractLinksInput(url=f"{http_url}/page", max_results=5),
            context.session,
        )

    assert "<h1>Server</h1>" in page
    assert "# Server" in text
    assert '"status": "ok"' in response_json
    parsed_links = json.loads(links)
    assert parsed_links[0]["absolute_url"].endswith("/a")


@pytest.mark.asyncio
async def test_tool_impl_applies_request_options(http_url: str) -> None:
    async with app_lifespan(mcp) as context:
        page = await _stealth_fetch_page_impl(
            StealthFetchPageInput(
                url=f"{http_url}/inspect",
                request_options={
                    "params": {"q": "1"},
                    "referer": "https://example.com/from",
                    "default_headers": False,
                },
            ),
            context.session,
        )

    assert "path=/inspect?q=1" in page
    assert "referer=https://example.com/from" in page


def test_main_contains_stdio_run() -> None:
    source = inspect.getsource(main)
    assert "mcp.run(" in source
