<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-21 | Updated: 2026-02-21 -->

# tests

## Purpose
Pytest test suite for the `stealth_fetch_mcp` package. Uses real in-process HTTP servers (via `ThreadingHTTPServer`) instead of mocks to give high-fidelity coverage of the full request/response pipeline. All tests are async-compatible via `pytest-asyncio` in auto mode.

## Key Files

| File | Description |
|------|-------------|
| `test_client.py` | Transport and session behavior: `_fetch`, `_create_session`, redirect handling, timeouts, truncation, HTTP error mapping, request options (params, headers) |
| `test_parser.py` | HTML parsing and link extraction: `_clean_html`, `extract_links`, selector scoping, truncation, regex filtering |
| `test_server.py` | MCP tool contracts: input model validation, tool registration/annotations, lifespan session management, full tool impl integration against a live HTTP server |

## For AI Agents

### Working In This Directory
- All tests use `ThreadingHTTPServer` on a random port (`0`) — no external network required.
- Do NOT add `unittest.mock` patches over network calls; spin up a local handler instead.
- Test functions for async code must be `async def` and are auto-collected via `asyncio_mode = "auto"` in `pyproject.toml`.
- Keep HTTP handler classes (`_TestHandler`, `_ServerHandler`) minimal — add only the paths needed for a new test.
- Follow the existing fixture pattern: yield the base URL, shut down in `finally`.

### Testing Requirements
Run the targeted test file first, then the full suite:
```
uv run pytest tests/test_client.py -q
uv run pytest tests/test_parser.py -q
uv run pytest tests/test_server.py -q
uv run pytest -q
```

Coverage report:
```
uv run pytest --cov=stealth_fetch_mcp --cov-report=term-missing
```

### Common Patterns

**Local HTTP server fixture:**
```python
@pytest.fixture()
def base_url() -> str:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)
```

**Async test with session:**
```python
@pytest.mark.asyncio
async def test_something(base_url: str) -> None:
    async with _create_session() as session:
        result = await _fetch(session, url=f"{base_url}/path")
    assert ...
```

## Dependencies

### Internal
- `stealth_fetch_mcp.client` — `_fetch`, `_create_session`, `FetchError`
- `stealth_fetch_mcp.parser` — `_clean_html`, `extract_links`, `_resolve_url`
- `stealth_fetch_mcp.server` — input models, impl functions, `app_lifespan`, `mcp`

### External
- `pytest>=9.0.2` — test runner
- `pytest-asyncio>=1.3.0` — async test support
- `pytest-cov` — coverage reporting

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
