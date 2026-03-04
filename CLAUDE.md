# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is docscout

CLI tool for exploratory data analysis of business document databases (PDF, DOCX, PPTX). Designed to inform agentic retrieval/search projects and test dataset curation. Uses [Docling](https://github.com/DS4SD/docling) for document parsing.

## Commands

```bash
# Install (use uv, not pip)
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Run CLI
uv run docscout <file-or-directory>

# Tests
uv run pytest                        # all tests
uv run pytest tests/test_parsing.py  # single file
uv run pytest -k "test_name"         # single test

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

Ruff line-length is 100.

## Architecture

Single-command Typer CLI (`cli.py` → `app`). Two modes: single-file analysis and directory profiling.

**Data flow — single file:** `cli.main` → `parsing.parse_file` → Docling `DocumentConverter` → `FileResult` → render or JSON output

**Data flow — directory:** `cli.main` → `scanner.scan_directory` → `discover_files` (recursive, skips hidden) → for each supported file: check `Cache.get` → `parsing.parse_file` → `Cache.put` → aggregate into `DirectorySummary` → render or JSON output

**Key modules:**
- `models.py` — Pydantic models: `FileResult` (per-file metrics, unit of caching), `DirectorySummary` (aggregate stats + filetype distribution), `FiletypeCount`
- `parsing.py` — Wraps Docling. Imports Docling lazily inside `parse_file()` (heavy dependency). Extracts page/word/char/table/figure/heading/section counts by iterating `doc.iterate_items()` and checking `DocItem.label`
- `scanner.py` — Directory orchestration: file discovery, cache lookups, progress bars, aggregation
- `cache.py` — SQLite cache (`~/.cache/docscout/cache.db`), keyed by absolute path, invalidated on size/mtime change
- `categories.py` — Extension→category mapping. Only `{pdf, docx, pptx}` are supported for parsing; all others are categorized but skipped
- `display.py` — Rich terminal rendering (panels, tables)
- `logging.py` — Simple stderr verbose logging via global `_verbose` flag

**Entry point:** `pyproject.toml` registers `docscout = "docscout.cli:app"`. Source lives in `src/docscout/` (src layout, built with hatchling).
