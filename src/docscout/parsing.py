"""Document parsing layer wrapping Docling."""

import time
from pathlib import Path
from typing import Callable

from docscout.categories import get_category, is_supported
from docscout.logging import log
from docscout.models import FileResult


def parse_file(
    path: Path,
    save_images: Path | None = None,
    on_page_done: Callable[[int, int], None] | None = None,
) -> FileResult:
    """Parse a single file and return a FileResult with extracted metrics.

    Args:
        path: Path to the file to parse.
        save_images: If set, save annotated page images to this directory.
        on_page_done: Callback invoked as (current_page, total_pages) after
            the page count is known.  Called once per page during item
            iteration.
    """
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
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        log(f"Parsing {path.name} ...")

        # Configure pipeline options for image generation when requested
        format_options = {}
        if save_images is not None:
            pipeline_options = PdfPipelineOptions()
            pipeline_options.generate_page_images = True
            pipeline_options.images_scale = 2.0
            format_options[InputFormat.PDF] = PdfFormatOption(
                pipeline_options=pipeline_options
            )
            log(f"  Image generation enabled (scale=2.0)")

        converter = DocumentConverter(format_options=format_options)
        result = converter.convert(str(path))
        doc = result.document

        log(f"  Conversion complete, extracting metrics ...")

        # Word and char count from exported text
        text = doc.export_to_markdown()
        words = len(text.split())
        chars = len(text)
        log(f"  Text: {words:,} words, {chars:,} chars")

        # Page count
        page_count = 0
        if hasattr(doc, "pages") and doc.pages:
            page_count = len(doc.pages)
        log(f"  Pages: {page_count}")

        # Save page images if requested
        if save_images is not None and page_count > 0:
            save_images.mkdir(parents=True, exist_ok=True)
            stem = path.stem
            for page_no, page in doc.pages.items():
                img_path = save_images / f"{stem}-page-{page_no}.png"
                try:
                    page.image.pil_image.save(str(img_path), format="PNG")
                    log(f"  Saved page image: {img_path.name}")
                except Exception as img_exc:
                    log(f"  Failed to save page image {page_no}: {img_exc}")

        # Tables and figures
        table_count = 0
        figure_count = 0
        heading_count = 0
        heading_max_depth = 0
        section_count = 0

        from docling.datamodel.document import DocItem

        items = list(doc.iterate_items())
        pages_signaled = 0
        items_per_page = max(len(items) // page_count, 1) if page_count > 0 else 0

        for idx, (item, _level) in enumerate(items):
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

            # Fire per-page callback based on progress through items
            if on_page_done and page_count > 0 and items_per_page > 0:
                current_page = min((idx + 1) // items_per_page, page_count)
                while pages_signaled < current_page:
                    pages_signaled += 1
                    on_page_done(pages_signaled, page_count)

        # Signal remaining pages
        if on_page_done and page_count > 0:
            while pages_signaled < page_count:
                pages_signaled += 1
                on_page_done(pages_signaled, page_count)

        log(
            f"  Tables: {table_count}, Figures: {figure_count}, "
            f"Headings: {heading_count}, Sections: {section_count}"
        )

        # If no section headers found via page_header, count section_headers as sections
        if section_count == 0 and heading_count > 0:
            section_count = heading_count

        duration = time.monotonic() - start
        log(f"  Done in {duration:.1f}s")

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
        log(f"  Error after {duration:.1f}s: {exc}")
        return FileResult(
            **base_result,
            parsed=False,
            parse_errors=[str(exc)],
            parse_duration_sec=round(duration, 3),
        )
