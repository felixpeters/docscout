"""Document parsing layer wrapping Docling."""

import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable

from docscout.categories import get_category, is_supported
from docscout.logging import log
from docscout.models import FileResult

# Formats that should be converted to PDF via LibreOffice before parsing
_CONVERT_TO_PDF_FORMATS = {"pptx", "docx"}


def _convert_to_pdf(source: Path) -> Path:
    """Convert a file to PDF via LibreOffice into a temp directory.

    Returns the path to the generated PDF.
    Raises RuntimeError if LibreOffice is not installed or conversion fails.
    The caller is responsible for cleaning up the parent temp directory.
    """
    soffice = shutil.which("soffice")
    if soffice is None:
        raise RuntimeError(
            "LibreOffice (soffice) is required for PPTX/DOCX parsing but was not found. "
            "Install it from https://www.libreoffice.org/"
        )

    tmpdir = tempfile.mkdtemp(prefix="docscout-")
    cmd = [soffice, "--headless", "--convert-to", "pdf", "--outdir", tmpdir, str(source)]
    log("  Converting to PDF via LibreOffice ...")
    proc = subprocess.run(cmd, capture_output=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(
            f"LibreOffice conversion failed (exit {proc.returncode}): "
            f"{proc.stderr.decode(errors='replace').strip()}"
        )

    pdf_path = Path(tmpdir) / (source.stem + ".pdf")
    if not pdf_path.exists():
        raise RuntimeError(f"LibreOffice did not produce expected PDF: {pdf_path.name}")

    return pdf_path


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
        return FileResult(**base_result, parsed=False)  # type: ignore[arg-type]

    start = time.monotonic()
    tmp_pdf_dir = None
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.document import DocItem  # type: ignore[attr-defined]
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        log(f"Parsing {path.name} ...")

        # For PPTX/DOCX: convert to PDF first, then parse the PDF
        parse_path = path
        if ext in _CONVERT_TO_PDF_FORMATS:
            pdf_path = _convert_to_pdf(path)
            tmp_pdf_dir = pdf_path.parent
            parse_path = pdf_path

        # Configure pipeline options for image generation when requested
        format_options = {}
        if save_images is not None:
            pipeline_options = PdfPipelineOptions()
            pipeline_options.generate_page_images = True
            pipeline_options.images_scale = 2.0
            format_options[InputFormat.PDF] = PdfFormatOption(pipeline_options=pipeline_options)
            log("  Image generation enabled (scale=2.0)")

        converter = DocumentConverter(format_options=format_options)  # type: ignore[arg-type]
        result = converter.convert(str(parse_path))
        doc = result.document

        log("  Conversion complete, extracting metrics ...")

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

        # Save annotated page images if requested
        if save_images is not None and page_count > 0:
            save_images.mkdir(parents=True, exist_ok=True)
            stem = path.stem

            # Collect bounding boxes per page from all items
            from collections import defaultdict

            from docling_core.types.doc.base import CoordOrigin
            from PIL import ImageDraw

            page_annotations: dict[int, list[tuple[str, tuple[float, ...]]]] = defaultdict(list)  # noqa: E501
            for item, _lvl in doc.iterate_items():
                if not isinstance(item, DocItem):
                    continue
                if not item.prov:
                    continue
                label = item.label.value if hasattr(item.label, "value") else str(item.label)
                for prov in item.prov:
                    bbox = prov.bbox
                    page_annotations[prov.page_no].append(
                        (label, (bbox.l, bbox.t, bbox.r, bbox.b, bbox.coord_origin))  # type: ignore[arg-type]
                    )

            # Color map for different element types
            label_colors = {
                "table": "red",
                "picture": "blue",
                "section_header": "green",
                "page_header": "orange",
                "text": "gray",
                "list_item": "purple",
                "caption": "cyan",
                "formula": "magenta",
            }

            for page_no, page in doc.pages.items():
                img_path = save_images / f"{stem}-page-{page_no}.png"
                try:
                    if not page.image or not page.image.pil_image:
                        log(f"  No image available for page {page_no}, skipping")
                        continue

                    img = page.image.pil_image.copy()
                    draw = ImageDraw.Draw(img)

                    # Compute scale factor: image pixels / page points
                    page_w = page.size.width if page.size else img.width
                    page_h = page.size.height if page.size else img.height
                    sx = img.width / page_w
                    sy = img.height / page_h

                    for label, (left, top, right, bot, coord_origin) in page_annotations.get(
                        page_no, []
                    ):
                        # Convert from PDF coords (bottom-left origin) to image coords
                        if coord_origin == CoordOrigin.BOTTOMLEFT:  # type: ignore[comparison-overlap]
                            x0 = left * sx
                            y0 = (page_h - top) * sy
                            x1 = right * sx
                            y1 = (page_h - bot) * sy
                        else:
                            x0 = left * sx
                            y0 = top * sy
                            x1 = right * sx
                            y1 = bot * sy

                        color = label_colors.get(label, "gray")
                        draw.rectangle([x0, y0, x1, y1], outline=color, width=2)
                        draw.text((x0, y0 - 12), label, fill=color)

                    img.save(str(img_path), format="PNG")
                    log(f"  Saved annotated page image: {img_path.name}")
                except Exception as img_exc:
                    log(f"  Failed to save page image {page_no}: {img_exc}")

        # Tables and figures
        table_count = 0
        figure_count = 0
        heading_count = 0
        heading_max_depth = 0
        section_count = 0

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
                elif label_name in ("section_header", "title"):
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
            **base_result,  # type: ignore[arg-type]
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
            **base_result,  # type: ignore[arg-type]
            parsed=False,
            parse_errors=[str(exc)],
            parse_duration_sec=round(duration, 3),
        )
    finally:
        # Clean up temp PDF directory
        if tmp_pdf_dir is not None:
            shutil.rmtree(tmp_pdf_dir, ignore_errors=True)
