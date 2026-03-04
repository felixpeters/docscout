"""Tests for file category mapping."""

from docscout.categories import (
    SUPPORTED_EXTENSIONS,
    get_category,
    is_supported,
)


class TestSupportedExtensions:
    def test_contains_pdf(self):
        assert "pdf" in SUPPORTED_EXTENSIONS

    def test_contains_docx(self):
        assert "docx" in SUPPORTED_EXTENSIONS

    def test_contains_pptx(self):
        assert "pptx" in SUPPORTED_EXTENSIONS

    def test_exactly_three(self):
        assert len(SUPPORTED_EXTENSIONS) == 3


class TestGetCategory:
    def test_supported_types_are_documents(self):
        assert get_category("pdf") == "documents"
        assert get_category("docx") == "documents"
        assert get_category("pptx") == "documents"

    def test_detection_only_documents(self):
        assert get_category("doc") == "documents"
        assert get_category("txt") == "documents"
        assert get_category("md") == "documents"
        assert get_category("html") == "documents"

    def test_spreadsheets(self):
        assert get_category("csv") == "spreadsheets"
        assert get_category("xlsx") == "spreadsheets"
        assert get_category("xls") == "spreadsheets"

    def test_images(self):
        assert get_category("png") == "images"
        assert get_category("jpg") == "images"
        assert get_category("jpeg") == "images"

    def test_tabular_data(self):
        assert get_category("parquet") == "tabular data"
        assert get_category("feather") == "tabular data"

    def test_archives(self):
        assert get_category("zip") == "archives"
        assert get_category("tar") == "archives"

    def test_unknown_returns_other(self):
        assert get_category("xyz") == "other"
        assert get_category("foo") == "other"

    def test_case_insensitive(self):
        assert get_category("PDF") == "documents"
        assert get_category("Docx") == "documents"

    def test_strips_leading_dot(self):
        assert get_category(".pdf") == "documents"
        assert get_category(".csv") == "spreadsheets"


class TestIsSupported:
    def test_supported(self):
        assert is_supported("pdf") is True
        assert is_supported("docx") is True
        assert is_supported("pptx") is True

    def test_not_supported(self):
        assert is_supported("txt") is False
        assert is_supported("csv") is False
        assert is_supported("png") is False
        assert is_supported("xyz") is False

    def test_case_insensitive(self):
        assert is_supported("PDF") is True
        assert is_supported("DOCX") is True

    def test_strips_leading_dot(self):
        assert is_supported(".pdf") is True
        assert is_supported(".txt") is False
