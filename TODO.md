# docscout MVP — Implementation Plan

> Step-by-step build order for the MVP defined in [SPEC.md](./SPEC.md).
> Each phase produces runnable, testable code before moving on.

---

## Phase 0: Project Scaffolding

- [ ] Create `pyproject.toml` with all metadata, dependencies, scripts entry point, build system, ruff + pytest config (copy from spec)
- [ ] Create `src/docscout/__init__.py` exposing `__version__ = "0.1.0"`
- [ ] Create empty module files: `cli.py`, `models.py`, `parsing.py`, `cache.py`, `scanner.py`, `categories.py`, `display.py`
- [ ] Create `tests/` directory with empty `conftest.py`
- [ ] Verify `pip install -e ".[dev]"` (or `uv pip install -e .`) succeeds and `docscout --help` prints without error (stub Typer app)

---

## Phase 1: Data Models (`src/docscout/models.py`)

- [ ] Implement `FiletypeCount` Pydantic model
- [ ] Implement `FileResult` Pydantic model with all fields from spec (content metrics default `None`, `parse_errors`/`parse_warnings` default `[]`, `parsed` default `False`)
- [ ] Implement `DirectorySummary` Pydantic model with all aggregate fields, `filetype_distribution`, and `file_results` list
- [ ] Write `tests/test_models.py`:
  - [ ] `FileResult` JSON serialization round-trip
  - [ ] `DirectorySummary` validates and serializes correctly
  - [ ] Verify default values for optional fields

---

## Phase 2: File Categories (`src/docscout/categories.py`)

- [ ] Define `SUPPORTED_EXTENSIONS` set: `{"pdf", "docx", "pptx"}`
- [ ] Define `EXTENSION_TO_CATEGORY` dict mapping every extension listed in the spec to its category
- [ ] Implement `get_category(extension: str) -> str` helper that returns the category (defaulting to `"other"`)
- [ ] Implement `is_supported(extension: str) -> bool` helper
- [ ] Write unit tests for category lookups (supported types, detection-only types, unknown extension → `"other"`)

---

## Phase 3: Parsing Layer (`src/docscout/parsing.py`)

- [ ] Implement `parse_file(path: Path) -> FileResult`:
  - [ ] Read file stat (size)
  - [ ] Determine extension and category
  - [ ] Guard: if not supported, return `FileResult` with `parsed=False`
  - [ ] Call Docling `DocumentConverter` to parse the file
  - [ ] Extract metrics from Docling result:
    - [ ] Page count from document structure
    - [ ] Word count and char count from exported text
    - [ ] Table count (count `TableItem` elements)
    - [ ] Figure count (count `PictureItem` elements)
    - [ ] Heading count and max heading depth
    - [ ] Section count
  - [ ] Measure parse duration
  - [ ] Catch exceptions → populate `parse_errors`, set `parsed=False`
- [ ] Create test fixtures in `tests/fixtures/`:
  - [ ] `sample.pdf` — 1-2 pages, text, 1 table, 1 heading, 1 figure
  - [ ] `sample.docx` — headings (2 levels), 1 table, body text
  - [ ] `sample.pptx` — 2-3 slides with titles and body text
- [ ] Write `tests/test_parsing.py`:
  - [ ] Parse each fixture, assert expected metric ranges
  - [ ] Unsupported file type → `parsed=False`
  - [ ] Corrupted/empty file → error recorded in `parse_errors`

---

## Phase 4: Cache Layer (`src/docscout/cache.py`)

- [ ] Implement `Cache` class:
  - [ ] `__init__(cache_dir: Path)` — create dir if needed, open/create SQLite DB, run `CREATE TABLE IF NOT EXISTS`
  - [ ] `get(path: Path) -> FileResult | None` — lookup by absolute path, validate mtime + size, return `None` if stale or missing
  - [ ] `put(path: Path, result: FileResult) -> None` — upsert with current mtime, size, serialized JSON, ISO timestamp
  - [ ] `invalidate(path: Path) -> None` — delete entry
  - [ ] `clear() -> None` — drop all entries
  - [ ] Handle cache corruption: catch SQLite errors, delete and recreate DB, log warning to stderr
- [ ] Determine default cache dir using `XDG_CACHE_HOME` env var with `~/.cache/docscout/` fallback
- [ ] Write `tests/test_cache.py`:
  - [ ] `put` + `get` round-trip returns same `FileResult`
  - [ ] Stale entry (modified mtime) returns `None`
  - [ ] `clear()` empties the cache
  - [ ] Verify `--no-cache` skip-read behavior (tested at integration level or via mock)

---

## Phase 5: Directory Scanner (`src/docscout/scanner.py`)

- [ ] Implement `discover_files(root: Path) -> list[Path]`:
  - [ ] `rglob("*")`, filter to files only
  - [ ] Skip hidden files/directories (name starts with `.`)
- [ ] Implement `scan_directory(root: Path, cache: Cache | None, no_cache: bool) -> DirectorySummary`:
  - [ ] Discover and categorize all files
  - [ ] Check cache for each supported file
  - [ ] Parse uncached supported files (with `rich.progress` on stderr)
  - [ ] Cache newly parsed results
  - [ ] Build `FiletypeCount` distribution list
  - [ ] Compute aggregate metrics and averages
  - [ ] Assemble and return `DirectorySummary`
- [ ] Progress bar: show only when output is a terminal and there are files to parse
- [ ] Write `tests/test_scanner.py`:
  - [ ] Discovers files recursively in a tmp directory
  - [ ] Skips hidden files and directories
  - [ ] Correctly categorizes file types
  - [ ] Aggregates metrics correctly in `DirectorySummary`

---

## Phase 6: Rich Display (`src/docscout/display.py`)

- [ ] Implement `render_file_result(result: FileResult)`:
  - [ ] Rich panel with file name as title
  - [ ] Key-value rows: file size (human-readable), pages, words, chars, tables, figures, headings (with max depth), sections
  - [ ] Warnings/errors displayed below panel if present
- [ ] Implement `render_directory_summary(summary: DirectorySummary)`:
  - [ ] Summary panel: pages, words, tables, figures, avg pages/doc, avg words/doc
  - [ ] Filetype distribution table: type, count, category, % of total
  - [ ] Warning line if any files had errors
- [ ] Implement `render_directory_detail(summary: DirectorySummary)`:
  - [ ] Table with one row per analyzed file: file path, type, pages, words, tables, figures, errors
  - [ ] `—` for metrics on files that failed to parse
- [ ] All Rich output goes to `Console(stderr=False)` (stdout); progress goes to stderr

---

## Phase 7: CLI (`src/docscout/cli.py`)

- [ ] Create Typer app with single command (default, no subcommands)
- [ ] Define positional argument: `path` (file or directory)
- [ ] Define options: `--format` (rich|json), `--detail`, `--cache-dir`, `--no-cache`, `--version`
- [ ] Implement main logic:
  - [ ] `--version` → print version, exit
  - [ ] Resolve path, validate exists and is readable → exit 1 with stderr message if not
  - [ ] **File mode:**
    - [ ] Check if supported type → exit 1 if not, listing supported types
    - [ ] Parse file via `parse_file()`
    - [ ] Output: `--format json` → print `FileResult` JSON; else render Rich panel
  - [ ] **Directory mode:**
    - [ ] Initialize cache (respecting `--cache-dir` / `--no-cache`)
    - [ ] Call `scan_directory()`
    - [ ] Output: `--format json` → print `DirectorySummary` JSON; `--detail` → render detail table; else render aggregate summary
  - [ ] Set exit code 2 if any files had parse errors (directory mode)
- [ ] Write `tests/test_cli.py` (using Typer `CliRunner`):
  - [ ] Single file + `--format rich` → output contains expected metrics
  - [ ] Single file + `--format json` → valid JSON matching `FileResult` schema
  - [ ] Directory default → aggregate summary output
  - [ ] Directory + `--detail` → per-file table
  - [ ] Directory + `--format json` → valid JSON matching `DirectorySummary` schema
  - [ ] Nonexistent path → exit code 1
  - [ ] `--version` → prints version string

---

## Phase 8: Final Integration & Polish

- [ ] Run full test suite, fix any failures
- [ ] Run `ruff check` and `ruff format` across codebase, fix any issues
- [ ] Manual smoke test: run `docscout` against a real directory with mixed file types
- [ ] Verify `--no-cache` forces re-parse
- [ ] Verify JSON output is valid and pipe-friendly (no Rich markup leaking)
- [ ] Verify progress bar appears on stderr only when appropriate
- [ ] Confirm exit codes: 0 on success, 1 on input error, 2 on partial parse failures

---

## Dependency Install Order

For reference, all runtime deps must be installed before Phase 3:

```
pip install docling>=2.0 typer>=0.9 rich>=13.0 pydantic>=2.0
```

Dev deps (needed from the start for testing):

```
pip install pytest>=8.0 ruff>=0.4
```

---

## Notes

- **Build order rationale**: Models first (no deps on other modules), then categories (pure mapping), then parsing (depends on models + categories + docling), then cache (depends on models), then scanner (depends on everything), then display (depends on models), then CLI (wires it all together).
- **Test fixtures**: Must be created before Phase 3 tests can run. Keep them small (< 100 KB each) to avoid bloating the repo.
- **Post-MVP items** (not in this plan): `--no-recurse`, language detection, Python library API, additional formats, filtering, parallel parsing, cache management CLI.
