from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlparse

from curl_cffi.const import CurlOpt
from curl_cffi.requests import AsyncSession
from curl_cffi.requests import exceptions as curl_exceptions
from curl_cffi.requests.impersonate import BrowserTypeLiteral

RequestMethod = Literal["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "TRACE", "PATCH", "QUERY"]

DEFAULT_IMPERSONATE: BrowserTypeLiteral = "chrome"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_CHARS = 100_000


@dataclass(slots=True)
class FetchResult:
    status_code: int
    final_url: str
    text: str
    headers: dict[str, str]


class FetchError(RuntimeError):
    """Raised when a fetch request cannot produce a usable response."""


def _to_curl_option_key(option: str | int) -> CurlOpt:
    if isinstance(option, int):
        return CurlOpt(option)
    normalized = option.strip()
    if normalized.startswith("CurlOpt."):
        normalized = normalized.split(".", 1)[1]
    if normalized.lstrip("-").isdigit():
        return CurlOpt(int(normalized))
    try:
        return getattr(CurlOpt, normalized)
    except AttributeError as exc:
        raise ValueError(
            f"Unsupported curl option key: {option}. Use CurlOpt names (e.g., TIMEOUT_MS)."
        ) from exc


def _normalize_curl_options(
    options: dict[str | int, Any] | None,
) -> dict[CurlOpt, Any] | None:
    if options is None:
        return None
    normalized: dict[CurlOpt, Any] = {}
    for key, value in options.items():
        normalized[_to_curl_option_key(key)] = value
    return normalized


def _normalize_options(options: dict[str, Any] | None) -> dict[str, Any]:
    if not options:
        return {}
    normalized = {k: v for k, v in options.items() if v is not None}
    if "curl_options" in normalized:
        normalized["curl_options"] = _normalize_curl_options(normalized["curl_options"])
    return normalized


def _truncate(value: str, max_chars: int) -> str:
    if max_chars <= 0:
        return "[truncated at 0 chars]"
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars].rstrip()}\n[truncated at {max_chars} chars]"


def _create_session(
    impersonate: BrowserTypeLiteral = DEFAULT_IMPERSONATE,
    timeout: float = DEFAULT_TIMEOUT,
    follow_redirects: bool = True,
    session_options: dict[str, Any] | None = None,
) -> AsyncSession:
    options = _normalize_options(session_options)
    options.setdefault("impersonate", impersonate)
    options.setdefault("timeout", timeout)
    options.setdefault("allow_redirects", follow_redirects)
    options.setdefault("raise_for_status", False)
    return AsyncSession(**options)


def _handle_error(
    error: Exception,
    status_code: int | None = None,
    response_snippet: str | None = None,
) -> str:
    if status_code is not None and status_code >= 400:
        snippet = (response_snippet or "").strip()
        if snippet:
            return f"HTTP {status_code} error. Response snippet: {snippet}"
        return f"HTTP {status_code} error."
    if isinstance(error, curl_exceptions.Timeout):
        return "Request timed out. Try increasing the timeout value."
    if isinstance(error, (curl_exceptions.DNSError, curl_exceptions.ConnectionError)):
        return "DNS/connection failed. Check that the URL is correct and reachable."
    if isinstance(
        error,
        (
            curl_exceptions.SSLError,
            curl_exceptions.CertificateVerifyError,
            curl_exceptions.ImpersonateError,
        ),
    ):
        return "TLS/impersonation error. Try a different impersonate target or verify certificates."
    return f"Request failed: {type(error).__name__}: {error}"


async def _fetch(
    session: AsyncSession,
    url: str,
    *,
    method: RequestMethod = "GET",
    headers: dict[str, str] | None = None,
    body: Any | None = None,
    impersonate: BrowserTypeLiteral | None = None,
    timeout: float | None = None,
    follow_redirects: bool | None = None,
    request_options: dict[str, Any] | None = None,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> FetchResult:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http/https URLs are supported.")

    request_kwargs = _normalize_options(request_options)

    if headers is not None:
        request_kwargs["headers"] = headers
    if impersonate is not None:
        request_kwargs["impersonate"] = impersonate
    if timeout is not None:
        request_kwargs["timeout"] = timeout
    if follow_redirects is not None:
        request_kwargs["allow_redirects"] = follow_redirects

    if body is not None and "json" not in request_kwargs and "data" not in request_kwargs:
        if isinstance(body, (dict, list)):
            request_kwargs["json"] = body
        else:
            request_kwargs["data"] = body

    try:
        response = await session.request(method=method, url=url, **request_kwargs)
    except (TypeError, ValueError) as exc:
        raise FetchError(f"Invalid curl_cffi options: {exc}") from exc
    except curl_exceptions.RequestException as exc:
        raise FetchError(_handle_error(exc)) from exc

    text = response.text
    if response.status_code >= 400:
        snippet = _truncate(text, max_chars=300)
        raise FetchError(
            _handle_error(
                RuntimeError(f"HTTP {response.status_code}"),
                status_code=response.status_code,
                response_snippet=snippet,
            )
        )

    return FetchResult(
        status_code=response.status_code,
        final_url=str(response.url),
        text=_truncate(text, max_chars=max_chars),
        headers={str(k): str(v) for k, v in response.headers.items()},
    )
