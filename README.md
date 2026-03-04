# docscout

[![CI](https://github.com/felixpeters/docscout/actions/workflows/ci.yml/badge.svg)](https://github.com/felixpeters/docscout/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/docscout)](https://pypi.org/project/docscout/)
[![Python versions](https://img.shields.io/pypi/pyversions/docscout)](https://pypi.org/project/docscout/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

CLI tool for exploratory data analysis of business document databases (PDF, DOCX, PPTX). Designed to inform agentic retrieval/search projects and test dataset curation. Uses [Docling](https://github.com/DS4SD/docling) for document parsing.

## Installation

Requires Python 3.11+. Uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
pip install docscout
```

Or from source:

```bash
uv venv && source .venv/bin/activate
uv pip install -e .
```

For development (includes pytest, ruff, mypy, and pre-commit):

```bash
uv pip install -e ".[dev]"
```

## Usage

### Single file analysis

Parses a document and reports page, word, character, table, figure, heading, and section counts.

```bash
docscout report.pdf
docscout quarterly_review.pptx
docscout report.pdf --format json
```

DOCX and PPTX files are automatically converted to PDF via LibreOffice before parsing.

### Directory profiling

Recursively scans a directory, parses all supported files, and displays aggregate statistics with per-metric breakdowns (total, avg, std, median, min, max with file paths).

```bash
docscout ./contracts/
docscout ./contracts/ --detail    # per-file detail table
docscout ./contracts/ --format json
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--format` | `rich` | Output format: `rich` (terminal tables) or `json` |
| `--detail` | off | Show per-file detail table (directory mode only) |
| `--cache-dir` | `~/.cache/docscout/` | Override cache location |
| `--no-cache` | off | Bypass cache and force re-parse |
| `--verbose` / `-v` | off | Enable verbose logging to stderr |
| `--save-images` | off | Save annotated page images to the given directory |
| `--version` | | Print version and exit |

### Supported file types

Parsed via [Docling](https://github.com/DS4SD/docling): **PDF**, **DOCX**, **PPTX**

DOCX and PPTX files require [LibreOffice](https://www.libreoffice.org/) to be installed (`soffice` on `PATH`) for conversion to PDF before parsing.

All other file types found during directory scans are categorized and counted in the filetype distribution but not parsed for content metrics.

### Caching

Results are cached in a SQLite database (`~/.cache/docscout/cache.db`) keyed by absolute file path. Cache entries are automatically invalidated when file size or modification time changes. Use `--no-cache` to force a fresh parse.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Input error (bad path, unsupported file type) |
| 2 | Partial failure (some files failed to parse) |

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for full setup instructions.

```bash
uv run pytest                        # all tests
uv run pytest tests/test_parsing.py  # single file
uv run pytest -k "test_name"         # single test

uv run ruff check src/ tests/        # lint
uv run ruff format src/ tests/       # format
uv run mypy src/                     # type check
```

## Future features

- **`--no-recurse` flag** — flat directory scan (no subdirectory traversal)
- **Language detection** — per-document language via `langdetect` or similar
- **Python API** — expose `parse_file()` and `scan_directory()` as a public library interface
- **Additional formats** — images (dimensions, EXIF), CSV/XLSX (row/column count), HTML
- **Filtering / querying** — e.g. `--filter "tables > 5"`
- **Parallel parsing** — multi-file parsing via `concurrent.futures`
- **Cache management CLI** — `docscout cache clear`, `docscout cache stats`

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT
