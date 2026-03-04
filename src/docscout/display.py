"""Rich terminal rendering for docscout."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from docscout.models import DirectorySummary, FileResult

console = Console()


def _human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable size string."""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size) < 1024:
            if unit == "B":
                return f"{int(size):,} {unit}"
            return f"{size:,.1f} {unit}"
        size /= 1024
    return f"{size:,.1f} TB"


def render_file_result(result: FileResult) -> None:
    """Render a single file result as a Rich panel."""
    lines: list[str] = []
    lines.append(f"File size:    {_human_size(result.file_size_bytes)}")

    if result.parsed:
        lines.append(
            f"Pages:        {result.page_count:,}"
            if result.page_count is not None
            else "Pages:        —"
        )
        lines.append(
            f"Words:        {result.word_count:,}"
            if result.word_count is not None
            else "Words:        —"
        )
        lines.append(
            f"Characters:   {result.char_count:,}"
            if result.char_count is not None
            else "Characters:   —"
        )
        lines.append(
            f"Tables:       {result.table_count:,}"
            if result.table_count is not None
            else "Tables:       —"
        )
        lines.append(
            f"Figures:      {result.figure_count:,}"
            if result.figure_count is not None
            else "Figures:      —"
        )

        if result.heading_count is not None and result.heading_max_depth is not None:
            lines.append(
                f"Headings:     {result.heading_count:,} (max depth: {result.heading_max_depth})"
            )
        elif result.heading_count is not None:
            lines.append(f"Headings:     {result.heading_count:,}")
        else:
            lines.append("Headings:     —")

        lines.append(
            f"Sections:     {result.section_count:,}"
            if result.section_count is not None
            else "Sections:     —"
        )

    if result.parse_errors:
        lines.append(f"Errors:       {len(result.parse_errors)}")
    if result.parse_warnings:
        lines.append(f"Warnings:     {len(result.parse_warnings)}")
    elif result.parsed and not result.parse_errors:
        lines.append("Warnings:     None")

    panel = Panel("\n".join(lines), title=result.file_name, expand=False)
    console.print(panel)

    if result.parse_errors:
        for err in result.parse_errors:
            console.print(f"  [red]Error:[/red] {err}")
    if result.parse_warnings:
        for warn in result.parse_warnings:
            console.print(f"  [yellow]Warning:[/yellow] {warn}")


def render_directory_summary(summary: DirectorySummary) -> None:
    """Render directory aggregate summary panel and filetype distribution."""
    title = f"{summary.root_path} ({summary.analyzed_files} documents)"

    lines: list[str] = []
    lines.append(f"Pages:    {summary.total_pages:,}    Tables:  {summary.total_tables:,}")
    lines.append(f"Words:    {summary.total_words:,}    Figures: {summary.total_figures:,}")
    lines.append(f"Avg pages/doc: {summary.avg_pages:.1f}")
    lines.append(f"Avg words/doc: {summary.avg_words:,.0f}")

    panel = Panel("\n".join(lines), title=title, expand=False)
    console.print(panel)

    if summary.filetype_distribution:
        table = Table(title="Filetype Distribution")
        table.add_column("Type", style="cyan")
        table.add_column("Count", justify="right")
        table.add_column("Category")
        table.add_column("% of Total", justify="right")

        for ft in summary.filetype_distribution:
            table.add_row(ft.file_type, str(ft.count), ft.category, f"{ft.percentage:.1f}%")

        console.print(table)

    if summary.files_with_errors > 0:
        console.print(
            f"\n[yellow]⚠ {summary.files_with_errors} files had parse errors. "
            f"Use --detail to see details.[/yellow]"
        )


def render_directory_detail(summary: DirectorySummary) -> None:
    """Render per-file detail table."""
    table = Table(title=f"Per-file Detail ({len(summary.file_results)} files)")
    table.add_column("File", style="cyan")
    table.add_column("Type")
    table.add_column("Pages", justify="right")
    table.add_column("Words", justify="right")
    table.add_column("Tables", justify="right")
    table.add_column("Figures", justify="right")
    table.add_column("Errors")

    for r in summary.file_results:
        if r.parsed and not r.parse_errors:
            table.add_row(
                r.file_path,
                r.file_type,
                str(r.page_count or 0),
                f"{r.word_count:,}" if r.word_count else "0",
                str(r.table_count or 0),
                str(r.figure_count or 0),
                "",
            )
        else:
            n = len(r.parse_errors)
            error_text = f"{n} error{'s' if n != 1 else ''}" if r.parse_errors else ""
            table.add_row(r.file_path, r.file_type, "—", "—", "—", "—", error_text)

    console.print(table)
