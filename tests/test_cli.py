"""Tests for the CLI interface."""

import json
from unittest.mock import patch

from typer.testing import CliRunner

from docscout.cli import app
from docscout.models import DirectorySummary, FileResult

runner = CliRunner()


class TestVersion:
    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "docscout" in result.output
        assert "0.1.0" in result.output


class TestNonexistentPath:
    def test_missing_path_exits_1(self):
        result = runner.invoke(app, ["/nonexistent/path/nowhere"])
        assert result.exit_code == 1


class TestSingleFile:
    @patch("docscout.cli.parse_file")
    @patch("docscout.cli.render_file_result")
    def test_rich_output(self, mock_render, mock_parse, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"fake pdf")
        mock_parse.return_value = FileResult(
            file_path=str(f),
            file_name="test.pdf",
            file_size_bytes=8,
            file_type="pdf",
            file_category="documents",
            parsed=True,
            page_count=5,
            word_count=100,
            char_count=600,
        )
        result = runner.invoke(app, [str(f)])
        assert result.exit_code == 0
        mock_render.assert_called_once()

    @patch("docscout.cli.parse_file")
    def test_json_output(self, mock_parse, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"fake pdf")
        mock_parse.return_value = FileResult(
            file_path=str(f),
            file_name="test.pdf",
            file_size_bytes=8,
            file_type="pdf",
            file_category="documents",
            parsed=True,
            page_count=5,
        )
        result = runner.invoke(app, [str(f), "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["file_name"] == "test.pdf"
        assert data["page_count"] == 5

    def test_unsupported_file_exits_1(self, tmp_path):
        f = tmp_path / "notes.txt"
        f.write_text("hello")
        result = runner.invoke(app, [str(f)])
        assert result.exit_code == 1

    @patch("docscout.cli.parse_file")
    @patch("docscout.cli.render_file_result")
    def test_verbose_flag_accepted(self, mock_render, mock_parse, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"fake pdf")
        mock_parse.return_value = FileResult(
            file_path=str(f),
            file_name="test.pdf",
            file_size_bytes=8,
            file_type="pdf",
            file_category="documents",
            parsed=True,
            page_count=1,
        )
        result = runner.invoke(app, [str(f), "--verbose"])
        assert result.exit_code == 0

    @patch("docscout.cli.parse_file")
    @patch("docscout.cli.render_file_result")
    def test_verbose_short_flag(self, mock_render, mock_parse, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"fake pdf")
        mock_parse.return_value = FileResult(
            file_path=str(f),
            file_name="test.pdf",
            file_size_bytes=8,
            file_type="pdf",
            file_category="documents",
            parsed=True,
            page_count=1,
        )
        result = runner.invoke(app, [str(f), "-v"])
        assert result.exit_code == 0

    @patch("docscout.cli.parse_file")
    @patch("docscout.cli.render_file_result")
    def test_save_images_flag_accepted(self, mock_render, mock_parse, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"fake pdf")
        images_dir = tmp_path / "images"
        mock_parse.return_value = FileResult(
            file_path=str(f),
            file_name="test.pdf",
            file_size_bytes=8,
            file_type="pdf",
            file_category="documents",
            parsed=True,
            page_count=1,
        )
        result = runner.invoke(app, [str(f), "--save-images", str(images_dir)])
        assert result.exit_code == 0
        # Verify save_images was passed to parse_file
        mock_parse.assert_called_once()
        call_kwargs = mock_parse.call_args
        assert call_kwargs.kwargs.get("save_images") == images_dir


class TestDirectory:
    def _mock_summary(self, root, files_with_errors=0):
        return DirectorySummary(
            root_path=str(root),
            total_files=2,
            analyzed_files=2,
            skipped_files=0,
            total_pages=10,
            total_words=500,
            total_chars=3000,
            total_tables=1,
            total_figures=0,
            total_headings=3,
            total_sections=2,
            avg_pages=5.0,
            avg_words=250.0,
            avg_tables=0.5,
            avg_figures=0.0,
            filetype_distribution=[],
            files_with_errors=files_with_errors,
            file_results=[],
        )

    @patch("docscout.cli.scan_directory")
    @patch("docscout.cli.render_directory_summary")
    @patch("docscout.cli.Cache")
    def test_rich_summary(self, mock_cache_cls, mock_render, mock_scan, tmp_path):
        mock_scan.return_value = self._mock_summary(tmp_path)
        result = runner.invoke(app, [str(tmp_path)])
        assert result.exit_code == 0
        mock_render.assert_called_once()

    @patch("docscout.cli.scan_directory")
    @patch("docscout.cli.Cache")
    def test_json_output(self, mock_cache_cls, mock_scan, tmp_path):
        mock_scan.return_value = self._mock_summary(tmp_path)
        result = runner.invoke(app, [str(tmp_path), "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_files"] == 2

    @patch("docscout.cli.scan_directory")
    @patch("docscout.cli.render_directory_detail")
    @patch("docscout.cli.Cache")
    def test_detail_flag(self, mock_cache_cls, mock_render, mock_scan, tmp_path):
        mock_scan.return_value = self._mock_summary(tmp_path)
        result = runner.invoke(app, [str(tmp_path), "--detail"])
        assert result.exit_code == 0
        mock_render.assert_called_once()

    @patch("docscout.cli.scan_directory")
    @patch("docscout.cli.Cache")
    def test_exit_code_2_on_errors(self, mock_cache_cls, mock_scan, tmp_path):
        mock_scan.return_value = self._mock_summary(tmp_path, files_with_errors=1)
        result = runner.invoke(app, [str(tmp_path)])
        assert result.exit_code == 2

    @patch("docscout.cli.scan_directory")
    @patch("docscout.cli.render_directory_summary")
    @patch("docscout.cli.Cache")
    def test_verbose_flag_with_directory(self, mock_cache_cls, mock_render, mock_scan, tmp_path):
        mock_scan.return_value = self._mock_summary(tmp_path)
        result = runner.invoke(app, [str(tmp_path), "--verbose"])
        assert result.exit_code == 0

    @patch("docscout.cli.scan_directory")
    @patch("docscout.cli.render_directory_summary")
    @patch("docscout.cli.Cache")
    def test_save_images_passed_to_scanner(self, mock_cache_cls, mock_render, mock_scan, tmp_path):
        mock_scan.return_value = self._mock_summary(tmp_path)
        images_dir = tmp_path / "images"
        result = runner.invoke(app, [str(tmp_path), "--save-images", str(images_dir)])
        assert result.exit_code == 0
        call_kwargs = mock_scan.call_args
        assert call_kwargs.kwargs.get("save_images") == images_dir
