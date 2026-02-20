# Contributing

Thanks for contributing to `stealth_fetch_mcp`.

## Development Setup

```bash
uv sync
```

## Quality Gates

Run all checks before opening a pull request:

```bash
uv run pytest -q
uv run pytest --cov=stealth_fetch_mcp --cov-report=term-missing
uv run ruff check .
uv run mypy src
```

## Test Style

- Follow TDD (red -> green -> refactor).
- Prefer deterministic tests.
- For network behavior, use local integration servers instead of external endpoints.

## Code Style

- Python 3.12+ with type hints.
- Keep shared logic in `client.py` and `parser.py` to avoid duplication in tools.
- Return actionable errors rather than stack traces.
