"""Tests for docscout Pydantic data models."""

import json

from docscout.models import DirectorySummary, FileResult, FiletypeCount


class TestFiletypeCount:
    def test_creation(self):
        ftc = FiletypeCount(file_type="pdf", category="documents", count=10, percentage=50.0)
        assert ftc.file_type == "pdf"
        assert ftc.category == "documents"
        assert ftc.count == 10
        assert ftc.percentage == 50.0

    def test_json_round_trip(self):
        ftc = FiletypeCount(file_type="docx", category="documents", count=5, percentage=25.0)
        json_str = ftc.model_dump_json()
        restored = FiletypeCount.model_validate_json(json_str)
        assert restored == ftc


class TestFileResult:
    def test_required_fields(self):
        result = FileResult(
            file_path="docs/report.pdf",
            file_name="report.pdf",
            file_size_bytes=1024,
            file_type="pdf",
            file_category="documents",
        )
        assert result.file_path == "docs/report.pdf"
        assert result.file_name == "report.pdf"
        assert result.file_size_bytes == 1024
        assert result.file_type == "pdf"
        assert result.file_category == "documents"

    def test_default_values(self):
        result = FileResult(
            file_path="test.pdf",
            file_name="test.pdf",
            file_size_bytes=512,
            file_type="pdf",
            file_category="documents",
        )
        assert result.page_count is None
        assert result.word_count is None
        assert result.char_count is None
        assert result.table_count is None
        assert result.figure_count is None
        assert result.heading_count is None
        assert result.heading_max_depth is None
        assert result.section_count is None
        assert result.parse_errors == []
        assert result.parse_warnings == []
        assert result.parsed is False
        assert result.parse_duration_sec is None

    def test_with_content_metrics(self):
        result = FileResult(
            file_path="report.pdf",
            file_name="report.pdf",
            file_size_bytes=2048,
            file_type="pdf",
            file_category="documents",
            page_count=10,
            word_count=5000,
            char_count=30000,
            table_count=3,
            figure_count=5,
            heading_count=12,
            heading_max_depth=3,
            section_count=8,
            parsed=True,
            parse_duration_sec=1.5,
        )
        assert result.page_count == 10
        assert result.word_count == 5000
        assert result.parsed is True
        assert result.parse_duration_sec == 1.5

    def test_with_errors(self):
        result = FileResult(
            file_path="broken.pdf",
            file_name="broken.pdf",
            file_size_bytes=100,
            file_type="pdf",
            file_category="documents",
            parsed=False,
            parse_errors=["Failed to parse document"],
            parse_warnings=["Low quality scan detected"],
        )
        assert result.parsed is False
        assert len(result.parse_errors) == 1
        assert "Failed to parse" in result.parse_errors[0]
        assert len(result.parse_warnings) == 1

    def test_json_round_trip(self):
        result = FileResult(
            file_path="docs/report.pdf",
            file_name="report.pdf",
            file_size_bytes=2048,
            file_type="pdf",
            file_category="documents",
            page_count=10,
            word_count=5000,
            char_count=30000,
            table_count=3,
            figure_count=5,
            heading_count=12,
            heading_max_depth=3,
            section_count=8,
            parsed=True,
            parse_duration_sec=1.5,
            parse_errors=[],
            parse_warnings=["Minor issue"],
        )
        json_str = result.model_dump_json()
        restored = FileResult.model_validate_json(json_str)
        assert restored == result

    def test_json_output_structure(self):
        result = FileResult(
            file_path="test.pdf",
            file_name="test.pdf",
            file_size_bytes=1024,
            file_type="pdf",
            file_category="documents",
            page_count=5,
            parsed=True,
        )
        data = json.loads(result.model_dump_json())
        assert "file_path" in data
        assert "page_count" in data
        assert data["page_count"] == 5
        assert data["word_count"] is None
        assert data["parsed"] is True


class TestDirectorySummary:
    def _make_file_result(self, name: str, **kwargs) -> FileResult:
        defaults = {
            "file_path": f"docs/{name}",
            "file_name": name,
            "file_size_bytes": 1024,
            "file_type": name.rsplit(".", 1)[-1],
            "file_category": "documents",
        }
        defaults.update(kwargs)
        return FileResult(**defaults)

    def test_creation(self):
        summary = DirectorySummary(
            root_path="./docs",
            total_files=10,
            analyzed_files=5,
            skipped_files=5,
            total_pages=100,
            total_words=50000,
            total_chars=300000,
            total_tables=20,
            total_figures=15,
            total_headings=50,
            total_sections=30,
            avg_pages=20.0,
            avg_words=10000.0,
            avg_tables=4.0,
            avg_figures=3.0,
            filetype_distribution=[
                FiletypeCount(file_type="pdf", category="documents", count=5, percentage=50.0),
                FiletypeCount(file_type="png", category="images", count=5, percentage=50.0),
            ],
            files_with_errors=0,
            file_results=[],
        )
        assert summary.total_files == 10
        assert summary.analyzed_files == 5
        assert summary.skipped_files == 5
        assert len(summary.filetype_distribution) == 2

    def test_with_file_results(self):
        results = [
            self._make_file_result("a.pdf", page_count=10, word_count=3000, parsed=True),
            self._make_file_result("b.pdf", page_count=20, word_count=7000, parsed=True),
        ]
        summary = DirectorySummary(
            root_path="./docs",
            total_files=2,
            analyzed_files=2,
            skipped_files=0,
            total_pages=30,
            total_words=10000,
            total_chars=60000,
            total_tables=0,
            total_figures=0,
            total_headings=0,
            total_sections=0,
            avg_pages=15.0,
            avg_words=5000.0,
            avg_tables=0.0,
            avg_figures=0.0,
            filetype_distribution=[
                FiletypeCount(file_type="pdf", category="documents", count=2, percentage=100.0),
            ],
            files_with_errors=0,
            file_results=results,
        )
        assert len(summary.file_results) == 2
        assert summary.file_results[0].file_name == "a.pdf"
        assert summary.avg_pages == 15.0

    def test_json_round_trip(self):
        results = [
            self._make_file_result("report.pdf", page_count=5, parsed=True),
        ]
        summary = DirectorySummary(
            root_path="./docs",
            total_files=3,
            analyzed_files=1,
            skipped_files=2,
            total_pages=5,
            total_words=2000,
            total_chars=12000,
            total_tables=1,
            total_figures=0,
            total_headings=3,
            total_sections=2,
            avg_pages=5.0,
            avg_words=2000.0,
            avg_tables=1.0,
            avg_figures=0.0,
            filetype_distribution=[
                FiletypeCount(file_type="pdf", category="documents", count=1, percentage=33.3),
                FiletypeCount(file_type="png", category="images", count=2, percentage=66.7),
            ],
            files_with_errors=0,
            file_results=results,
        )
        json_str = summary.model_dump_json()
        restored = DirectorySummary.model_validate_json(json_str)
        assert restored == summary

    def test_json_output_structure(self):
        summary = DirectorySummary(
            root_path="./test",
            total_files=0,
            analyzed_files=0,
            skipped_files=0,
            total_pages=0,
            total_words=0,
            total_chars=0,
            total_tables=0,
            total_figures=0,
            total_headings=0,
            total_sections=0,
            avg_pages=0.0,
            avg_words=0.0,
            avg_tables=0.0,
            avg_figures=0.0,
            filetype_distribution=[],
            files_with_errors=0,
            file_results=[],
        )
        data = json.loads(summary.model_dump_json())
        assert "root_path" in data
        assert "filetype_distribution" in data
        assert "file_results" in data
        assert isinstance(data["filetype_distribution"], list)
        assert isinstance(data["file_results"], list)

    def test_with_errors(self):
        results = [
            self._make_file_result("broken.pdf", parsed=False, parse_errors=["Parse failed"]),
        ]
        summary = DirectorySummary(
            root_path="./docs",
            total_files=1,
            analyzed_files=0,
            skipped_files=0,
            total_pages=0,
            total_words=0,
            total_chars=0,
            total_tables=0,
            total_figures=0,
            total_headings=0,
            total_sections=0,
            avg_pages=0.0,
            avg_words=0.0,
            avg_tables=0.0,
            avg_figures=0.0,
            filetype_distribution=[
                FiletypeCount(file_type="pdf", category="documents", count=1, percentage=100.0),
            ],
            files_with_errors=1,
            file_results=results,
        )
        assert summary.files_with_errors == 1
        assert summary.file_results[0].parsed is False
