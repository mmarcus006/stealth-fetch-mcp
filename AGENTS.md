# Repository Guidelines
<!-- Generated: 2026-02-21 | Updated: 2026-02-21 -->

## What This Server Does
`stealth-fetch-mcp` is an MCP server that fetches web content using `curl_cffi` browser impersonation to reduce bot-blocking compared to default Python HTTP clients. It exposes nine read-only tools:

- `stealth_fetch_page`: returns raw HTML.
- `stealth_fetch_text`: returns cleaned, readable text.
- `stealth_fetch_json`: calls JSON endpoints (`GET`/`POST`) and returns pretty JSON.
- `stealth_extract_links`: returns extracted links with optional selector/regex filtering.
- `stealth_fetch_headers`: returns `{status_code, final_url, headers}` as JSON.
- `stealth_extract_metadata`: extracts JSON-LD, Open Graph, Twitter Card, and `<meta>` tags as JSON.
- `stealth_extract_tables`: extracts HTML tables as `[{headers, rows}]` JSON.
- `stealth_fetch_feed`: fetches and parses RSS 2.0 or Atom feeds into structured JSON.
- `stealth_fetch_bulk`: fetches 1–50 URLs concurrently with per-URL error isolation.

All tools enforce truncation and return actionable errors.

## Key Files

| File | Description |
|------|-------------|
| `pyproject.toml` | Project metadata, dependencies, build config, tool settings (ruff, mypy, pytest) |
| `README.md` | User-facing documentation and MCP client configuration examples |
| `CONTRIBUTING.md` | Contribution guidelines |
| `.python-version` | Pins Python version for uv |
| `uv.lock` | Locked dependency graph — do not edit manually |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `src/` | Application source code — the `stealth_fetch_mcp` package (see `src/AGENTS.md`) |
| `tests/` | Pytest test suite covering client, parser, and server behavior (see `tests/AGENTS.md`) |

## Project Structure & Code Map
- `src/stealth_fetch_mcp/server.py`: MCP tool schemas, argument validation, tool wiring, `SERVER_INSTRUCTIONS`.
- `src/stealth_fetch_mcp/client.py`: shared request/session layer, impersonation defaults, error mapping.
- `src/stealth_fetch_mcp/parser.py`: HTML parsing, readability-style extraction, link normalization.
- `src/stealth_fetch_mcp/__main__.py`: enables `python -m stealth_fetch_mcp` invocation.
- `tests/test_client.py`: transport/session behavior and error-path tests.
- `tests/test_parser.py`: parsing and extraction behavior.
- `tests/test_server.py`: MCP tool contract tests.

## For AI Agents

### Working In This Directory
- Python `3.12+`, 4-space indentation, max line length `100`, explicit type hints.
- Use `snake_case` for functions/modules and keep reusable logic in `client.py`/`parser.py`.
- Do not add new top-level files without a clear reason; prefer extending existing modules.
- Never edit `uv.lock` manually — run `uv sync` after changing `pyproject.toml`.

### Testing Requirements
Run the full quality gate before considering any change complete:
```
uv run pytest -q && uv run ruff check . && uv run mypy src
```

Individual commands:
- `uv run pytest -q` — run tests
- `uv run pytest --cov=stealth_fetch_mcp --cov-report=term-missing` — coverage report
- `uv run ruff check .` — lint
- `uv run mypy src` — type checks with strict settings

### Testing Workflow
1. Start with focused tests for the file you changed, then run full suite.
2. For parsing changes, add/adjust cases in `tests/test_parser.py` using stable HTML fixtures.
3. For request/settings changes, validate in `tests/test_client.py` with deterministic mocks/local servers.
4. For MCP schema/tool behavior, add assertions in `tests/test_server.py` and verify required/optional fields.

### Changing Runtime Settings
Default behavior uses `impersonate="chrome"` with bounded output (`max_chars` varies per tool). Adjust behavior per call instead of changing global code where possible.

Examples:

```json
{"url":"https://example.com","impersonate":"chrome124","timeout":20,"follow_redirects":true}
```

```json
{
  "url":"https://api.example.com/data",
  "method":"POST",
  "headers":{"content-type":"application/json"},
  "body":"{\"q\":\"mcp\"}",
  "request_options":{"verify":true,"allow_redirects":false}
}
```

```json
{
  "url":"https://example.com",
  "session_options":{"proxy":"http://127.0.0.1:8080"},
  "request_options":{"curl_options":[{"option":"TIMEOUT_MS","value":8000}]}
}
```

Use `session_options` for session-level defaults and `request_options` for per-request overrides.

## Build, Run, and Test Locally
- `uv sync`: install runtime + dev dependencies.
- `uv run stealth-fetch-mcp`: run server entrypoint.
- `uv run python -m stealth_fetch_mcp`: equivalent direct module run.
- `uv run python -m stealth_fetch_mcp.server`: also works (legacy).
- `uv run pytest -q`: run tests.
- `uv run pytest --cov=stealth_fetch_mcp --cov-report=term-missing`: coverage report.
- `uv run ruff check .`: lint.
- `uv run mypy src`: type checks with strict settings.

## GitHub Actions

Two workflows live in `.github/workflows/`:

| Workflow | File | Trigger |
|----------|------|---------|
| Claude Code Review | `claude-code-review.yml` | `pull_request` events (opened, synchronize, ready_for_review, reopened) |
| Claude PR Assistant | `claude.yml` | Issue/PR comments or reviews containing `@claude`; new issues with `@claude` in title/body |

**Important for agents:** Neither workflow fires on direct pushes to `main`.
To trigger the code review, open a pull request instead of pushing directly to `main`.
The PR assistant responds to `@claude` mentions in comments on any open issue or PR.

## Coding, Commits, and PRs
- Python `3.12+`, 4-space indentation, max line length `100`, explicit type hints.
- Use `snake_case` for functions/modules and keep reusable logic in `client.py`/`parser.py`.
- Commit messages should be imperative and specific, for example: `Expand curl_cffi option coverage across MCP tools`.
- PRs should include intent, risk notes, commands executed, and docs updates when tool arguments/behavior change.
- Use feature branches and PRs (not direct pushes to `main`) when you want the Claude Code Review workflow to run automatically.

## Dependencies

### Runtime
- `mcp[cli]` — MCP server framework (FastMCP)
- `curl-cffi>=0.7` — Browser impersonation via libcurl with TLS/HTTP fingerprinting
- `beautifulsoup4>=4.12` + `lxml>=5.0` — HTML parsing
- `pydantic>=2` — Input validation and schema generation

### Dev
- `pytest` + `pytest-asyncio` + `pytest-cov` — test framework
- `ruff` — linting and formatting
- `mypy` — static type checking

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
