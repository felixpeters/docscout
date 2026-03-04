# docscout

[![CI](https://github.com/felixpeters/docscout/actions/workflows/ci.yml/badge.svg)](https://github.com/felixpeters/docscout/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/docscout)](https://pypi.org/project/docscout/)
[![Python versions](https://img.shields.io/pypi/pyversions/docscout)](https://pypi.org/project/docscout/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

CLI tool for exploratory data analysis of business document databases, designed to inform agentic retrieval/search projects and test dataset curation.

## Installation

Requires Python 3.11+.

```bash
pip install docscout
```

For development:

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Usage

### Single file analysis

```bash
docscout report.pdf
docscout report.pdf --format json
```

### Directory profiling

```bash
docscout ./contracts/
docscout ./contracts/ --detail
docscout ./contracts/ --format json
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--format` | `rich` | Output format: `rich` (terminal tables) or `json` |
| `--detail` | off | Show per-file detail table (directory mode only) |
| `--cache-dir` | `~/.cache/docscout/` | Override cache location |
| `--no-cache` | off | Bypass cache and force re-parse |
| `--version` | | Print version and exit |

### Supported file types

Parsed via [Docling](https://github.com/DS4SD/docling): **PDF**, **DOCX**, **PPTX**

All other file types found during directory scans are categorized and counted in the filetype distribution but not parsed for content metrics.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Input error (bad path, unsupported file type) |
| 2 | Partial failure (some files failed to parse) |

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for full setup instructions.

```bash
uv run pytest                          # tests
uv run ruff check src/ tests/          # lint
uv run ruff format src/ tests/         # format
uv run mypy src/                       # type check
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT
