# Project Structure

```text
stealth-fetch-mcp/
├── .github/
│   └── workflows/
│       ├── claude-code-review.yml   # PR code review workflow
│       └── claude.yml               # @claude PR assistant workflow
├── src/
│   └── stealth_fetch_mcp/
│       ├── __init__.py              # Package entry point, re-exports main()
│       ├── client.py                # AsyncSession factory, _fetch(), FetchResult, error mapping
│       ├── parser.py                # HTML cleaning, link/metadata/table extraction, feed parsing
│       └── server.py                # FastMCP server, Pydantic input models, tool registration
├── tests/
│   ├── test_client.py               # Transport/session behavior, error paths, request options
│   ├── test_parser.py               # Parsing, extraction, and feed behavior
│   └── test_server.py               # MCP tool contracts, input validation, integration tests
├── specs/                           # Generated project documentation (this directory)
├── .gitignore
├── .python-version                  # Python version pin for uv
├── AGENTS.md                        # Repository guidelines for AI agents
├── CONTRIBUTING.md                  # Contribution guidelines
├── LICENSE                          # MIT license
├── README.md                        # User-facing documentation
├── pyproject.toml                   # Project metadata, dependencies, tool config
└── uv.lock                          # Locked dependency graph (auto-generated)
```
