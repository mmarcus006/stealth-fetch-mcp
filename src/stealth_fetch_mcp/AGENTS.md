<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-21 | Updated: 2026-02-21 -->

# stealth_fetch_mcp

## Purpose
The core MCP server package. Implements browser-impersonated HTTP fetching via `curl_cffi` and exposes four read-only MCP tools. The package is split into three functional modules: `server` (tool definitions and wiring), `client` (HTTP transport), and `parser` (HTML processing). The `__init__.py` serves as the package entry point for CLI use.

## Key Files

| File | Description |
|------|-------------|
| `server.py` | FastMCP tool definitions, Pydantic input models, request option merging, session lifecycle management (`app_lifespan`). The four MCP tools are registered here. |
| `client.py` | `AsyncSession` creation and configuration, `_fetch` coroutine, curl option normalization, error classification and actionable message mapping. Shared constants (`DEFAULT_IMPERSONATE`, `DEFAULT_TIMEOUT`, `DEFAULT_MAX_CHARS`). |
| `parser.py` | `_clean_html` — readability-style text extraction that strips noise tags and renders Markdown-like output. `extract_links` — CSS-selector + regex link extraction returning JSON. |
| `__init__.py` | Package entry point; re-exports `main` for the `stealth-fetch-mcp` CLI script. |

## For AI Agents

### Architecture: Three-Layer Design
```
server.py  ←  validates input, merges options, manages session scope
    ↓
client.py  ←  executes HTTP request, normalizes curl options, maps errors
    ↓
parser.py  ←  processes HTML response into text/links
```

- **Add new MCP tools** in `server.py`: define a Pydantic input model inheriting `_BaseInputModel`, write an `_impl` coroutine, register with `@mcp.tool()`.
- **Add new request behavior** (auth, proxy, curl options) in `client.py`: extend `_normalize_options` or `_create_session`.
- **Add new HTML extraction logic** in `parser.py`: extend `_clean_html` or add new public functions.

### Working In This Directory
- All public functions and classes must have explicit type annotations (mypy strict mode).
- `_` prefix = private/internal — do not export or call from outside the module without good reason.
- Keep `client.py` and `parser.py` free of MCP/FastMCP imports — they are standalone utilities.
- `server.py` is the only file that imports from both `client` and `parser`.
- Pydantic models use `ConfigDict(extra="forbid")` — unknown fields raise `ValidationError`.
- `_options_to_dict` serializes Pydantic models to kwargs dicts, converting `curl_options` lists to `{CurlOpt: value}` maps.
- Session scope: tools use the shared `AppContext.session` by default; `session_options` triggers an ephemeral session via `_session_scope`.
- All output is truncated via `_truncate` before being returned to MCP callers.

### Testing Requirements
Each module has a dedicated test file:
- Changes to `server.py` → add/update `tests/test_server.py`
- Changes to `client.py` → add/update `tests/test_client.py`
- Changes to `parser.py` → add/update `tests/test_parser.py`

Run targeted tests first:
```
uv run pytest tests/test_server.py -q
uv run pytest tests/test_client.py -q
uv run pytest tests/test_parser.py -q
```

Then full gate:
```
uv run pytest -q && uv run ruff check . && uv run mypy src
```

### Common Patterns

**Adding a new MCP tool (server.py):**
```python
class MyNewToolInput(_BaseInputModel):
    url: str = Field(..., description="Target URL.")
    max_chars: int = Field(default=50_000, gt=0, le=1_000_000)
    session_options: SessionOptionsInput | None = Field(default=None, ...)
    request_options: RequestOptionsInput | None = Field(default=None, ...)

@mcp.tool(name="my_new_tool", annotations=READONLY_TOOL_ANNOTATIONS)
async def my_new_tool(params: MyNewToolInput, ctx: Context[ServerSession, AppContext]) -> str:
    """Docstring shown in MCP tool listing."""
    return await _my_new_tool_impl(params, ctx.request_context.lifespan_context.session)
```

**curl_options usage (via request_options):**
```json
{"request_options": {"curl_options": [{"option": "TIMEOUT_MS", "value": 8000}]}}
```
Option keys accept: `"TIMEOUT_MS"`, `"CurlOpt.TIMEOUT_MS"`, or numeric id.

**Fingerprint customization:**
```json
{
  "impersonate": "chrome124",
  "session_options": {
    "ja3": "...",
    "extra_fp": {"tls_grease": true, "http2_no_priority": true}
  }
}
```

## Dependencies

### Internal
- `server.py` imports from `client.py` and `parser.py`
- `__init__.py` imports `main` from `server.py`

### External
- `curl_cffi` — `AsyncSession`, `BrowserTypeLiteral`, `CurlOpt`, exception types
- `mcp` — `FastMCP`, `Context`, `ServerSession`, `ToolAnnotations`
- `pydantic` — `BaseModel`, `Field`, `field_validator`, `ConfigDict`
- `beautifulsoup4` + `lxml` — HTML parsing in `parser.py`

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
