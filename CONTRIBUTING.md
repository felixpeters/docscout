# Contributing to docscout

## Development setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/felixpeters/docscout.git
cd docscout
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

Install pre-commit hooks:

```bash
pre-commit install
```

## Running checks

```bash
# Tests
uv run pytest

# Tests with coverage
uv run pytest --cov=docscout --cov-report=term-missing

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type check
uv run mypy src/
```

## Code style

- Formatter and linter: [Ruff](https://docs.astral.sh/ruff/)
- Line length: 100 characters
- Type annotations required on all public functions
- Target Python version: 3.11+

## Pull requests

1. Create a feature branch from `main`
2. Make your changes with clear, focused commits
3. Ensure all checks pass (`ruff check`, `ruff format --check`, `mypy`, `pytest`)
4. Open a PR against `main` with a description of your changes

## Reporting issues

Open an issue at https://github.com/felixpeters/docscout/issues with:

- Steps to reproduce
- Expected vs actual behavior
- Python version and OS
