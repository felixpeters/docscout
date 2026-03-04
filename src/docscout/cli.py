import typer

app = typer.Typer(help="EDA for single documents and document databases.")


@app.command()
def main(
    path: str = typer.Argument(help="File or directory path to analyze"),
) -> None:
    """Analyze a document or directory of documents."""
    typer.echo(f"docscout: {path}")
    raise typer.Exit()
