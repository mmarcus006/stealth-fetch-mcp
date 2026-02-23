# Setup Guide

## Prerequisites

- **Python 3.12+** — required by `pyproject.toml`
- **uv** — Python package manager ([install guide](https://docs.astral.sh/uv/getting-started/installation/))
- **Git** — for cloning the repository

## Installation

```bash
# Clone the repository
git clone https://github.com/mmarcus006/stealth-fetch-mcp.git
cd stealth-fetch-mcp

# Install all dependencies (runtime + dev)
uv sync
```

## Environment Variables

No `.env` file or environment variables are required. The server runs entirely locally with no external service dependencies.

## Running the MCP Server

```bash
# Via console script entry point
uv run stealth-fetch-mcp

# Or directly as a Python module
uv run python -m stealth_fetch_mcp.server
```

The server starts in stdio transport mode, ready to accept MCP client connections.

## MCP Client Configuration

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

### Codex CLI

```bash
codex mcp add stealth-fetch -- uvx --from /path/to/stealth-fetch-mcp stealth-fetch-mcp
```

## Running Tests

```bash
# Quick test run
uv run pytest -q

# With coverage report
uv run pytest --cov=stealth_fetch_mcp --cov-report=term-missing
```

## Quality Gates

Run the full quality gate before committing:

```bash
uv run pytest -q && uv run ruff check . && uv run mypy src
```

Individual commands:

| Command | Purpose |
|---------|---------|
| `uv run pytest -q` | Run test suite |
| `uv run pytest --cov=stealth_fetch_mcp --cov-report=term-missing` | Coverage report |
| `uv run ruff check .` | Lint check (line-length: 100) |
| `uv run mypy src` | Static type check (strict mode) |

## Verification

```bash
# Verify the package imports correctly
uv run python -c "from stealth_fetch_mcp.server import mcp; print('OK')"

# Build a distributable wheel
uv build
```
