<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-02-21 | Updated: 2026-02-21 -->

# src

## Purpose
Source root for the `stealth-fetch-mcp` package. Contains the single installable Python package `stealth_fetch_mcp`. This directory exists as the `hatchling` build source root — the wheel packages everything under `src/stealth_fetch_mcp/`.

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `stealth_fetch_mcp/` | The MCP server package — all runtime code lives here (see `stealth_fetch_mcp/AGENTS.md`) |

## For AI Agents

### Working In This Directory
- Do not add Python modules directly in `src/`; all code belongs inside `src/stealth_fetch_mcp/`.
- New sub-packages would require a corresponding `packages` entry in `pyproject.toml`.
- The `src/` layout is intentional — it prevents accidental imports of the package from the repo root without installation.

### Testing Requirements
Tests import from `stealth_fetch_mcp` (not `src.stealth_fetch_mcp`). Ensure `uv sync` has been run so the package is installed in the venv before running pytest.

## Dependencies

### Internal
- `stealth_fetch_mcp/` — the only package in this source root

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
