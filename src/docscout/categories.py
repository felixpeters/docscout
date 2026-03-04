"""File extension to category mapping for docscout."""

SUPPORTED_EXTENSIONS: set[str] = {"pdf", "docx", "pptx"}

EXTENSION_TO_CATEGORY: dict[str, str] = {
    # Supported (parsed via Docling)
    "pdf": "documents",
    "docx": "documents",
    "pptx": "documents",
    # Documents (detection only)
    "doc": "documents",
    "odt": "documents",
    "rtf": "documents",
    "txt": "documents",
    "md": "documents",
    "html": "documents",
    "epub": "documents",
    # Spreadsheets
    "csv": "spreadsheets",
    "xlsx": "spreadsheets",
    "xls": "spreadsheets",
    "ods": "spreadsheets",
    "tsv": "spreadsheets",
    # Images
    "png": "images",
    "jpg": "images",
    "jpeg": "images",
    "gif": "images",
    "svg": "images",
    "tiff": "images",
    "bmp": "images",
    "webp": "images",
    # Tabular data
    "parquet": "tabular data",
    "feather": "tabular data",
    "arrow": "tabular data",
    # Archives
    "zip": "archives",
    "tar": "archives",
    "gz": "archives",
    "7z": "archives",
    "rar": "archives",
}


def get_category(extension: str) -> str:
    """Return the category for a file extension. Defaults to 'other'."""
    return EXTENSION_TO_CATEGORY.get(extension.lower().lstrip("."), "other")


def is_supported(extension: str) -> bool:
    """Return True if the extension is supported for detailed parsing."""
    return extension.lower().lstrip(".") in SUPPORTED_EXTENSIONS
