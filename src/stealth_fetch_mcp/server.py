from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Literal

from curl_cffi.requests import AsyncSession
from curl_cffi.requests.impersonate import BrowserTypeLiteral
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field, field_validator

from stealth_fetch_mcp.client import (
    DEFAULT_IMPERSONATE,
    DEFAULT_MAX_CHARS,
    DEFAULT_TIMEOUT,
    FetchError,
    _create_session,
    _fetch,
)
from stealth_fetch_mcp.parser import _clean_html, extract_links

DEFAULT_TEXT_MAX_CHARS = 50_000
DEFAULT_JSON_MAX_CHARS = 100_000
DEFAULT_LINKS_MAX_CHARS = 100_000
READONLY_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


def _truncate(value: str, max_chars: int) -> str:
    if max_chars <= 0:
        return "[truncated at 0 chars]"
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars].rstrip()}\n[truncated at {max_chars} chars]"


class _BaseInputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("url", check_fields=False)
    @classmethod
    def _validate_http_url(cls, value: str) -> str:
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return value


class StealthFetchPageInput(_BaseInputModel):
    url: str = Field(..., description="Target URL to fetch.")
    impersonate: BrowserTypeLiteral = Field(
        default=DEFAULT_IMPERSONATE,
        description="Browser fingerprint target for curl_cffi impersonation.",
    )
    headers: dict[str, str] | None = Field(
        default=None,
        description="Optional request headers to include.",
    )
    timeout: float = Field(
        default=DEFAULT_TIMEOUT,
        description="Request timeout in seconds.",
        gt=0,
        le=300,
    )
    follow_redirects: bool = Field(
        default=True,
        description="Whether HTTP redirects should be followed.",
    )
    max_chars: int = Field(
        default=DEFAULT_MAX_CHARS,
        description="Maximum number of characters to return.",
        gt=0,
        le=1_000_000,
    )


class StealthFetchTextInput(_BaseInputModel):
    url: str = Field(..., description="Target URL to fetch.")
    impersonate: BrowserTypeLiteral = Field(
        default=DEFAULT_IMPERSONATE,
        description="Browser fingerprint target for curl_cffi impersonation.",
    )
    selector: str | None = Field(
        default=None,
        description="Optional CSS selector to scope readable text extraction.",
    )
    max_chars: int = Field(
        default=DEFAULT_TEXT_MAX_CHARS,
        description="Maximum number of characters to return.",
        gt=0,
        le=1_000_000,
    )


class StealthFetchJsonInput(_BaseInputModel):
    url: str = Field(..., description="Target JSON API URL.")
    impersonate: BrowserTypeLiteral = Field(
        default=DEFAULT_IMPERSONATE,
        description="Browser fingerprint target for curl_cffi impersonation.",
    )
    headers: dict[str, str] | None = Field(
        default=None,
        description="Optional request headers to include.",
    )
    method: Literal["GET", "POST"] = Field(
        default="GET",
        description="HTTP method for the request.",
    )
    body: str | None = Field(
        default=None,
        description="Optional JSON string body used when method is POST.",
    )
    max_chars: int = Field(
        default=DEFAULT_JSON_MAX_CHARS,
        description="Maximum number of characters to return.",
        gt=0,
        le=1_000_000,
    )


class StealthExtractLinksInput(_BaseInputModel):
    url: str = Field(..., description="Target URL to fetch.")
    impersonate: BrowserTypeLiteral = Field(
        default=DEFAULT_IMPERSONATE,
        description="Browser fingerprint target for curl_cffi impersonation.",
    )
    selector: str = Field(
        default="a[href]",
        description="CSS selector used to find link elements.",
        min_length=1,
    )
    pattern: str | None = Field(
        default=None,
        description="Optional regex filter applied to href values.",
    )
    max_results: int = Field(
        default=100,
        description="Maximum number of links to return.",
        gt=0,
        le=10_000,
    )
    max_chars: int = Field(
        default=DEFAULT_LINKS_MAX_CHARS,
        description="Maximum number of characters to return.",
        gt=0,
        le=1_000_000,
    )


@dataclass
class AppContext:
    session: AsyncSession


@asynccontextmanager
async def app_lifespan(_: FastMCP[AppContext]) -> AsyncIterator[AppContext]:
    session = _create_session()
    try:
        yield AppContext(session=session)
    finally:
        await session.close()


mcp = FastMCP("stealth_fetch_mcp", lifespan=app_lifespan)


async def _stealth_fetch_page_impl(params: StealthFetchPageInput, session: AsyncSession) -> str:
    result = await _fetch(
        session=session,
        url=params.url,
        method="GET",
        headers=params.headers,
        impersonate=params.impersonate,
        timeout=params.timeout,
        follow_redirects=params.follow_redirects,
        max_chars=params.max_chars,
    )
    return result.text


async def _stealth_fetch_text_impl(params: StealthFetchTextInput, session: AsyncSession) -> str:
    result = await _fetch(
        session=session,
        url=params.url,
        method="GET",
        impersonate=params.impersonate,
        max_chars=max(params.max_chars * 2, DEFAULT_MAX_CHARS),
    )
    return _clean_html(result.text, selector=params.selector, max_chars=params.max_chars)


async def _stealth_fetch_json_impl(params: StealthFetchJsonInput, session: AsyncSession) -> str:
    parsed_body: Any | None = None
    if params.method == "POST" and params.body:
        try:
            parsed_body = json.loads(params.body)
        except json.JSONDecodeError as exc:
            raise FetchError(f"Invalid JSON body for POST request: {exc}") from exc

    result = await _fetch(
        session=session,
        url=params.url,
        method=params.method,
        headers=params.headers,
        body=parsed_body,
        impersonate=params.impersonate,
        max_chars=max(params.max_chars * 2, DEFAULT_MAX_CHARS),
    )

    try:
        pretty = json.dumps(json.loads(result.text), indent=2)
    except json.JSONDecodeError:
        warning = "Warning: response was not valid JSON; returning raw content."
        pretty = f"{warning}\n{result.text}"
    return _truncate(pretty, params.max_chars)


async def _stealth_extract_links_impl(
    params: StealthExtractLinksInput,
    session: AsyncSession,
) -> str:
    result = await _fetch(
        session=session,
        url=params.url,
        method="GET",
        impersonate=params.impersonate,
        max_chars=DEFAULT_MAX_CHARS,
    )
    links_json = extract_links(
        html=result.text,
        base_url=params.url,
        selector=params.selector,
        pattern=params.pattern,
        max_results=params.max_results,
    )
    return _truncate(links_json, params.max_chars)


@mcp.tool(name="stealth_fetch_page", annotations=READONLY_TOOL_ANNOTATIONS)
async def stealth_fetch_page(
    params: StealthFetchPageInput,
    ctx: Context[ServerSession, AppContext],
) -> str:
    """Fetch a web page with browser TLS impersonation and return raw HTML.

    Uses curl_cffi with browser-grade TLS/HTTP fingerprinting to improve compatibility with
    sites that reject default Python HTTP client signatures.
    """

    return await _stealth_fetch_page_impl(params, ctx.request_context.lifespan_context.session)


@mcp.tool(name="stealth_fetch_text", annotations=READONLY_TOOL_ANNOTATIONS)
async def stealth_fetch_text(
    params: StealthFetchTextInput,
    ctx: Context[ServerSession, AppContext],
) -> str:
    """Fetch a page and return cleaned readability-style text content.

    Removes scripts/navigation chrome and preserves key structure such as headings, lists, and links.
    """

    return await _stealth_fetch_text_impl(params, ctx.request_context.lifespan_context.session)


@mcp.tool(name="stealth_fetch_json", annotations=READONLY_TOOL_ANNOTATIONS)
async def stealth_fetch_json(
    params: StealthFetchJsonInput,
    ctx: Context[ServerSession, AppContext],
) -> str:
    """Fetch a JSON API endpoint with browser impersonation and return pretty JSON text.

    Supports GET and POST requests, with optional JSON body parsing for POST operations.
    """

    return await _stealth_fetch_json_impl(params, ctx.request_context.lifespan_context.session)


@mcp.tool(name="stealth_extract_links", annotations=READONLY_TOOL_ANNOTATIONS)
async def stealth_extract_links(
    params: StealthExtractLinksInput,
    ctx: Context[ServerSession, AppContext],
) -> str:
    """Fetch a page and extract matching links as JSON.

    Returns link text, raw href, and resolved absolute URL values.
    """

    return await _stealth_extract_links_impl(params, ctx.request_context.lifespan_context.session)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
