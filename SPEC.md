# docscout MVP Spec

> CLI tool for exploratory data analysis of business document databases, designed to inform agentic retrieval/search projects and test dataset curation.

## MVP Scope

The MVP delivers two core use cases:

1. **Single-file inspection** -- rich overview of one document's structure and content metrics
2. **Directory profiling** -- aggregate summary of a document tree with per-file detail available on demand, plus JSON manifest export

Deferred to post-MVP: `--no-recurse` flag, language detection, importable Python API (library interface), additional format support beyond PDF/DOCX/PPTX.

---

## CLI Interface

Entry point: `docscout` (installed via `[project.scripts]` in pyproject.toml)

### Commands

docscout uses a single-command design (no subcommands). The positional argument is a file or directory path.

```
docscout <PATH> [OPTIONS]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--format` | `rich \| json` | `rich` | Output format. `rich` for terminal tables, `json` for structured output. |
| `--detail` | `bool` | `false` | (Directory mode only) Show per-file detail table instead of aggregate summary. |
| `--cache-dir` | `Path` | XDG cache dir | Override cache location. Default: `$XDG_CACHE_HOME/docscout/` (falls back to `~/.cache/docscout/`). |
| `--no-cache` | `bool` | `false` | Bypass cache; force re-parse of all files. |
| `--version` | `bool` | -- | Print version and exit. |
| `--help` | `bool` | -- | Print help and exit. |

### Behavior by Path Type

**File path** -- Parse the single file and display its metrics.

**Directory path** -- Recursively discover all files, parse supported types (PDF, DOCX, PPTX), report on all discovered filetypes, display aggregate summary. Full per-file results are cached.

**Nonexistent / unreadable path** -- Print error message to stderr, exit code 1.

---

## Supported File Types

### Detailed analysis (parsed via Docling)

| Format | Extensions |
|--------|-----------|
| PDF | `.pdf` |
| DOCX | `.docx` |
| PPTX | `.pptx` |

### Detection only (reported in filetype distribution, not parsed for content metrics)

All other files discovered during directory scan are categorized and counted but not parsed. Categories:

| Category | Extensions (examples) |
|----------|----------------------|
| Documents | `.doc`, `.odt`, `.rtf`, `.txt`, `.md`, `.html`, `.epub` |
| Spreadsheets | `.csv`, `.xlsx`, `.xls`, `.ods`, `.tsv` |
| Images | `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.tiff`, `.bmp`, `.webp` |
| Tabular data | `.parquet`, `.feather`, `.arrow` |
| Archives | `.zip`, `.tar`, `.gz`, `.7z`, `.rar` |
| Other | Everything else |

The category mapping is defined in a single dict/enum for easy extension.

---

## Data Models (Pydantic)

### `FileResult`

Per-file parsing result. This is the unit of caching.

```python
class FileResult(BaseModel):
    file_path: str            # Relative path from scan root (or absolute for single-file mode)
    file_name: str            # Basename
    file_size_bytes: int      # Size in bytes
    file_type: str            # Extension, lowercase, without dot (e.g. "pdf")
    file_category: str        # Category from the mapping above (e.g. "documents")

    # Content metrics (None if file type not supported for detailed analysis)
    page_count: int | None = None
    word_count: int | None = None
    char_count: int | None = None
    table_count: int | None = None
    figure_count: int | None = None
    heading_count: int | None = None
    heading_max_depth: int | None = None
    section_count: int | None = None

    # Parse metadata
    parse_errors: list[str] = []
    parse_warnings: list[str] = []
    parsed: bool = False      # True if detailed analysis was performed
    parse_duration_sec: float | None = None
```

### `DirectorySummary`

Aggregate stats for directory mode.

```python
class DirectorySummary(BaseModel):
    root_path: str
    total_files: int
    analyzed_files: int       # Files with detailed analysis
    skipped_files: int        # Files detected but not analyzed

    # Aggregate content metrics (across analyzed files only)
    total_pages: int
    total_words: int
    total_chars: int
    total_tables: int
    total_figures: int
    total_headings: int
    total_sections: int

    # Per-document averages (across analyzed files only)
    avg_pages: float
    avg_words: float
    avg_tables: float
    avg_figures: float

    # Filetype distribution
    filetype_distribution: list[FiletypeCount]

    # Errors
    files_with_errors: int

    # All per-file results (included in JSON output, used for --detail)
    file_results: list[FileResult]
```

### `FiletypeCount`

```python
class FiletypeCount(BaseModel):
    file_type: str            # Extension (e.g. "pdf")
    category: str             # Category (e.g. "documents")
    count: int
    percentage: float         # Percentage of total_files
```

---

## Output Formats

### Single-file -- Rich (default)

Key-value panel:

```
╭─ report.pdf ──────────────────────────╮
│ File size:    2.4 MB                  │
│ Pages:        42                      │
│ Words:        12,450                  │
│ Characters:   68,200                  │
│ Tables:       8                       │
│ Figures:      15                      │
│ Headings:     23 (max depth: 3)      │
│ Sections:     12                      │
│ Warnings:     None                    │
╰───────────────────────────────────────╯
```

If parse errors/warnings exist, they are displayed below the panel.

### Single-file -- JSON

The `FileResult` model serialized as JSON, printed to stdout.

### Directory -- Rich aggregate (default)

Summary panel followed by filetype distribution table:

```
╭─ ./contracts/ (42 documents) ─────────╮
│ Pages:    1,284    Tables:  89        │
│ Words:    312,450  Figures: 156       │
│ Avg pages/doc: 30.6                  │
│ Avg words/doc: 7,439                 │
╰───────────────────────────────────────╯

 Filetype Distribution
┏━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Type     ┃ Count ┃ Category  ┃ % of Total ┃
┡━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ pdf      │    25 │ documents │      59.5% │
│ docx     │    12 │ documents │      28.6% │
│ pptx     │     5 │ documents │      11.9% │
└──────────┴───────┴───────────┴────────────┘
```

If there are files with parse errors, a warning line is shown below: `⚠ 3 files had parse errors. Use --detail to see details.`

### Directory -- Rich detail (`--detail`)

A table with one row per analyzed file:

```
 Per-file Detail (42 files)
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┓
┃ File                   ┃ Type ┃ Pages ┃ Words  ┃ Tables ┃ Figures ┃ Errors  ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━┩
│ contracts/a.pdf        │ pdf  │    12 │  3,400 │      2 │       4 │         │
│ contracts/b.docx       │ docx │     8 │  2,100 │      1 │       0 │         │
│ contracts/broken.pdf   │ pdf  │     — │      — │      — │       — │ 1 error │
└────────────────────────┴──────┴───────┴────────┴────────┴─────────┴─────────┘
```

Files that couldn't be parsed show `—` for metrics and the error count in the last column.

### Directory -- JSON

The `DirectorySummary` model serialized as JSON (includes the full `file_results` list), printed to stdout.

---

## Parsing Layer

### Docling Integration

The parsing layer wraps Docling to extract structured content from supported file types.

```
docscout/parsing.py
```

Key responsibilities:

1. **Accept a file path**, determine if it's a supported type
2. **Call Docling** to parse the document into its internal representation
3. **Extract metrics** from the Docling result:
   - **Page count**: From Docling's document structure
   - **Word count / char count**: From extracted text content
   - **Table count**: Count of `TableItem` elements
   - **Figure count**: Count of `PictureItem` elements
   - **Heading count + max depth**: Count of heading elements; track max heading level
   - **Section count**: Count of distinct sections
4. **Return a `FileResult`** with all metrics populated
5. **Catch and record errors**: If Docling fails, return a `FileResult` with `parsed=False` and the error in `parse_errors`

### Error Handling

- Files that fail to parse do NOT halt the directory scan
- Errors are captured in the `FileResult` and surfaced in the output
- A summary count of errored files is shown in directory mode

---

## Cache Layer

### Backend: SQLite

Location: `$XDG_CACHE_HOME/docscout/cache.db` (default), overridable via `--cache-dir`.

```
docscout/cache.py
```

### Schema

Single table:

```sql
CREATE TABLE IF NOT EXISTS file_cache (
    file_path     TEXT PRIMARY KEY,  -- Absolute path
    file_size     INTEGER NOT NULL,
    file_mtime    REAL NOT NULL,     -- os.stat st_mtime
    result_json   TEXT NOT NULL,     -- FileResult serialized as JSON
    cached_at     TEXT NOT NULL      -- ISO 8601 timestamp
);
```

### Cache Operations

| Operation | Description |
|-----------|-------------|
| `get(path)` | Look up by absolute path. Return `FileResult` if `mtime` and `size` match current file, else `None` (stale). |
| `put(path, result)` | Upsert the cache entry with current `mtime`, `size`, and serialized `FileResult`. |
| `invalidate(path)` | Delete the entry for a given path. |
| `clear()` | Drop all entries. |

### Invalidation Strategy

**mtime + file size**: On cache lookup, compare the stored `file_mtime` and `file_size` against current `os.stat()` results. If either differs, the entry is stale and the file is re-parsed.

### `--no-cache` Behavior

When `--no-cache` is passed, skip all cache reads (but still write results to cache after parsing, so subsequent runs benefit).

---

## Directory Scanning

```
docscout/scanner.py
```

### Discovery

1. Recursively walk the directory tree using `pathlib.Path.rglob("*")`
2. Filter to files only (skip directories, symlinks to directories)
3. Skip hidden files/directories (names starting with `.`)
4. Categorize each file by extension using the filetype mapping

### Processing Pipeline

1. **Discover** all files, categorize them
2. **Check cache** for each supported file
3. **Parse** uncached supported files (with progress bar via `rich.progress`)
4. **Cache** newly parsed results
5. **Aggregate** results into `DirectorySummary`

### Progress Bar

Shown on stderr (so stdout remains clean for piping):

```
Parsing documents ━━━━━━━━━━━━━━━━━━━━ 35/42 files  83%  ETA 0:00:12
```

The progress bar is displayed when:
- In directory mode
- Output is going to a terminal (not piped)
- There is at least 1 file to parse (cached files are skipped in the progress count)

---

## Project Structure

```
docscout/
├── pyproject.toml
├── README.md
├── LICENSE
├── SPEC.md
├── src/
│   └── docscout/
│       ├── __init__.py       # Package version
│       ├── cli.py            # Typer app, argument parsing, output rendering
│       ├── models.py         # Pydantic models (FileResult, DirectorySummary, FiletypeCount)
│       ├── parsing.py        # Docling wrapper, metric extraction
│       ├── cache.py          # SQLite cache layer
│       ├── scanner.py        # Directory walking, file discovery, orchestration
│       ├── categories.py     # File extension → category mapping
│       └── display.py        # Rich rendering (panels, tables)
└── tests/
    ├── conftest.py           # Shared fixtures
    ├── fixtures/             # Small test documents
    │   ├── sample.pdf        # 1-2 page PDF with text, a table, and a heading
    │   ├── sample.docx       # Simple DOCX with headings and a table
    │   └── sample.pptx       # 2-3 slide PPTX
    ├── test_parsing.py       # Tests for Docling parsing and metric extraction
    ├── test_cache.py         # Tests for SQLite cache operations
    ├── test_scanner.py       # Tests for directory discovery and orchestration
    ├── test_models.py        # Tests for Pydantic model validation/serialization
    └── test_cli.py           # CLI integration tests (invoke via CliRunner)
```

Uses `src/` layout so the installed package is always the built one, not the source tree.

---

## Dependencies

### Runtime

| Package | Purpose | Version constraint |
|---------|---------|--------------------|
| `docling` | Document parsing engine | `>=2.0` |
| `typer` | CLI framework | `>=0.9` |
| `rich` | Terminal output (tables, panels, progress bars) | `>=13.0` |
| `pydantic` | Data models, serialization | `>=2.0` |

### Development

| Package | Purpose |
|---------|---------|
| `pytest` | Test runner |
| `ruff` | Linter + formatter |

---

## pyproject.toml Key Sections

```toml
[project]
name = "docscout"
version = "0.1.0"
description = "EDA for single documents and document databases"
requires-python = ">=3.13"
dependencies = [
    "docling>=2.0",
    "typer>=0.9",
    "rich>=13.0",
    "pydantic>=2.0",
]

[project.scripts]
docscout = "docscout.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/docscout"]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "ruff>=0.4",
]

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Unsupported file type (single-file mode) | Print message listing supported types, exit code 1 |
| File not found | Print error to stderr, exit code 1 |
| Permission denied | Print error to stderr, exit code 1 |
| Docling parse failure | Record error in `FileResult`, continue (directory mode) or display error panel (single-file mode) |
| Empty directory (no files found) | Print message, exit code 0 |
| Directory with no supported files | Show filetype distribution only (no content metrics panel), exit code 0 |
| Cache corruption | Delete and recreate cache DB, log warning to stderr |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Input error (bad path, unsupported file type) |
| 2 | Partial failure (some files failed to parse in directory mode; results still shown) |

---

## Testing Strategy

### Fixtures

Small, hand-crafted documents committed to `tests/fixtures/`:

- `sample.pdf` -- 1-2 pages, contains text paragraphs, 1 table, 1 heading, 1 figure/image
- `sample.docx` -- Contains headings (2 levels), 1 table, body text
- `sample.pptx` -- 2-3 slides with titles and body text

### Test Cases

**Parsing (`test_parsing.py`)**
- Parse each fixture file, assert expected metric ranges (e.g., `page_count == 1 or 2`, `table_count == 1`)
- Unsupported file type returns `FileResult` with `parsed=False`
- Corrupted/empty file returns `FileResult` with error recorded

**Cache (`test_cache.py`)**
- Put + get returns same `FileResult`
- Stale entry (modified mtime) returns `None` on get
- `clear()` empties the cache
- `--no-cache` skips reads

**Scanner (`test_scanner.py`)**
- Discovers files recursively in a temp directory
- Skips hidden files/directories
- Correctly categorizes file types
- Aggregates metrics correctly in `DirectorySummary`

**Models (`test_models.py`)**
- `FileResult` serialization round-trips through JSON
- `DirectorySummary` computes averages correctly

**CLI (`test_cli.py`)**
- Single file with `--format rich` produces output containing expected metrics
- Single file with `--format json` produces valid JSON matching `FileResult` schema
- Directory with default flags shows aggregate summary
- Directory with `--detail` shows per-file table
- Directory with `--format json` produces valid JSON matching `DirectorySummary` schema
- Nonexistent path exits with code 1
- `--version` prints version

---

## Post-MVP Roadmap (out of scope, noted for architecture awareness)

These are NOT part of the MVP but the architecture should not preclude them:

- **`--no-recurse` flag**: Flat directory scan
- **Language detection**: Via `langdetect` or similar, added to `FileResult`
- **Python API**: Expose `parse_file()`, `scan_directory()` as public functions
- **Additional formats**: Images (dimensions, EXIF), CSV/XLSX (row/column count), HTML
- **Filtering / querying**: `--filter "tables > 5"` or similar
- **Parallel parsing**: `concurrent.futures` for multi-file parsing
- **Cache management CLI**: `docscout cache clear`, `docscout cache stats`
