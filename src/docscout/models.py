"""Pydantic data models for docscout."""

from pydantic import BaseModel


class MetricStats(BaseModel):
    """Descriptive statistics for a single metric across analyzed files."""

    total: int
    avg: float
    std: float
    median: float
    min: int
    min_file: str  # Relative path of the file with the minimum value
    max: int
    max_file: str  # Relative path of the file with the maximum value


class FiletypeCount(BaseModel):
    """Distribution entry for a single file type."""

    file_type: str  # Extension (e.g. "pdf")
    category: str  # Category (e.g. "documents")
    count: int
    percentage: float  # Percentage of total_files


class FileResult(BaseModel):
    """Per-file parsing result. This is the unit of caching."""

    file_path: str  # Relative path from scan root (or absolute for single-file mode)
    file_name: str  # Basename
    file_size_bytes: int  # Size in bytes
    file_type: str  # Extension, lowercase, without dot (e.g. "pdf")
    file_category: str  # Category from the mapping (e.g. "documents")

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
    parsed: bool = False  # True if detailed analysis was performed
    parse_duration_sec: float | None = None


class DirectorySummary(BaseModel):
    """Aggregate stats for directory mode."""

    root_path: str
    total_files: int
    analyzed_files: int  # Files with detailed analysis
    skipped_files: int  # Files detected but not analyzed

    # Aggregate content metrics (across analyzed files only)
    total_chars: int
    total_headings: int
    total_sections: int

    # Per-metric descriptive statistics (across analyzed files only)
    pages_stats: MetricStats
    words_stats: MetricStats
    tables_stats: MetricStats
    figures_stats: MetricStats

    # Filetype distribution
    filetype_distribution: list[FiletypeCount]

    # Errors
    files_with_errors: int

    # All per-file results (included in JSON output, used for --detail)
    file_results: list[FileResult]
