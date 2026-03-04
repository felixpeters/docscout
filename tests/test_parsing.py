"""Tests for document parsing layer."""

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from docscout.models import FileResult
from docscout.parsing import parse_file


def _setup_docling_mock():
    """Set up mock docling modules so imports succeed."""
    mock_converter_cls = MagicMock()
    mock_module = ModuleType("docling")
    mock_dc_module = ModuleType("docling.document_converter")
    mock_dc_module.DocumentConverter = mock_converter_cls
    mock_dc_module.PdfFormatOption = MagicMock()
    mock_dm_module = ModuleType("docling.datamodel")
    mock_doc_module = ModuleType("docling.datamodel.document")
    mock_doc_module.DocItem = MagicMock
    mock_bm_module = ModuleType("docling.datamodel.base_models")
    mock_bm_module.InputFormat = MagicMock()
    mock_po_module = ModuleType("docling.datamodel.pipeline_options")
    mock_po_module.PdfPipelineOptions = MagicMock()

    sys.modules["docling"] = mock_module
    sys.modules["docling.document_converter"] = mock_dc_module
    sys.modules["docling.datamodel"] = mock_dm_module
    sys.modules["docling.datamodel.document"] = mock_doc_module
    sys.modules["docling.datamodel.base_models"] = mock_bm_module
    sys.modules["docling.datamodel.pipeline_options"] = mock_po_module

    return mock_converter_cls


def _cleanup_docling_mock():
    for key in list(sys.modules):
        if key.startswith("docling"):
            del sys.modules[key]


@pytest.fixture
def sample_pdf(tmp_path):
    f = tmp_path / "sample.pdf"
    f.write_bytes(b"%PDF-1.4 fake pdf content")
    return f


@pytest.fixture
def sample_txt(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("Hello world")
    return f


class TestParseFile:
    def test_unsupported_file_returns_unparsed(self, sample_txt):
        result = parse_file(sample_txt)
        assert isinstance(result, FileResult)
        assert result.parsed is False
        assert result.file_type == "txt"
        assert result.file_category == "documents"
        assert result.page_count is None

    def test_unsupported_unknown_ext(self, tmp_path):
        f = tmp_path / "data.xyz"
        f.write_bytes(b"some data")
        result = parse_file(f)
        assert result.parsed is False
        assert result.file_category == "other"

    def test_file_metadata(self, sample_pdf):
        mock_converter_cls = _setup_docling_mock()
        try:
            mock_doc = MagicMock()
            mock_doc.export_to_markdown.return_value = "Hello world test"
            mock_doc.pages = {"1": MagicMock()}
            mock_doc.iterate_items.return_value = []

            mock_result = MagicMock()
            mock_result.document = mock_doc
            mock_converter_cls.return_value.convert.return_value = mock_result

            result = parse_file(sample_pdf)
            assert result.file_name == "sample.pdf"
            assert result.file_type == "pdf"
            assert result.file_size_bytes > 0
            assert result.parsed is True
        finally:
            _cleanup_docling_mock()

    def test_word_and_char_count(self, sample_pdf):
        mock_converter_cls = _setup_docling_mock()
        try:
            mock_doc = MagicMock()
            mock_doc.export_to_markdown.return_value = "word1 word2 word3"
            mock_doc.pages = {}
            mock_doc.iterate_items.return_value = []

            mock_result = MagicMock()
            mock_result.document = mock_doc
            mock_converter_cls.return_value.convert.return_value = mock_result

            result = parse_file(sample_pdf)
            assert result.word_count == 3
            assert result.char_count == len("word1 word2 word3")
        finally:
            _cleanup_docling_mock()

    def test_parse_error_is_captured(self, sample_pdf):
        mock_converter_cls = _setup_docling_mock()
        try:
            mock_converter_cls.return_value.convert.side_effect = RuntimeError("Parse failed")

            result = parse_file(sample_pdf)
            assert result.parsed is False
            assert len(result.parse_errors) == 1
            assert "Parse failed" in result.parse_errors[0]
            assert result.parse_duration_sec is not None
        finally:
            _cleanup_docling_mock()

    def test_parse_duration_measured(self, sample_pdf):
        mock_converter_cls = _setup_docling_mock()
        try:
            mock_doc = MagicMock()
            mock_doc.export_to_markdown.return_value = "text"
            mock_doc.pages = {}
            mock_doc.iterate_items.return_value = []

            mock_result = MagicMock()
            mock_result.document = mock_doc
            mock_converter_cls.return_value.convert.return_value = mock_result

            result = parse_file(sample_pdf)
            assert result.parse_duration_sec is not None
            assert result.parse_duration_sec >= 0
        finally:
            _cleanup_docling_mock()

    def test_on_page_done_callback(self, sample_pdf):
        mock_converter_cls = _setup_docling_mock()
        try:
            mock_doc = MagicMock()
            mock_doc.export_to_markdown.return_value = "hello world"
            mock_doc.pages = {"1": MagicMock(), "2": MagicMock()}

            # Create mock items so callback fires
            mock_item1 = MagicMock()
            mock_item1.label = None
            mock_item2 = MagicMock()
            mock_item2.label = None
            mock_doc.iterate_items.return_value = [
                (mock_item1, 0),
                (mock_item2, 0),
            ]

            mock_result = MagicMock()
            mock_result.document = mock_doc
            mock_converter_cls.return_value.convert.return_value = mock_result

            pages_seen = []

            def on_page(current, total):
                pages_seen.append((current, total))

            result = parse_file(sample_pdf, on_page_done=on_page)
            assert result.parsed is True
            assert result.page_count == 2
            # All pages should be signaled
            assert len(pages_seen) == 2
            assert pages_seen[-1] == (2, 2)
        finally:
            _cleanup_docling_mock()

    def test_save_images_configures_pipeline(self, sample_pdf, tmp_path):
        mock_converter_cls = _setup_docling_mock()
        try:
            mock_doc = MagicMock()
            mock_doc.export_to_markdown.return_value = "text"
            mock_doc.pages = {}
            mock_doc.iterate_items.return_value = []

            mock_result = MagicMock()
            mock_result.document = mock_doc
            mock_converter_cls.return_value.convert.return_value = mock_result

            images_dir = tmp_path / "images"
            result = parse_file(sample_pdf, save_images=images_dir)
            assert result.parsed is True
            # DocumentConverter should have been called with format_options
            call_kwargs = mock_converter_cls.call_args
            assert "format_options" in call_kwargs.kwargs
            assert len(call_kwargs.kwargs["format_options"]) > 0
        finally:
            _cleanup_docling_mock()
