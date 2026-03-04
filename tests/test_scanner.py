"""Tests for directory scanning and orchestration."""

from pathlib import Path
from unittest.mock import patch

import pytest

from docscout.scanner import discover_files, scan_directory


@pytest.fixture
def sample_dir(tmp_path):
    """Create a sample directory structure for testing."""
    # Regular files
    (tmp_path / "doc1.pdf").write_bytes(b"pdf content 1")
    (tmp_path / "doc2.docx").write_bytes(b"docx content")
    (tmp_path / "image.png").write_bytes(b"png data")
    (tmp_path / "data.csv").write_bytes(b"a,b,c\n1,2,3")

    # Nested directory
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "nested.pdf").write_bytes(b"nested pdf")

    # Hidden files and directories
    (tmp_path / ".hidden_file").write_bytes(b"hidden")
    hidden_dir = tmp_path / ".hidden_dir"
    hidden_dir.mkdir()
    (hidden_dir / "secret.pdf").write_bytes(b"secret")

    return tmp_path


class TestDiscoverFiles:
    def test_finds_all_regular_files(self, sample_dir):
        files = discover_files(sample_dir)
        names = {f.name for f in files}
        assert "doc1.pdf" in names
        assert "doc2.docx" in names
        assert "image.png" in names
        assert "data.csv" in names

    def test_finds_nested_files(self, sample_dir):
        files = discover_files(sample_dir)
        names = {f.name for f in files}
        assert "nested.pdf" in names

    def test_skips_hidden_files(self, sample_dir):
        files = discover_files(sample_dir)
        names = {f.name for f in files}
        assert ".hidden_file" not in names

    def test_skips_hidden_directories(self, sample_dir):
        files = discover_files(sample_dir)
        names = {f.name for f in files}
        assert "secret.pdf" not in names

    def test_empty_directory(self, tmp_path):
        files = discover_files(tmp_path)
        assert files == []

    def test_returns_paths(self, sample_dir):
        files = discover_files(sample_dir)
        assert all(isinstance(f, Path) for f in files)
        assert all(f.is_file() for f in files)


class TestScanDirectory:
    def test_counts_all_files(self, sample_dir):
        with patch("docscout.scanner.parse_file") as mock_parse:
            from docscout.models import FileResult

            mock_parse.return_value = FileResult(
                file_path="test.pdf",
                file_name="test.pdf",
                file_size_bytes=100,
                file_type="pdf",
                file_category="documents",
                parsed=True,
                page_count=1,
                word_count=10,
                char_count=50,
                table_count=0,
                figure_count=0,
                heading_count=0,
                section_count=0,
                parse_duration_sec=0.1,
            )
            summary = scan_directory(sample_dir, cache=None, no_cache=True)
            assert summary.total_files == 5  # 4 root + 1 nested (excludes hidden)

    def test_filetype_distribution(self, sample_dir):
        with patch("docscout.scanner.parse_file") as mock_parse:
            from docscout.models import FileResult

            mock_parse.return_value = FileResult(
                file_path="test.pdf",
                file_name="test.pdf",
                file_size_bytes=100,
                file_type="pdf",
                file_category="documents",
                parsed=True,
                page_count=1,
                word_count=10,
                char_count=50,
                table_count=0,
                figure_count=0,
                heading_count=0,
                section_count=0,
                parse_duration_sec=0.1,
            )
            summary = scan_directory(sample_dir, cache=None, no_cache=True)
            types = {ft.file_type for ft in summary.filetype_distribution}
            assert "pdf" in types
            assert "docx" in types
            assert "png" in types
            assert "csv" in types

    def test_aggregate_metrics(self, sample_dir):
        call_count = 0

        def mock_parse_fn(path, **kwargs):
            nonlocal call_count
            call_count += 1
            from docscout.models import FileResult

            return FileResult(
                file_path=str(path),
                file_name=path.name,
                file_size_bytes=100,
                file_type=path.suffix.lstrip("."),
                file_category="documents",
                parsed=True,
                page_count=10,
                word_count=500,
                char_count=3000,
                table_count=2,
                figure_count=1,
                heading_count=3,
                section_count=3,
                parse_duration_sec=0.1,
            )

        with patch("docscout.scanner.parse_file", side_effect=mock_parse_fn):
            summary = scan_directory(sample_dir, cache=None, no_cache=True)
            # 2 pdf + 1 docx = 3 supported files parsed
            assert summary.analyzed_files == 3
            assert summary.total_pages == 30  # 10 * 3
            assert summary.total_words == 1500  # 500 * 3

    def test_empty_directory(self, tmp_path):
        summary = scan_directory(tmp_path, cache=None, no_cache=True)
        assert summary.total_files == 0
        assert summary.analyzed_files == 0
        assert summary.filetype_distribution == []
