"""CLI entry point for docscout."""

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

from docscout import __version__
from docscout.cache import Cache
from docscout.categories import SUPPORTED_EXTENSIONS, is_supported
from docscout.display import render_directory_detail, render_directory_summary, render_file_result
from docscout.logging import log, set_verbose
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
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose output on stderr")
    ] = False,
    save_images: Annotated[
        Optional[str],
        typer.Option("--save-images", help="Save annotated page images to this directory"),
    ] = None,
    version: Annotated[
        Optional[bool],
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Print version"),
    ] = None,
) -> None:
    """Analyze a document or directory of documents."""
    set_verbose(verbose)
    images_dir = Path(save_images) if save_images else None

    target = Path(path)

    if not target.exists():
        typer.echo(f"Error: path not found: {path}", err=True)
        raise typer.Exit(code=1)

    if target.is_file():
        _handle_file(target, format, images_dir, cache_dir, no_cache)
    elif target.is_dir():
        _handle_directory(target, format, detail, cache_dir, no_cache, images_dir)
    else:
        typer.echo(f"Error: unsupported path type: {path}", err=True)
        raise typer.Exit(code=1)


def _handle_file(
    target: Path,
    fmt: str,
    save_images: Path | None,
    cache_dir: str | None = None,
    no_cache: bool = False,
) -> None:
    ext = target.suffix.lower().lstrip(".")
    if not is_supported(ext):
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        typer.echo(
            f"Error: unsupported file type '.{ext}'. Supported types: {supported}",
            err=True,
        )
        raise typer.Exit(code=1)

    log(f"Analyzing single file: {target}")

    cache_path = Path(cache_dir) if cache_dir else None
    cache = Cache(cache_dir=cache_path)

    cached = None if no_cache else cache.get(target)
    if cached is not None:
        log("Cache hit, skipping parse")
        result = cached
    else:
        show_progress = sys.stderr.isatty()
        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]Parsing {task.fields[filename]}..."),
                transient=True,
            ) as progress:
                progress.add_task("parse", filename=target.name, total=None)
                result = parse_file(target, save_images=save_images)
        else:
            result = parse_file(target, save_images=save_images)
        if not no_cache and not result.parse_errors:
            cache.put(target, result)

    if fmt == "json":
        typer.echo(result.model_dump_json(indent=2))
    else:
        render_file_result(result)

    if result.parse_errors:
        raise typer.Exit(code=1)


def _handle_directory(
    target: Path,
    fmt: str,
    detail: bool,
    cache_dir: str | None,
    no_cache: bool,
    save_images: Path | None,
) -> None:
    cache_path = Path(cache_dir) if cache_dir else None
    cache = Cache(cache_dir=cache_path)

    log(f"Scanning directory: {target}")

    summary = scan_directory(
        target, cache=cache, no_cache=no_cache, save_images=save_images
    )

    if fmt == "json":
        typer.echo(summary.model_dump_json(indent=2))
    elif detail:
        render_directory_detail(summary)
    else:
        render_directory_summary(summary)

    if summary.files_with_errors > 0:
        raise typer.Exit(code=2)
