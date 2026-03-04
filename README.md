# docscout

CLI tool for exploratory data analysis of business document databases, designed to inform agentic retrieval/search projects and test dataset curation.

## Installation

Requires Python 3.11+.

```bash
pip install .
```

For development:

```bash
pip install -e ".[dev]"
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

```bash
# Run tests
pytest

# Lint and format
ruff check src/ tests/
ruff format src/ tests/
```

## License

MIT
