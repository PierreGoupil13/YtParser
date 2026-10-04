"""Command-line interface for YtParser."""

import typer

app = typer.Typer(no_args_is_help=True, help="YtParser: music compilation tools.")


@app.callback()
def main() -> None:
    """Expose commands without implementing business logic."""


@app.command()
def hello() -> None:
    """Check that the CLI is installed correctly."""
    typer.echo("Hello from YtParser!")
