"""Document parsing layer wrapping Docling."""

import time
from pathlib import Path

from docscout.categories import get_category, is_supported
from docscout.models import FileResult


def parse_file(path: Path) -> FileResult:
    """Parse a single file and return a FileResult with extracted metrics."""
    path = path.resolve()
    stat = path.stat()
    ext = path.suffix.lower().lstrip(".")
    category = get_category(ext)

    base_result = {
        "file_path": str(path),
        "file_name": path.name,
        "file_size_bytes": stat.st_size,
        "file_type": ext,
        "file_category": category,
    }

    if not is_supported(ext):
        return FileResult(**base_result, parsed=False)

    start = time.monotonic()
    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(str(path))
        doc = result.document

        # Word and char count from exported text
        text = doc.export_to_markdown()
        words = len(text.split())
        chars = len(text)

        # Page count
        page_count = 0
        if hasattr(doc, "pages") and doc.pages:
            page_count = len(doc.pages)

        # Tables and figures
        table_count = 0
        figure_count = 0
        heading_count = 0
        heading_max_depth = 0
        section_count = 0

        from docling.datamodel.document import DocItem

        for item, _level in doc.iterate_items():
            if not isinstance(item, DocItem):
                continue
            label = item.label if hasattr(item, "label") else None
            if label is not None:
                label_name = label.value if hasattr(label, "value") else str(label)
                if label_name == "table":
                    table_count += 1
                elif label_name == "picture":
                    figure_count += 1
                elif label_name == "section_header":
                    heading_count += 1
                    level = item.level if hasattr(item, "level") else 1
                    if isinstance(level, int) and level > heading_max_depth:
                        heading_max_depth = level
                elif label_name == "page_header":
                    section_count += 1

        # If no section headers found via page_header, count section_headers as sections
        if section_count == 0 and heading_count > 0:
            section_count = heading_count

        duration = time.monotonic() - start

        return FileResult(
            **base_result,
            parsed=True,
            page_count=page_count,
            word_count=words,
            char_count=chars,
            table_count=table_count,
            figure_count=figure_count,
            heading_count=heading_count,
            heading_max_depth=heading_max_depth if heading_max_depth > 0 else None,
            section_count=section_count,
            parse_duration_sec=round(duration, 3),
        )
    except Exception as exc:
        duration = time.monotonic() - start
        return FileResult(
            **base_result,
            parsed=False,
            parse_errors=[str(exc)],
            parse_duration_sec=round(duration, 3),
        )
