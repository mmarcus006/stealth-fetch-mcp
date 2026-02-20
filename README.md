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
uv run python -m stealth_fetch_mcp.server
```

## Tool Reference

### `stealth_fetch_page`

- `url` (required)
- `impersonate` (default: `"chrome"`)
- `headers` (optional object)
- `timeout` (default: `30`)
- `follow_redirects` (default: `true`)
- `max_chars` (default: `100000`)
- returns: raw HTML string

### `stealth_fetch_text`

- `url` (required)
- `impersonate` (default: `"chrome"`)
- `selector` (optional CSS selector)
- `max_chars` (default: `50000`)
- returns: cleaned markdown-ish text content

### `stealth_fetch_json`

- `url` (required)
- `impersonate` (default: `"chrome"`)
- `headers` (optional object)
- `method` (`"GET"` or `"POST"`, default: `"GET"`)
- `body` (optional JSON string for POST)
- `max_chars` (default: `100000`)
- returns: pretty-printed JSON string

### `stealth_extract_links`

- `url` (required)
- `impersonate` (default: `"chrome"`)
- `selector` (default: `"a[href]"`)
- `pattern` (optional regex on `href`)
- `max_results` (default: `100`)
- `max_chars` (default: `100000`)
- returns: JSON list of `{text, href, absolute_url}`

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
uv run python -m stealth_fetch_mcp.server
uv build
claude mcp add --help
codex mcp add --help
```

## Limitations and Safety

- This server improves transport-level compatibility, but it is not a CAPTCHA solver.
- Always respect site terms of service, robots rules, and rate limits.
- Keep request scopes targeted; avoid scraping sensitive or restricted content.

## License

MIT. See `LICENSE`.

## Contributing

See `CONTRIBUTING.md`.
