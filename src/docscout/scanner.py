"""Directory scanning and orchestration for docscout."""

from __future__ import annotations

import statistics
import sys
from collections import Counter
from pathlib import Path

from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn

from docscout.cache import Cache
from docscout.categories import get_category, is_supported
from docscout.logging import log
from docscout.models import DirectorySummary, FileResult, FiletypeCount, MetricStats
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
    save_images: Path | None = None,
) -> DirectorySummary:
    """Scan a directory tree and return aggregate results."""
    root = root.resolve()
    all_files = discover_files(root)
    log(f"Discovered {len(all_files)} files under {root}")

    # Categorize all files
    file_results: list[FileResult] = []
    supported_files: list[Path] = []

    for f in all_files:
        ext = f.suffix.lower().lstrip(".")
        if is_supported(ext):
            supported_files.append(f)

    log(f"Supported files to analyze: {len(supported_files)}")

    log(f"Supported files to parse: {len(supported_files)}")

    # Process supported files with progress (cache check + parse)
    show_progress = sys.stderr.isatty() and supported_files
    if show_progress:
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("{task.fields[status]}"),
            transient=True,
        ) as progress:
            file_task = progress.add_task(
                "Files", total=len(supported_files), status=""
            )

            for f in supported_files:
                progress.update(file_task, status=f"  {f.name}")

                # Check cache first
                if cache and not no_cache:
                    cached = cache.get(f)
                    if cached is not None:
                        log(f"Cache hit: {f.name}")
                        file_results.append(cached)
                        progress.advance(file_task)
                        continue

                # Parse uncached file
                result = parse_file(f, save_images=save_images)
                try:
                    result.file_path = str(f.relative_to(root))
                except ValueError:
                    pass
                file_results.append(result)
                if cache:
                    cache.put(f, result)
                progress.advance(file_task)
            progress.update(file_task, status="")
    else:
        for f in supported_files:
            if cache and not no_cache:
                cached = cache.get(f)
                if cached is not None:
                    log(f"Cache hit: {f.name}")
                    file_results.append(cached)
                    continue
            result = parse_file(f, save_images=save_images)
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

    total_chars = sum(r.char_count or 0 for r in analyzed)
    total_headings = sum(r.heading_count or 0 for r in analyzed)
    total_sections = sum(r.section_count or 0 for r in analyzed)

    def _compute_stats(
        results: list[FileResult], attr: str
    ) -> MetricStats:
        values = [(getattr(r, attr) or 0, r.file_path) for r in results]
        nums = [v for v, _ in values]
        total = sum(nums)
        if not nums:
            return MetricStats(
                total=0, avg=0, std=0, median=0, min=0, min_file="", max=0, max_file=""
            )
        avg = total / len(nums)
        std = statistics.stdev(nums) if len(nums) > 1 else 0.0
        med = statistics.median(nums)
        min_val, min_file = min(values, key=lambda x: x[0])
        max_val, max_file = max(values, key=lambda x: x[0])
        return MetricStats(
            total=total,
            avg=round(avg, 1),
            std=round(std, 1),
            median=round(med, 1),
            min=min_val,
            min_file=min_file,
            max=max_val,
            max_file=max_file,
        )

    return DirectorySummary(
        root_path=str(root),
        total_files=total_files,
        analyzed_files=len(analyzed),
        skipped_files=total_files - len(analyzed),
        total_chars=total_chars,
        total_headings=total_headings,
        total_sections=total_sections,
        pages_stats=_compute_stats(analyzed, "page_count"),
        words_stats=_compute_stats(analyzed, "word_count"),
        tables_stats=_compute_stats(analyzed, "table_count"),
        figures_stats=_compute_stats(analyzed, "figure_count"),
        filetype_distribution=filetype_distribution,
        files_with_errors=files_with_errors,
        file_results=file_results,
    )
