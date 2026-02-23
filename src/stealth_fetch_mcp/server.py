from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlparse

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
from stealth_fetch_mcp.parser import (
    _clean_html,
    extract_links,
    extract_metadata,
    extract_tables,
    parse_feed,
    parse_robots_txt,
)

DEFAULT_TEXT_MAX_CHARS = 50_000
DEFAULT_JSON_MAX_CHARS = 100_000
DEFAULT_LINKS_MAX_CHARS = 100_000
READONLY_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
HttpVersionLiteral = Literal["v1", "v2", "v2tls", "v2_prior_knowledge", "v3", "v3only"]
CurlOptionValue = str | int | float | bool


def _truncate(value: str, max_chars: int) -> str:
    if max_chars <= 0:
        return "[truncated at 0 chars]"
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars].rstrip()}\n[truncated at {max_chars} chars]"


class _ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class _BaseInputModel(_ConfigModel):
    @field_validator("url", check_fields=False)
    @classmethod
    def _validate_http_url(cls, value: str) -> str:
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return value


class CurlOptionInput(_ConfigModel):
    option: str | int = Field(
        ...,
        description="Curl option key (e.g. TIMEOUT_MS, CurlOpt.TIMEOUT_MS, or numeric id).",
    )
    value: CurlOptionValue = Field(..., description="Curl option value.")


class ExtraFingerprintInput(_ConfigModel):
    tls_min_version: int | None = Field(
        default=None,
        description="TLS min version (e.g. 771 for TLSv1.2, 772 for TLSv1.3).",
    )
    tls_grease: bool | None = Field(default=None, description="Enable TLS GREASE extension.")
    tls_permute_extensions: bool | None = Field(
        default=None,
        description="Permute TLS extension order in ClientHello.",
    )
    tls_cert_compression: Literal["zlib", "brotli"] | None = Field(
        default=None,
        description="TLS certificate compression preference.",
    )
    tls_signature_algorithms: list[str] | None = Field(
        default=None,
        description="TLS signature algorithms list.",
    )
    tls_delegated_credential: str | None = Field(
        default=None,
        description="TLS delegated credential signature algorithms string.",
    )
    tls_record_size_limit: int | None = Field(
        default=None,
        description="TLS record size limit extension value.",
    )
    http2_stream_weight: int | None = Field(
        default=None,
        description="HTTP/2 stream weight fingerprint value.",
    )
    http2_stream_exclusive: int | None = Field(
        default=None,
        description="HTTP/2 stream exclusive fingerprint value.",
    )
    http2_no_priority: bool | None = Field(
        default=None,
        description="Disable HTTP/2 priority signals in fingerprint.",
    )


class SessionOptionsInput(_ConfigModel):
    headers: dict[str, str] | None = Field(default=None, description="Default session headers.")
    cookies: dict[str, str] | None = Field(default=None, description="Default session cookies.")
    auth: tuple[str, str] | None = Field(default=None, description="HTTP basic auth tuple.")
    proxies: dict[str, str] | None = Field(
        default=None,
        description="Proxy map for schemes/hosts (e.g. {'https': 'http://proxy:8080'}).",
    )
    proxy: str | None = Field(default=None, description="Single proxy URL for all requests.")
    proxy_auth: tuple[str, str] | None = Field(
        default=None,
        description="Proxy auth tuple (username, password).",
    )
    base_url: str | None = Field(
        default=None,
        description="Absolute base URL for relative request paths.",
    )
    params: dict[str, Any] | list[tuple[str, Any]] | None = Field(
        default=None,
        description="Default query params for all requests in this session.",
    )
    verify: bool | str | None = Field(
        default=None,
        description="TLS verification (bool) or CA bundle path.",
    )
    timeout: float | tuple[float, float] | None = Field(
        default=None,
        description="Session timeout seconds or (connect, read).",
    )
    trust_env: bool | None = Field(
        default=None,
        description="Use proxy/cert settings from environment variables.",
    )
    allow_redirects: bool | None = Field(default=None, description="Default redirect behavior.")
    max_redirects: int | None = Field(
        default=None,
        ge=-1,
        le=1_000,
        description="Maximum redirects (-1 for unlimited).",
    )
    impersonate: BrowserTypeLiteral | None = Field(
        default=None,
        description="Default browser fingerprint profile.",
    )
    ja3: str | None = Field(default=None, description="Custom JA3 TLS fingerprint string.")
    akamai: str | None = Field(default=None, description="Custom Akamai HTTP/2 fingerprint.")
    extra_fp: ExtraFingerprintInput | None = Field(
        default=None,
        description="Additional fingerprint overrides applied with impersonation/JA3/Akamai.",
    )
    default_headers: bool | None = Field(
        default=None,
        description="Enable curl_cffi browser default headers.",
    )
    default_encoding: str | None = Field(
        default=None,
        description="Default response text encoding fallback.",
    )
    curl_options: list[CurlOptionInput] | None = Field(
        default=None,
        description="Low-level libcurl option overrides.",
    )
    http_version: HttpVersionLiteral | None = Field(
        default=None,
        description="HTTP version strategy.",
    )
    debug: bool | None = Field(default=None, description="Enable curl debug logs.")
    interface: str | None = Field(
        default=None,
        description="Bind socket to a specific interface or source IP.",
    )
    cert: str | tuple[str, str] | None = Field(
        default=None,
        description="Client cert path or (cert_path, key_path) tuple.",
    )
    discard_cookies: bool | None = Field(
        default=None,
        description="Do not persist response cookies into session jar.",
    )
    raise_for_status: bool | None = Field(
        default=None,
        description="Raise HTTP error exceptions for 4xx/5xx responses.",
    )
    max_clients: int | None = Field(
        default=None,
        gt=0,
        le=1_000,
        description="AsyncSession connection pool size.",
    )


class RequestOptionsInput(_ConfigModel):
    params: dict[str, Any] | list[tuple[str, Any]] | None = Field(
        default=None,
        description="Per-request query params.",
    )
    data: dict[str, str] | list[tuple[str, str]] | str | None = Field(
        default=None,
        description="Request body for form/text payloads.",
    )
    json_body: dict[str, Any] | list[Any] | None = Field(
        default=None,
        alias="json",
        serialization_alias="json",
        validation_alias="json",
        description="Request JSON body payload.",
    )
    headers: dict[str, str] | None = Field(default=None, description="Per-request headers.")
    cookies: dict[str, str] | None = Field(default=None, description="Per-request cookies.")
    auth: tuple[str, str] | None = Field(default=None, description="HTTP basic auth tuple.")
    timeout: float | tuple[float, float] | None = Field(
        default=None,
        description="Request timeout seconds or (connect, read).",
    )
    allow_redirects: bool | None = Field(default=None, description="Per-request redirect behavior.")
    max_redirects: int | None = Field(
        default=None,
        ge=-1,
        le=1_000,
        description="Maximum redirects (-1 for unlimited).",
    )
    proxies: dict[str, str] | None = Field(default=None, description="Proxy map.")
    proxy: str | None = Field(default=None, description="Single proxy URL.")
    proxy_auth: tuple[str, str] | None = Field(default=None, description="Proxy auth tuple.")
    verify: bool | str | None = Field(
        default=None,
        description="TLS verification (bool) or CA bundle path.",
    )
    referer: str | None = Field(default=None, description="Referer header shortcut.")
    accept_encoding: str | None = Field(default=None, description="Accept-Encoding header value.")
    impersonate: BrowserTypeLiteral | None = Field(
        default=None,
        description="Browser fingerprint profile for this request.",
    )
    ja3: str | None = Field(default=None, description="Custom JA3 TLS fingerprint.")
    akamai: str | None = Field(default=None, description="Custom Akamai HTTP/2 fingerprint.")
    extra_fp: ExtraFingerprintInput | None = Field(
        default=None,
        description="Additional fingerprint overrides.",
    )
    default_headers: bool | None = Field(
        default=None,
        description="Enable/disable browser default headers.",
    )
    default_encoding: str | None = Field(
        default=None,
        description="Default response text encoding fallback.",
    )
    quote: str | Literal[False] | None = Field(
        default=None,
        description="URL quoting behavior; False keeps URL as-is.",
    )
    http_version: HttpVersionLiteral | None = Field(
        default=None,
        description="HTTP version strategy.",
    )
    interface: str | None = Field(
        default=None,
        description="Bind socket to specific interface/source IP.",
    )
    cert: str | tuple[str, str] | None = Field(
        default=None,
        description="Client cert path or (cert_path, key_path).",
    )
    stream: bool | None = Field(
        default=None,
        description="Streaming responses are not supported by this MCP tool output path.",
    )
    max_recv_speed: int | None = Field(
        default=None,
        ge=0,
        description="Maximum receive speed in bytes/second.",
    )
    discard_cookies: bool | None = Field(
        default=None,
        description="Do not store response cookies from this request.",
    )
    curl_options: list[CurlOptionInput] | None = Field(
        default=None,
        description="Low-level libcurl option overrides.",
    )

    @field_validator("stream")
    @classmethod
    def _validate_stream_setting(cls, value: bool | None) -> bool | None:
        if value:
            raise ValueError("stream=True is not supported by this MCP server output mode.")
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
    session_options: SessionOptionsInput | None = Field(
        default=None,
        description="Optional AsyncSession-level curl_cffi options.",
    )
    request_options: RequestOptionsInput | None = Field(
        default=None,
        description="Optional per-request curl_cffi options.",
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
    session_options: SessionOptionsInput | None = Field(
        default=None,
        description="Optional AsyncSession-level curl_cffi options.",
    )
    request_options: RequestOptionsInput | None = Field(
        default=None,
        description="Optional per-request curl_cffi options.",
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
    session_options: SessionOptionsInput | None = Field(
        default=None,
        description="Optional AsyncSession-level curl_cffi options.",
    )
    request_options: RequestOptionsInput | None = Field(
        default=None,
        description="Optional per-request curl_cffi options.",
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
    session_options: SessionOptionsInput | None = Field(
        default=None,
        description="Optional AsyncSession-level curl_cffi options.",
    )
    request_options: RequestOptionsInput | None = Field(
        default=None,
        description="Optional per-request curl_cffi options.",
    )
    max_chars: int = Field(
        default=DEFAULT_LINKS_MAX_CHARS,
        description="Maximum number of characters to return.",
        gt=0,
        le=1_000_000,
    )


class StealthFetchHeadersInput(_BaseInputModel):
    url: str = Field(..., description="Target URL to inspect.")
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
    session_options: SessionOptionsInput | None = Field(
        default=None,
        description="Optional AsyncSession-level curl_cffi options.",
    )
    request_options: RequestOptionsInput | None = Field(
        default=None,
        description="Optional per-request curl_cffi options.",
    )


class StealthExtractMetadataInput(_BaseInputModel):
    url: str = Field(..., description="Target URL to fetch.")
    impersonate: BrowserTypeLiteral = Field(
        default=DEFAULT_IMPERSONATE,
        description="Browser fingerprint target for curl_cffi impersonation.",
    )
    session_options: SessionOptionsInput | None = Field(
        default=None,
        description="Optional AsyncSession-level curl_cffi options.",
    )
    request_options: RequestOptionsInput | None = Field(
        default=None,
        description="Optional per-request curl_cffi options.",
    )
    max_chars: int = Field(
        default=DEFAULT_JSON_MAX_CHARS,
        description="Maximum number of characters to return.",
        gt=0,
        le=1_000_000,
    )


class StealthExtractTablesInput(_BaseInputModel):
    url: str = Field(..., description="Target URL to fetch.")
    impersonate: BrowserTypeLiteral = Field(
        default=DEFAULT_IMPERSONATE,
        description="Browser fingerprint target for curl_cffi impersonation.",
    )
    selector: str | None = Field(
        default=None,
        description="Optional CSS selector to scope table search within a sub-element.",
    )
    session_options: SessionOptionsInput | None = Field(
        default=None,
        description="Optional AsyncSession-level curl_cffi options.",
    )
    request_options: RequestOptionsInput | None = Field(
        default=None,
        description="Optional per-request curl_cffi options.",
    )
    max_chars: int = Field(
        default=DEFAULT_JSON_MAX_CHARS,
        description="Maximum number of characters to return.",
        gt=0,
        le=1_000_000,
    )


class StealthFetchRobotsInput(_BaseInputModel):
    url: str = Field(
        ...,
        description=(
            "Any URL on the target site. The scheme and host are used to derive "
            "the robots.txt URL (e.g. https://example.com/page → "
            "https://example.com/robots.txt)."
        ),
    )
    impersonate: BrowserTypeLiteral = Field(
        default=DEFAULT_IMPERSONATE,
        description="Browser fingerprint target for curl_cffi impersonation.",
    )
    session_options: SessionOptionsInput | None = Field(
        default=None,
        description="Optional AsyncSession-level curl_cffi options.",
    )
    request_options: RequestOptionsInput | None = Field(
        default=None,
        description="Optional per-request curl_cffi options.",
    )


class StealthFetchFeedInput(_BaseInputModel):
    url: str = Field(..., description="Target RSS 2.0 or Atom feed URL.")
    impersonate: BrowserTypeLiteral = Field(
        default=DEFAULT_IMPERSONATE,
        description="Browser fingerprint target for curl_cffi impersonation.",
    )
    max_items: int = Field(
        default=50,
        description="Maximum number of feed items to return.",
        gt=0,
        le=500,
    )
    session_options: SessionOptionsInput | None = Field(
        default=None,
        description="Optional AsyncSession-level curl_cffi options.",
    )
    request_options: RequestOptionsInput | None = Field(
        default=None,
        description="Optional per-request curl_cffi options.",
    )
    max_chars: int = Field(
        default=DEFAULT_JSON_MAX_CHARS,
        description="Maximum number of characters to return.",
        gt=0,
        le=1_000_000,
    )


class BulkUrlInput(_BaseInputModel):
    url: str = Field(..., description="Target URL to fetch.")


class StealthFetchBulkInput(_ConfigModel):
    urls: list[BulkUrlInput] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of URLs to fetch (1–50 entries).",
    )
    impersonate: BrowserTypeLiteral = Field(
        default=DEFAULT_IMPERSONATE,
        description="Browser fingerprint target applied to all requests.",
    )
    max_concurrency: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of concurrent requests.",
    )
    delay: float = Field(
        default=0.0,
        ge=0.0,
        le=60.0,
        description="Seconds to sleep after acquiring a semaphore slot before each request.",
    )
    timeout: float = Field(
        default=DEFAULT_TIMEOUT,
        gt=0,
        le=300,
        description="Per-request timeout in seconds.",
    )
    session_options: SessionOptionsInput | None = Field(
        default=None,
        description="Optional AsyncSession-level curl_cffi options.",
    )
    max_chars_per_url: int = Field(
        default=10_000,
        gt=0,
        le=100_000,
        description="Maximum characters of body text to return per URL.",
    )


def _options_to_dict(options: _ConfigModel | None) -> dict[str, Any]:
    if options is None:
        return {}
    data = options.model_dump(exclude_none=True, by_alias=True)
    curl_options = data.pop("curl_options", None)
    if curl_options:
        data["curl_options"] = {
            entry["option"]: entry["value"]
            for entry in curl_options
        }
    return data


def _merge_request_options(
    request_options: RequestOptionsInput | None,
    **overrides: Any,
) -> dict[str, Any] | None:
    merged = _options_to_dict(request_options)
    for key, value in overrides.items():
        if value is not None:
            merged[key] = value
    return merged or None


@asynccontextmanager
async def _session_scope(
    shared_session: AsyncSession,
    session_options: SessionOptionsInput | None,
) -> AsyncIterator[AsyncSession]:
    if session_options is None:
        yield shared_session
        return

    options = _options_to_dict(session_options)
    async with _create_session(session_options=options) as ephemeral_session:
        yield ephemeral_session


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
    request_options = _merge_request_options(
        params.request_options,
        headers=params.headers,
        impersonate=params.impersonate,
        timeout=params.timeout,
        allow_redirects=params.follow_redirects,
    )
    async with _session_scope(session, params.session_options) as active_session:
        result = await _fetch(
            session=active_session,
            url=params.url,
            method="GET",
            request_options=request_options,
            max_chars=params.max_chars,
        )
    return result.text


async def _stealth_fetch_text_impl(params: StealthFetchTextInput, session: AsyncSession) -> str:
    request_options = _merge_request_options(
        params.request_options,
        impersonate=params.impersonate,
    )
    async with _session_scope(session, params.session_options) as active_session:
        result = await _fetch(
            session=active_session,
            url=params.url,
            method="GET",
            request_options=request_options,
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

    request_options = _merge_request_options(
        params.request_options,
        headers=params.headers,
        impersonate=params.impersonate,
    )
    async with _session_scope(session, params.session_options) as active_session:
        result = await _fetch(
            session=active_session,
            url=params.url,
            method=params.method,
            body=parsed_body,
            request_options=request_options,
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
    request_options = _merge_request_options(
        params.request_options,
        impersonate=params.impersonate,
    )
    async with _session_scope(session, params.session_options) as active_session:
        result = await _fetch(
            session=active_session,
            url=params.url,
            method="GET",
            request_options=request_options,
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


async def _stealth_fetch_headers_impl(
    params: StealthFetchHeadersInput,
    session: AsyncSession,
) -> str:
    request_options = _merge_request_options(
        params.request_options,
        headers=params.headers,
        impersonate=params.impersonate,
        timeout=params.timeout,
        allow_redirects=params.follow_redirects,
    )
    async with _session_scope(session, params.session_options) as active_session:
        result = await _fetch(
            session=active_session,
            url=params.url,
            method="GET",
            request_options=request_options,
            max_chars=1,
        )
    return json.dumps(
        {"status_code": result.status_code, "final_url": result.final_url, "headers": result.headers},
        indent=2,
    )


async def _stealth_extract_metadata_impl(
    params: StealthExtractMetadataInput,
    session: AsyncSession,
) -> str:
    request_options = _merge_request_options(
        params.request_options,
        impersonate=params.impersonate,
    )
    async with _session_scope(session, params.session_options) as active_session:
        result = await _fetch(
            session=active_session,
            url=params.url,
            method="GET",
            request_options=request_options,
            max_chars=DEFAULT_MAX_CHARS,
        )
    return _truncate(extract_metadata(result.text), params.max_chars)


async def _stealth_extract_tables_impl(
    params: StealthExtractTablesInput,
    session: AsyncSession,
) -> str:
    request_options = _merge_request_options(
        params.request_options,
        impersonate=params.impersonate,
    )
    async with _session_scope(session, params.session_options) as active_session:
        result = await _fetch(
            session=active_session,
            url=params.url,
            method="GET",
            request_options=request_options,
            max_chars=DEFAULT_MAX_CHARS,
        )
    return _truncate(extract_tables(result.text, selector=params.selector), params.max_chars)


async def _stealth_fetch_robots_impl(
    params: StealthFetchRobotsInput,
    session: AsyncSession,
) -> str:
    parsed = urlparse(params.url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    request_options = _merge_request_options(
        params.request_options,
        impersonate=params.impersonate,
    )
    async with _session_scope(session, params.session_options) as active_session:
        result = await _fetch(
            session=active_session,
            url=robots_url,
            method="GET",
            request_options=request_options,
            max_chars=500_000,
        )
    robots_data: dict[str, Any] = parse_robots_txt(result.text)
    robots_data["url"] = robots_url
    return json.dumps(robots_data, indent=2)


async def _stealth_fetch_feed_impl(
    params: StealthFetchFeedInput,
    session: AsyncSession,
) -> str:
    request_options = _merge_request_options(
        params.request_options,
        impersonate=params.impersonate,
    )
    async with _session_scope(session, params.session_options) as active_session:
        result = await _fetch(
            session=active_session,
            url=params.url,
            method="GET",
            request_options=request_options,
            max_chars=DEFAULT_MAX_CHARS,
        )
    try:
        parsed = parse_feed(result.text, max_items=params.max_items)
    except ValueError as exc:
        raise FetchError(str(exc)) from exc
    return _truncate(parsed, params.max_chars)


async def _stealth_fetch_bulk_impl(
    params: StealthFetchBulkInput,
    session: AsyncSession,
) -> str:
    semaphore = asyncio.Semaphore(params.max_concurrency)

    async def _fetch_one(url: str) -> dict[str, Any]:
        async with semaphore:
            if params.delay > 0:
                await asyncio.sleep(params.delay)
            request_options = _merge_request_options(
                None,
                impersonate=params.impersonate,
                timeout=params.timeout,
            )
            try:
                result = await _fetch(
                    session=active_session,
                    url=url,
                    method="GET",
                    request_options=request_options,
                    max_chars=params.max_chars_per_url,
                )
                return {
                    "url": url,
                    "status": "ok",
                    "status_code": result.status_code,
                    "final_url": result.final_url,
                    "text": result.text,
                }
            except FetchError as exc:
                return {"url": url, "status": "error", "error": str(exc)}

    async with _session_scope(session, params.session_options) as active_session:
        results = await asyncio.gather(*[_fetch_one(entry.url) for entry in params.urls])
    return json.dumps(list(results), indent=2)


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


@mcp.tool(name="stealth_fetch_headers", annotations=READONLY_TOOL_ANNOTATIONS)
async def stealth_fetch_headers(
    params: StealthFetchHeadersInput,
    ctx: Context[ServerSession, AppContext],
) -> str:
    """Fetch a URL and return HTTP status code, final URL, and response headers as JSON.

    Useful for content-type detection, redirect inspection, cache analysis, and auth header
    verification without fetching the full response body.
    """
    return await _stealth_fetch_headers_impl(params, ctx.request_context.lifespan_context.session)


@mcp.tool(name="stealth_extract_metadata", annotations=READONLY_TOOL_ANNOTATIONS)
async def stealth_extract_metadata(
    params: StealthExtractMetadataInput,
    ctx: Context[ServerSession, AppContext],
) -> str:
    """Fetch a page and extract structured metadata as JSON.

    Returns JSON-LD script blocks, Open Graph (og:*) tags, Twitter Card (twitter:*) tags,
    and standard <meta> tags in a single structured object.
    """
    return await _stealth_extract_metadata_impl(
        params, ctx.request_context.lifespan_context.session
    )


@mcp.tool(name="stealth_extract_tables", annotations=READONLY_TOOL_ANNOTATIONS)
async def stealth_extract_tables(
    params: StealthExtractTablesInput,
    ctx: Context[ServerSession, AppContext],
) -> str:
    """Fetch a page and extract all HTML tables as a JSON list of {headers, rows} objects.

    Automatically detects header rows from <thead> or leading <th> elements. Handles large
    pages with many tables without needing a simplified URL. Useful for financial data,
    comparison tables, sports results, and pricing grids.
    """
    return await _stealth_extract_tables_impl(
        params, ctx.request_context.lifespan_context.session
    )


@mcp.tool(name="stealth_fetch_robots", annotations=READONLY_TOOL_ANNOTATIONS)
async def stealth_fetch_robots(
    params: StealthFetchRobotsInput,
    ctx: Context[ServerSession, AppContext],
) -> str:
    """Fetch and parse a site's robots.txt, returning structured Allow/Disallow/Sitemap data.

    Derives the robots.txt URL from the scheme and host of the provided URL. Returns fully
    parsed, structured JSON — no need to fetch robots.txt manually afterwards. Useful for
    planning respectful crawls and discovering sitemap locations.
    """
    return await _stealth_fetch_robots_impl(params, ctx.request_context.lifespan_context.session)


@mcp.tool(name="stealth_fetch_feed", annotations=READONLY_TOOL_ANNOTATIONS)
async def stealth_fetch_feed(
    params: StealthFetchFeedInput,
    ctx: Context[ServerSession, AppContext],
) -> str:
    """Fetch and parse an RSS 2.0 or Atom feed, returning items as structured JSON.

    Follows redirects automatically — pass any feed URL and redirect resolution is handled.
    Returns feed title, feed link, and a list of items with title, link, published date,
    and summary. Useful for tracking changelogs, blog updates, and news feeds.
    """
    return await _stealth_fetch_feed_impl(params, ctx.request_context.lifespan_context.session)


@mcp.tool(name="stealth_fetch_bulk", annotations=READONLY_TOOL_ANNOTATIONS)
async def stealth_fetch_bulk(
    params: StealthFetchBulkInput,
    ctx: Context[ServerSession, AppContext],
) -> str:
    """Fetch multiple URLs concurrently and return per-URL results as a JSON list.

    Each result includes status ("ok" or "error"), status_code, final_url, and body text.
    Errors for individual URLs are isolated — one failure does not stop the others.
    """
    return await _stealth_fetch_bulk_impl(params, ctx.request_context.lifespan_context.session)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
