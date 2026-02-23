# Tech Stack

## Language
- **Python 3.12+** — target version enforced in `pyproject.toml` (`target-version = "py312"`)

## Package Management & Build
- **uv** — package manager and virtual environment tool
- **hatchling** — build backend (`[build-system]` in `pyproject.toml`)

## Runtime Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `mcp[cli]` | latest | MCP server framework (FastMCP), provides tool registration, lifespan management, and stdio transport |
| `curl-cffi` | >=0.7 | Browser TLS/JA3/HTTP2 fingerprint impersonation via libcurl bindings |
| `beautifulsoup4` | >=4.12 | HTML parsing for text extraction, link discovery, metadata, and table extraction |
| `lxml` | >=5.0 | Fast HTML/XML parser backend for BeautifulSoup |
| `pydantic` | >=2 | Input validation, schema generation, and configuration models |

## Dev Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | >=9.0.2 | Test framework |
| `pytest-asyncio` | >=1.3.0 | Async test support (`asyncio_mode = "auto"`) |
| `pytest-cov` | >=7.0.0 | Coverage reporting |
| `ruff` | >=0.15.2 | Linting and formatting (line-length: 100) |
| `mypy` | >=1.19.1 | Static type checking (`disallow_untyped_defs = true`) |

## Key Stdlib Modules Used
- `asyncio` — concurrent bulk fetching
- `json` — JSON serialization/deserialization
- `xml.etree.ElementTree` — RSS/Atom feed XML parsing
- `re` — regex filtering for link extraction
- `urllib.parse` — URL resolution and validation
- `http.server` — local test HTTP servers (tests only)

## CI/CD
- **GitHub Actions** — two workflows:
  - `claude-code-review.yml` — automated code review on pull requests
  - `claude.yml` — PR assistant responding to `@claude` mentions
