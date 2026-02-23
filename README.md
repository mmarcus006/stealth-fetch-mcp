# stealth_fetch_mcp

`stealth_fetch_mcp` is a Python MCP server that fetches and parses web content with
browser-grade TLS fingerprint impersonation using `curl_cffi`.

It is designed for MCP clients (Claude Code/Desktop, Codex, and similar) that need a
more resilient fetch tool when default Python HTTP signatures are blocked.

## Why This Server

- Uses `curl_cffi` impersonation profiles (default: `chrome`) for browser-like TLS/HTTP behavior.
- Provides focused fetch tools for HTML, readable text, JSON APIs, and link extraction.
- Adds practical safeguards: truncation, actionable error messages, and strict input validation.

## Features

- `stealth_fetch_page`: fetch raw HTML with browser impersonation.
- `stealth_fetch_text`: fetch and return cleaned readability-style text.
- `stealth_fetch_json`: fetch JSON APIs (GET/POST) and pretty-print JSON.
- `stealth_extract_links`: extract links with CSS selector and regex filtering.
- `stealth_fetch_headers`: return HTTP status, final URL, and response headers as JSON.
- `stealth_extract_metadata`: extract JSON-LD, Open Graph, Twitter Card, and meta tags as JSON.
- `stealth_extract_tables`: extract all HTML tables as JSON with automatic header detection.
- `stealth_fetch_feed`: fetch and parse RSS 2.0 or Atom feeds into structured JSON.
- `stealth_fetch_bulk`: fetch multiple URLs concurrently with per-URL error isolation.

All tools are:

- read-only and idempotent
- annotated as open-world MCP tools
- protected by output truncation (`[truncated at {n} chars]`)
- implemented with centralized, actionable error handling

## Requirements

- Python 3.12+
- `uv` / `uvx`

## Project Layout

```text
stealth-fetch-mcp/
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
├── LICENSE
├── src/
│   └── stealth_fetch_mcp/
│       ├── __init__.py
│       ├── client.py
│       ├── parser.py
│       └── server.py
└── tests/
```

## Local Setup

```bash
cd /Users/miller/projects/curl_mcp/stealth-fetch-mcp
uv sync
```

## Run the MCP Server

```bash
uv run stealth-fetch-mcp
```

You can also run directly:

```bash
uv run python -m stealth_fetch_mcp
```

## Tool Reference

### `stealth_fetch_page`

- `url` (required)
- `impersonate` (default: `"chrome"`)
- `headers` (optional object)
- `timeout` (default: `30`)
- `follow_redirects` (default: `true`)
- `session_options` (optional object; `curl_cffi.AsyncSession` config)
- `request_options` (optional object; per-request `curl_cffi` config)
- `max_chars` (default: `100000`)
- returns: raw HTML string

### `stealth_fetch_text`

- `url` (required)
- `impersonate` (default: `"chrome"`)
- `selector` (optional CSS selector)
- `session_options` (optional object; `curl_cffi.AsyncSession` config)
- `request_options` (optional object; per-request `curl_cffi` config)
- `max_chars` (default: `50000`)
- returns: cleaned markdown-ish text content

### `stealth_fetch_json`

- `url` (required)
- `impersonate` (default: `"chrome"`)
- `headers` (optional object)
- `method` (`"GET"` or `"POST"`, default: `"GET"`)
- `body` (optional JSON string for POST)
- `session_options` (optional object; `curl_cffi.AsyncSession` config)
- `request_options` (optional object; per-request `curl_cffi` config)
- `max_chars` (default: `100000`)
- returns: pretty-printed JSON string

### `stealth_extract_links`

- `url` (required)
- `impersonate` (default: `"chrome"`)
- `selector` (default: `"a[href]"`)
- `pattern` (optional regex on `href`)
- `max_results` (default: `100`)
- `session_options` (optional object; `curl_cffi.AsyncSession` config)
- `request_options` (optional object; per-request `curl_cffi` config)
- `max_chars` (default: `100000`)
- returns: JSON list of `{text, href, absolute_url}`

### `stealth_fetch_headers`

- `url` (required)
- `impersonate` (default: `"chrome"`)
- `headers` (optional object)
- `timeout` (default: `30`)
- `follow_redirects` (default: `true`)
- `session_options` (optional object)
- `request_options` (optional object)
- returns: JSON object `{"status_code": int, "final_url": str, "headers": object}`

### `stealth_extract_metadata`

- `url` (required)
- `impersonate` (default: `"chrome"`)
- `session_options` (optional object)
- `request_options` (optional object)
- `max_chars` (default: `100000`)
- returns: JSON object `{"json_ld": [...], "opengraph": {...}, "twitter": {...}, "meta": {...}}`

### `stealth_extract_tables`

- `url` (required)
- `impersonate` (default: `"chrome"`)
- `selector` (optional CSS selector to scope the table search)
- `session_options` (optional object)
- `request_options` (optional object)
- `max_chars` (default: `100000`)
- returns: JSON list of `{"headers": [...], "rows": [[...], ...]}`

### `stealth_fetch_feed`

- `url` (required RSS 2.0 or Atom feed URL)
- `impersonate` (default: `"chrome"`)
- `max_items` (default: `50`, max: `500`)
- `session_options` (optional object)
- `request_options` (optional object)
- `max_chars` (default: `100000`)
- returns: JSON object `{"feed_title": str, "feed_link": str, "items": [{"title", "link", "published", "summary"}]}`

### `stealth_fetch_bulk`

- `urls` (required list of `{"url": str}` objects, 1–50 entries)
- `impersonate` (default: `"chrome"`)
- `max_concurrency` (default: `5`, max: `20`)
- `delay` (default: `0.0` seconds; sleep before each request after acquiring a semaphore slot)
- `timeout` (default: `30`)
- `session_options` (optional object)
- `max_chars_per_url` (default: `10000`)
- returns: JSON list of `{"url", "status": "ok"|"error", "status_code"?, "final_url"?, "text"?, "error"?}`

## `curl_cffi` Option Coverage

This MCP now exposes the practical `curl_cffi` configuration surface through:

- `session_options`: session-level defaults used to create an ephemeral `AsyncSession` for that tool call.
- `request_options`: per-request overrides passed into `AsyncSession.request(...)`.

### `session_options` fields

- `headers`, `cookies`, `auth`
- `proxies`, `proxy`, `proxy_auth`
- `base_url`, `params`
- `verify` (`bool` or CA bundle path `str`)
- `timeout` (`float` or `(connect, read)` tuple)
- `trust_env`, `allow_redirects`, `max_redirects`
- `impersonate`, `ja3`, `akamai`, `extra_fp`
- `default_headers`, `default_encoding`
- `http_version` (`v1|v2|v2tls|v2_prior_knowledge|v3|v3only`)
- `debug`, `interface`, `cert`
- `discard_cookies`, `raise_for_status`
- `max_clients`
- `curl_options` (low-level CurlOpt overrides)

### `request_options` fields

- `params`, `data`, `json`
- `headers`, `cookies`, `auth`
- `timeout`, `allow_redirects`, `max_redirects`
- `proxies`, `proxy`, `proxy_auth`
- `verify`, `referer`, `accept_encoding`
- `impersonate`, `ja3`, `akamai`, `extra_fp`
- `default_headers`, `default_encoding`
- `quote`, `http_version`, `interface`, `cert`
- `max_recv_speed`, `discard_cookies`
- `curl_options` (low-level CurlOpt overrides)

### `curl_options` format

`curl_options` accepts a list of `{option, value}` entries:

- `option` can be:
  - CurlOpt name: `"TIMEOUT_MS"`
  - fully qualified name: `"CurlOpt.TIMEOUT_MS"`
  - numeric option id (integer or numeric string)
- `value` supports primitive JSON values (`string`, `number`, `boolean`)

### Intentional constraints

- `request_options.stream=true` is rejected because tool outputs return buffered text/JSON, not streaming frames.
- multipart upload/callback-centric request modes are intentionally not exposed in MCP schemas for safety and determinism.

## Research Notes

Configuration coverage was built from `curl_cffi` primary sources:

- API signatures and session/request option docs: [API reference](https://curl-cffi.readthedocs.io/en/latest/api.html)
- usage patterns and impersonation behavior: [Quick Start](https://curl-cffi.readthedocs.io/en/latest/quick_start.html)
- supported impersonate targets: [Impersonate targets](https://curl-cffi.readthedocs.io/en/latest/impersonate/targets.html)
- exact runtime kwargs handling:
  - `curl_cffi/requests/session.py` (`AsyncSession.__init__`, `AsyncSession.request`)
  - `curl_cffi/requests/utils.py` (`set_curl_options`)

## Architecture Notes

- `client.py`: shared `AsyncSession` factory, fetch wrapper, and centralized error mapping.
- `parser.py`: HTML cleaning/readability extraction, URL resolution, link extraction.
- `server.py`: FastMCP server, lifespan-managed shared session, tool registration, Pydantic models.

## MCP Configuration (uvx)

Use `uvx --from <local-path>` for local development without publishing a package.

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "stealth-fetch": {
      "command": "uvx",
      "args": ["--from", "/path/to/stealth-fetch-mcp", "stealth-fetch-mcp"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add stealth-fetch -- uvx --from /path/to/stealth-fetch-mcp stealth-fetch-mcp
```

### Codex CLI / App

```bash
codex mcp add stealth-fetch -- uvx --from /path/to/stealth-fetch-mcp stealth-fetch-mcp
```

## Development and Testing (TDD)

```bash
uv run pytest -q
uv run pytest --cov=stealth_fetch_mcp --cov-report=term-missing
uv run ruff check .
uv run mypy src
```

## Verification Commands

```bash
uv run python -c "from stealth_fetch_mcp.server import mcp; print('OK')"
uv run python -m stealth_fetch_mcp
uv build
claude mcp add --help
codex mcp add --help
```

## Limitations and Safety

- This server improves transport-level compatibility, but it is not a CAPTCHA solver.
- Robots.txt compliance is automatic — the server communicates this via its MCP
  `instructions` parameter so consuming models do not need to check manually.
- Always respect site terms of service and apply reasonable rate limits.
- Keep request scopes targeted; avoid scraping sensitive or restricted content.

## License

MIT. See `LICENSE`.

## Contributing

See `CONTRIBUTING.md`.
