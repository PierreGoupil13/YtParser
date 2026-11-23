"""Command-line interface for YtParser."""

import io
import subprocess
import sys
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from yaml import YAMLError

from ytparser.adapters.ffmpegadapter import cut_tracklist
from ytparser.adapters.yamladapter import load_tracklist

app = typer.Typer(no_args_is_help=True, help="YtParser: music compilation tools.")


@app.callback()
def main() -> None:
    """Expose commands without implementing business logic."""
    # Une sortie redirigée sous Windows utilise souvent cp1252 : remplacer plutôt que planter
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(errors="replace")


@app.command()
def hello() -> None:
    """Check that the CLI is installed correctly."""
    typer.echo("Hello from YtParser!")


@app.command()
def cut(
    tracklist_file: Annotated[
        Path,
        typer.Argument(exists=True, dir_okay=False, readable=True, help="YAML tracklist."),
    ],
    audio: Annotated[
        Path,
        typer.Option(
            "--audio",
            "-a",
            exists=True,
            dir_okay=False,
            readable=True,
            help="Local audio file described by the tracklist.",
        ),
    ],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", file_okay=False, help="Folder receiving the tracks."),
    ] = Path("output"),
) -> None:
    """Cut a local audio file into one file per track, without re-encoding.

    Tracks keep the source format and are named after their number: 01.mp3, 02.mp3...
    """
    try:
        tracklist = load_tracklist(tracklist_file)
        typer.echo(f"Cutting {len(tracklist.tracks)} tracks from {audio.name} (stream copy)...")
        created = cut_tracklist(audio, tracklist, output)
    except subprocess.CalledProcessError as error:
        details = (error.stderr or "").strip() or "see the messages above."
        _fail(f"{error.cmd[0]} failed with exit code {error.returncode}: {details}")
    except (OSError, ValueError, YAMLError) as error:
        _fail(str(error))

    for path, track in zip(created, tracklist.tracks, strict=True):
        typer.echo(f"{path.name}  {track.artist} - {track.title}")
    typer.echo(f"{len(created)} tracks written to {output}")


def _fail(message: str) -> NoReturn:
    typer.secho(f"Error: {message}", err=True, fg=typer.colors.RED)
    raise typer.Exit(code=1)
