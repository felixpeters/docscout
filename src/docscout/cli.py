"""CLI entry point for docscout."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from docscout import __version__
from docscout.cache import Cache
from docscout.categories import SUPPORTED_EXTENSIONS, is_supported
from docscout.display import render_directory_detail, render_directory_summary, render_file_result
from docscout.parsing import parse_file
from docscout.scanner import scan_directory

app = typer.Typer(help="EDA for single documents and document databases.")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"docscout {__version__}")
        raise typer.Exit()


@app.command()
def main(
    path: Annotated[str, typer.Argument(help="File or directory path to analyze")],
    format: Annotated[str, typer.Option(help="Output format: rich or json")] = "rich",
    detail: Annotated[bool, typer.Option("--detail", help="Show per-file detail table")] = False,
    cache_dir: Annotated[
        Optional[str], typer.Option("--cache-dir", help="Override cache directory")
    ] = None,
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Bypass cache")] = False,
    version: Annotated[
        Optional[bool],
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Print version"),
    ] = None,
) -> None:
    """Analyze a document or directory of documents."""
    target = Path(path)

    if not target.exists():
        typer.echo(f"Error: path not found: {path}", err=True)
        raise typer.Exit(code=1)

    if target.is_file():
        _handle_file(target, format)
    elif target.is_dir():
        _handle_directory(target, format, detail, cache_dir, no_cache)
    else:
        typer.echo(f"Error: unsupported path type: {path}", err=True)
        raise typer.Exit(code=1)


def _handle_file(target: Path, fmt: str) -> None:
    ext = target.suffix.lower().lstrip(".")
    if not is_supported(ext):
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        typer.echo(
            f"Error: unsupported file type '.{ext}'. Supported types: {supported}",
            err=True,
        )
        raise typer.Exit(code=1)

    result = parse_file(target)

    if fmt == "json":
        typer.echo(result.model_dump_json(indent=2))
    else:
        render_file_result(result)

    if result.parse_errors:
        raise typer.Exit(code=1)


def _handle_directory(
    target: Path, fmt: str, detail: bool, cache_dir: str | None, no_cache: bool
) -> None:
    cache_path = Path(cache_dir) if cache_dir else None
    cache = Cache(cache_dir=cache_path)

    summary = scan_directory(target, cache=cache, no_cache=no_cache)

    if fmt == "json":
        typer.echo(summary.model_dump_json(indent=2))
    elif detail:
        render_directory_detail(summary)
    else:
        render_directory_summary(summary)

    if summary.files_with_errors > 0:
        raise typer.Exit(code=2)
