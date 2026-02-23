# API Contracts

This project is an MCP server — it exposes tools (not HTTP endpoints) via the Model Context Protocol stdio transport. Each tool is registered with `FastMCP` and accepts a Pydantic-validated input model.

All tools share these annotations:
- `readOnlyHint: true`
- `destructiveHint: false`
- `idempotentHint: true`
- `openWorldHint: true`

## Tools

### `stealth_fetch_page`
**Purpose:** Fetch a page and return raw HTML with browser impersonation.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` (required) | — | Target URL (http/https only) |
| `impersonate` | `BrowserTypeLiteral` | `"chrome"` | Browser fingerprint profile |
| `headers` | `dict[str, str]` | `null` | Optional request headers |
| `timeout` | `float` (0–300) | `30` | Request timeout in seconds |
| `follow_redirects` | `bool` | `true` | Follow HTTP redirects |
| `session_options` | `SessionOptionsInput` | `null` | Session-level curl_cffi config |
| `request_options` | `RequestOptionsInput` | `null` | Per-request curl_cffi config |
| `max_chars` | `int` (1–1,000,000) | `100000` | Max characters in response |

**Returns:** Raw HTML string.

---

### `stealth_fetch_text`
**Purpose:** Fetch a page and return cleaned readability-style text.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` (required) | — | Target URL |
| `impersonate` | `BrowserTypeLiteral` | `"chrome"` | Browser fingerprint profile |
| `selector` | `str` | `null` | CSS selector to scope extraction |
| `session_options` | `SessionOptionsInput` | `null` | Session-level config |
| `request_options` | `RequestOptionsInput` | `null` | Per-request config |
| `max_chars` | `int` (1–1,000,000) | `50000` | Max characters in response |

**Returns:** Cleaned markdown-ish text content.

---

### `stealth_fetch_json`
**Purpose:** Fetch a JSON API endpoint and return pretty-printed JSON.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` (required) | — | Target JSON API URL |
| `impersonate` | `BrowserTypeLiteral` | `"chrome"` | Browser fingerprint profile |
| `headers` | `dict[str, str]` | `null` | Optional request headers |
| `method` | `"GET" \| "POST"` | `"GET"` | HTTP method |
| `body` | `str` | `null` | JSON string body for POST |
| `session_options` | `SessionOptionsInput` | `null` | Session-level config |
| `request_options` | `RequestOptionsInput` | `null` | Per-request config |
| `max_chars` | `int` (1–1,000,000) | `100000` | Max characters in response |

**Returns:** Pretty-printed JSON string.

---

### `stealth_extract_links`
**Purpose:** Fetch a page and extract matching links as JSON.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` (required) | — | Target URL |
| `impersonate` | `BrowserTypeLiteral` | `"chrome"` | Browser fingerprint profile |
| `selector` | `str` | `"a[href]"` | CSS selector for link elements |
| `pattern` | `str` | `null` | Regex filter on href values |
| `max_results` | `int` (1–10,000) | `100` | Max links to return |
| `session_options` | `SessionOptionsInput` | `null` | Session-level config |
| `request_options` | `RequestOptionsInput` | `null` | Per-request config |
| `max_chars` | `int` (1–1,000,000) | `100000` | Max characters in response |

**Returns:** JSON list of `{"text", "href", "absolute_url"}`.

---

### `stealth_fetch_headers`
**Purpose:** Return HTTP status code, final URL, and response headers as JSON.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` (required) | — | Target URL |
| `impersonate` | `BrowserTypeLiteral` | `"chrome"` | Browser fingerprint profile |
| `headers` | `dict[str, str]` | `null` | Optional request headers |
| `timeout` | `float` (0–300) | `30` | Request timeout in seconds |
| `follow_redirects` | `bool` | `true` | Follow HTTP redirects |
| `session_options` | `SessionOptionsInput` | `null` | Session-level config |
| `request_options` | `RequestOptionsInput` | `null` | Per-request config |

**Returns:** JSON object `{"status_code": int, "final_url": str, "headers": object}`.

---

### `stealth_extract_metadata`
**Purpose:** Extract structured metadata (JSON-LD, OG, Twitter Card, meta tags) as JSON.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` (required) | — | Target URL |
| `impersonate` | `BrowserTypeLiteral` | `"chrome"` | Browser fingerprint profile |
| `session_options` | `SessionOptionsInput` | `null` | Session-level config |
| `request_options` | `RequestOptionsInput` | `null` | Per-request config |
| `max_chars` | `int` (1–1,000,000) | `100000` | Max characters in response |

**Returns:** JSON object `{"json_ld": [...], "opengraph": {...}, "twitter": {...}, "meta": {...}}`.

---

### `stealth_extract_tables`
**Purpose:** Extract HTML tables as JSON list of `{headers, rows}` objects.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` (required) | — | Target URL |
| `impersonate` | `BrowserTypeLiteral` | `"chrome"` | Browser fingerprint profile |
| `selector` | `str` | `null` | CSS selector to scope table search |
| `session_options` | `SessionOptionsInput` | `null` | Session-level config |
| `request_options` | `RequestOptionsInput` | `null` | Per-request config |
| `max_chars` | `int` (1–1,000,000) | `100000` | Max characters in response |

**Returns:** JSON list of `{"headers": [...], "rows": [[...], ...]}`.

---

### `stealth_fetch_feed`
**Purpose:** Fetch and parse an RSS 2.0 or Atom feed into structured JSON.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` (required) | — | RSS/Atom feed URL |
| `impersonate` | `BrowserTypeLiteral` | `"chrome"` | Browser fingerprint profile |
| `max_items` | `int` (1–500) | `50` | Max feed items to return |
| `session_options` | `SessionOptionsInput` | `null` | Session-level config |
| `request_options` | `RequestOptionsInput` | `null` | Per-request config |
| `max_chars` | `int` (1–1,000,000) | `100000` | Max characters in response |

**Returns:** JSON object `{"feed_title": str, "feed_link": str, "items": [{"title", "link", "published", "summary"}]}`.

---

### `stealth_fetch_bulk`
**Purpose:** Fetch multiple URLs concurrently with per-URL error isolation.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `urls` | `list[{"url": str}]` (1–50) | — | URLs to fetch |
| `impersonate` | `BrowserTypeLiteral` | `"chrome"` | Browser fingerprint profile |
| `max_concurrency` | `int` (1–20) | `5` | Max concurrent requests |
| `delay` | `float` (0–60) | `0.0` | Seconds to sleep before each request |
| `timeout` | `float` (0–300) | `30` | Per-request timeout |
| `session_options` | `SessionOptionsInput` | `null` | Session-level config |
| `max_chars_per_url` | `int` (1–100,000) | `10000` | Max chars per URL response |

**Returns:** JSON list of `{"url", "status": "ok"|"error", "status_code"?, "final_url"?, "text"?, "error"?}`.

---

## Shared Option Schemas

### `SessionOptionsInput`
Session-level defaults for `curl_cffi.AsyncSession`. Key fields: `headers`, `cookies`, `auth`, `proxies`, `proxy`, `verify`, `timeout`, `impersonate`, `ja3`, `akamai`, `extra_fp`, `http_version`, `curl_options`, `max_clients`.

### `RequestOptionsInput`
Per-request overrides for `curl_cffi.AsyncSession.request()`. Key fields: `params`, `data`, `json`, `headers`, `cookies`, `timeout`, `impersonate`, `referer`, `accept_encoding`, `curl_options`. Note: `stream=true` is explicitly rejected.

### `CurlOptionInput`
Low-level libcurl option entry: `{"option": str|int, "value": str|int|float|bool}`. Option can be a CurlOpt name (`"TIMEOUT_MS"`), qualified name (`"CurlOpt.TIMEOUT_MS"`), or numeric ID.

## Error Handling

All tools raise `FetchError` with actionable messages:
- HTTP 4xx/5xx: `"HTTP {status} error. Response snippet: ..."`
- Timeout: `"Request timed out. Try increasing the timeout value."`
- DNS/Connection: `"DNS/connection failed. Check that the URL is correct and reachable."`
- TLS/Impersonation: `"TLS/impersonation error. Try a different impersonate target or verify certificates."`
