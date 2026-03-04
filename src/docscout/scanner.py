"""Directory scanning and orchestration for docscout."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from rich.progress import Progress

from docscout.cache import Cache
from docscout.categories import get_category, is_supported
from docscout.models import DirectorySummary, FileResult, FiletypeCount
from docscout.parsing import parse_file


def discover_files(root: Path) -> list[Path]:
    """Recursively discover all non-hidden files under root."""
    files: list[Path] = []
    for p in sorted(root.rglob("*")):
        # Skip hidden files and files inside hidden directories
        if any(part.startswith(".") for part in p.relative_to(root).parts):
            continue
        if p.is_file():
            files.append(p)
    return files


def scan_directory(
    root: Path,
    cache: Cache | None = None,
    no_cache: bool = False,
) -> DirectorySummary:
    """Scan a directory tree and return aggregate results."""
    root = root.resolve()
    all_files = discover_files(root)

    # Categorize all files
    file_results: list[FileResult] = []
    supported_files: list[Path] = []

    for f in all_files:
        ext = f.suffix.lower().lstrip(".")
        if is_supported(ext):
            supported_files.append(f)

    # Check cache and parse supported files
    to_parse: list[Path] = []
    for f in supported_files:
        if cache and not no_cache:
            cached = cache.get(f)
            if cached is not None:
                file_results.append(cached)
                continue
        to_parse.append(f)

    # Parse with progress bar (only on terminal)
    if to_parse:
        show_progress = sys.stderr.isatty()
        if show_progress:
            with Progress(transient=True) as progress:
                task = progress.add_task("Parsing documents", total=len(to_parse))
                for f in to_parse:
                    result = parse_file(f)
                    # Make path relative to root for display
                    try:
                        result.file_path = str(f.relative_to(root))
                    except ValueError:
                        pass
                    file_results.append(result)
                    if cache:
                        cache.put(f, result)
                    progress.advance(task)
        else:
            for f in to_parse:
                result = parse_file(f)
                try:
                    result.file_path = str(f.relative_to(root))
                except ValueError:
                    pass
                file_results.append(result)
                if cache:
                    cache.put(f, result)

    # Also make cached results relative
    for r in file_results:
        try:
            abs_path = Path(r.file_path)
            if abs_path.is_absolute():
                r.file_path = str(abs_path.relative_to(root))
        except ValueError:
            pass

    # Build filetype distribution across ALL files
    ext_counter: Counter[str] = Counter()
    for f in all_files:
        ext = f.suffix.lower().lstrip(".")
        if ext:
            ext_counter[ext] += 1
        else:
            ext_counter["(no extension)"] += 1

    total_files = len(all_files)
    filetype_distribution = [
        FiletypeCount(
            file_type=ext,
            category=get_category(ext),
            count=count,
            percentage=round(count / total_files * 100, 1) if total_files > 0 else 0,
        )
        for ext, count in ext_counter.most_common()
    ]

    # Aggregate metrics from parsed results
    analyzed = [r for r in file_results if r.parsed]
    files_with_errors = sum(1 for r in file_results if r.parse_errors)

    total_pages = sum(r.page_count or 0 for r in analyzed)
    total_words = sum(r.word_count or 0 for r in analyzed)
    total_chars = sum(r.char_count or 0 for r in analyzed)
    total_tables = sum(r.table_count or 0 for r in analyzed)
    total_figures = sum(r.figure_count or 0 for r in analyzed)
    total_headings = sum(r.heading_count or 0 for r in analyzed)
    total_sections = sum(r.section_count or 0 for r in analyzed)

    n = len(analyzed) or 1  # avoid division by zero

    return DirectorySummary(
        root_path=str(root),
        total_files=total_files,
        analyzed_files=len(analyzed),
        skipped_files=total_files - len(analyzed),
        total_pages=total_pages,
        total_words=total_words,
        total_chars=total_chars,
        total_tables=total_tables,
        total_figures=total_figures,
        total_headings=total_headings,
        total_sections=total_sections,
        avg_pages=round(total_pages / n, 1),
        avg_words=round(total_words / n, 1),
        avg_tables=round(total_tables / n, 1),
        avg_figures=round(total_figures / n, 1),
        filetype_distribution=filetype_distribution,
        files_with_errors=files_with_errors,
        file_results=file_results,
    )
