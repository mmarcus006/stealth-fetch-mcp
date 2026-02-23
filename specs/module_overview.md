# Module Overview

This document describes the responsibility of each source module in the `stealth_fetch_mcp` package.

## Source Modules (`src/stealth_fetch_mcp/`)

- **`__init__.py`**: Package entry point. Re-exports `main()` from `server.py` so the package can be invoked as `python -m stealth_fetch_mcp.server` or via the `stealth-fetch-mcp` console script.

- **`client.py`**: Transport layer. Provides `_create_session()` for constructing `curl_cffi.AsyncSession` instances with impersonation defaults, `_fetch()` for executing HTTP requests with unified error handling, and `FetchResult` as the canonical response dataclass. Also handles `curl_options` normalization (string/int keys to `CurlOpt` enums) and output truncation. All network I/O flows through this module.

- **`parser.py`**: Content extraction layer. Contains pure functions that transform raw HTML/XML text into structured output:
  - `_clean_html()` — readability-style text extraction with noise tag removal and markdown-ish formatting
  - `extract_links()` — CSS selector + regex filtered link discovery with URL resolution
  - `extract_metadata()` — JSON-LD, Open Graph, Twitter Card, and `<meta>` tag extraction
  - `extract_tables()` — HTML `<table>` to `{headers, rows}` JSON conversion with automatic header detection
  - `parse_feed()` — RSS 2.0 and Atom feed XML parsing into structured JSON

- **`server.py`**: MCP tool surface. Defines the `FastMCP` server instance, all 9 tool functions, Pydantic input models (`StealthFetchPageInput`, etc.), session/request option schemas (`SessionOptionsInput`, `RequestOptionsInput`), and the `SERVER_INSTRUCTIONS` constant that guides consuming models. Manages the shared `AsyncSession` via lifespan context and provides `_session_scope` for ephemeral session creation when `session_options` are provided.

## Test Modules (`tests/`)

- **`test_client.py`**: Tests for `client.py` — session creation defaults, fetch success/error/timeout/redirect behavior, request option passthrough, and truncation. Uses a local `ThreadingHTTPServer` fixture.

- **`test_parser.py`**: Tests for `parser.py` — HTML cleaning, link extraction with patterns, metadata extraction (JSON-LD, OG, Twitter, meta), table extraction (thead/tbody, headerless, multiple tables), and feed parsing (RSS 2.0, Atom, error cases). All tests use inline HTML fixtures.

- **`test_server.py`**: Tests for `server.py` — input model validation constraints, tool registration and annotation verification, lifespan session lifecycle, all 9 tool `_impl` functions against a live local HTTP server, request option passthrough, and bulk fetch error isolation.

## Data Flow

```
MCP Client Request
  → server.py (Pydantic validation → _impl function)
    → client.py (_fetch via AsyncSession)
      → curl_cffi (browser-impersonated HTTP request)
    ← FetchResult (status, url, text, headers)
    → parser.py (optional: clean/extract/parse)
  ← Truncated string response to MCP client
```
