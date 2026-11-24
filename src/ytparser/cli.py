"""Command-line interface for YtParser."""

import io
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from yaml import YAMLError

from ytparser.adapters.configadapter import load_config
from ytparser.adapters.ffmpegadapter import cut_tracklist, probe_audio_codec
from ytparser.adapters.libraryadapter import export_library
from ytparser.adapters.yamladapter import load_tracklist, save_tracklist
from ytparser.adapters.ytdlpadapter import (
    AudioDownloadError,
    VideoFetchError,
    download_audio,
    fetch_video_info,
)
from ytparser.core.config import ConfigError, resolve_format
from ytparser.core.download import OutputFormat
from ytparser.core.plan import build_tracklist
from ytparser.core.profiles import OutputProfile, get_profile
from ytparser.core.sources import SourceSelection, select_source

FORMAT_HELP = "Output format: m4a, mp3 or opus. Default: config file, then m4a."
ConfigOption = Annotated[
    Path | None,
    typer.Option(
        "--config",
        exists=True,
        dir_okay=False,
        readable=True,
        help="YAML settings file to use instead of the user config.yaml.",
    ),
]

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


@app.command()
def plan(
    url: Annotated[str, typer.Argument(help="YouTube video URL.")],
    artist: Annotated[
        str | None,
        typer.Option("--artist", "-a", help="Artist used when a label does not name one."),
    ] = None,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", dir_okay=False, help="YAML tracklist to write."),
    ] = Path("tracklist.yaml"),
    comment: Annotated[
        int | None,
        typer.Option(
            "--comment",
            "-c",
            min=1,
            help="Use this comment of the ranked list instead of chapters or description.",
        ),
    ] = None,
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing file.")] = False,
) -> None:
    """Build an editable YAML tracklist from the timestamps of a YouTube video.

    Sources are tried in order: chapters, description, then the best comment.
    """
    if output.exists() and not force:
        _fail(f"{output} already exists; use --force to overwrite it.")

    try:
        typer.echo("Fetching video metadata (no download)...")
        info = fetch_video_info(url)
        selection = select_source(info, None if comment is None else comment - 1)
        tracklist = build_tracklist(selection.entries, info.duration, artist)
        save_tracklist(output, tracklist)
    except (VideoFetchError, OSError, ValueError) as error:
        _fail(str(error))

    typer.echo(f"Video: {info.title}")
    if selection.source == "comment":
        _echo_comment_candidates(selection)
    typer.echo(f"{len(tracklist.tracks)} tracks from {selection.source} written to {output}")


@app.command()
def download(
    url: Annotated[str, typer.Argument(help="YouTube video URL.")],
    audio_format: Annotated[
        OutputFormat | None,
        typer.Option("--format", "-f", help=FORMAT_HELP + " Selects the source stream."),
    ] = None,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", file_okay=False, help="Folder receiving the audio file."),
    ] = Path("output"),
    config_file: ConfigOption = None,
) -> None:
    """Download the audio stream of a video (no video, no re-encoding) and check its codec."""
    profile = _resolve_profile(audio_format, config_file)
    source = profile.source
    try:
        typer.echo(f"Downloading audio for {profile.format.value}...")
        path = download_audio(url, profile.format, output)
        codec = probe_audio_codec(path)
    except AudioDownloadError as error:
        _fail(str(error))
    except FileNotFoundError:
        _fail("ffprobe not found. Install FFmpeg and add it to the PATH.")
    except (subprocess.CalledProcessError, OSError, ValueError) as error:
        _fail(f"downloaded file is unreadable: {error}")

    typer.echo(f"{path} (codec: {codec})")
    if not source.is_preferred(codec):
        typer.secho(
            f"Warning: preferred {source.preferred_codec} stream unavailable; "
            f"fell back to {codec}.",
            err=True,
            fg=typer.colors.YELLOW,
        )


@app.command()
def export(
    tracklist_file: Annotated[
        Path,
        typer.Argument(exists=True, dir_okay=False, readable=True, help="YAML tracklist."),
    ],
    audio: Annotated[
        Path,
        typer.Option("--audio", "-a", exists=True, dir_okay=False, help="Local .m4a file."),
    ],
    album: Annotated[str, typer.Option("--album", help="Album title (the compilation).")],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", file_okay=False, help="Library root folder."),
    ] = Path("output"),
    audio_format: Annotated[
        OutputFormat | None, typer.Option("--format", "-f", help=FORMAT_HELP)
    ] = None,
    config_file: ConfigOption = None,
) -> None:
    """Cut, tag and file tracks as Artist/Album/NN - Title.ext (Jellyfin layout)."""
    profile = _resolve_profile(audio_format, config_file)
    try:
        tracklist = load_tracklist(tracklist_file)
        created = export_library(audio, tracklist, album, output, profile)
    except subprocess.CalledProcessError as error:
        details = (error.stderr or "").strip() or "see the messages above."
        _fail(f"{error.cmd[0]} failed with exit code {error.returncode}: {details}")
    except (OSError, ValueError, YAMLError) as error:
        _fail(str(error))

    for path in created:
        typer.echo(path.relative_to(output))
    typer.echo(f"{len(created)} tagged tracks written to {output}")


@app.command()
def auto(
    url: Annotated[str, typer.Argument(help="YouTube video URL.")],
    artist: Annotated[
        str | None,
        typer.Option("--artist", "-a", help="Artist used when a label does not name one."),
    ] = None,
    comment: Annotated[
        int | None,
        typer.Option("--comment", "-c", min=1, help="Use this comment of the ranked list."),
    ] = None,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", file_okay=False, help="Library root folder."),
    ] = Path("output"),
    audio_format: Annotated[
        OutputFormat | None, typer.Option("--format", "-f", help=FORMAT_HELP)
    ] = None,
    config_file: ConfigOption = None,
) -> None:
    """URL to tagged tracks: plan, download, cut, tag and file them in one go."""
    profile = _resolve_profile(audio_format, config_file)
    try:
        typer.echo("Fetching video metadata (no download)...")
        info = fetch_video_info(url)
        selection = select_source(info, None if comment is None else comment - 1)
        tracklist = build_tracklist(selection.entries, info.duration, artist)
        typer.echo(f"{len(tracklist.tracks)} tracks from {selection.source}; downloading...")
        with tempfile.TemporaryDirectory(prefix="ytparser-dl-") as temp:
            audio = download_audio(url, profile.format, Path(temp))
            created = export_library(audio, tracklist, info.title, output, profile)
    except (VideoFetchError, AudioDownloadError) as error:
        _fail(str(error))
    except subprocess.CalledProcessError as error:
        details = (error.stderr or "").strip() or "see the messages above."
        _fail(f"{error.cmd[0]} failed with exit code {error.returncode}: {details}")
    except (OSError, ValueError) as error:
        _fail(str(error))

    for path in created:
        typer.echo(path.relative_to(output))
    typer.echo(f"{len(created)} tagged tracks written to {output}")


def _echo_comment_candidates(selection: SourceSelection) -> None:
    typer.echo("Comment candidates (most timestamps, then most likes):")
    for index, candidate in enumerate(selection.candidates):
        marker = "*" if index == selection.chosen else " "
        first_line = candidate.comment.text.strip().splitlines()[0][:60]
        typer.echo(
            f" {marker} {index + 1}. {len(candidate.entries)} timestamps, "
            f"{candidate.comment.like_count} likes - {first_line}"
        )
    if len(selection.candidates) > 1:
        typer.echo("Use --comment N to pick another one.")


def _resolve_profile(audio_format: OutputFormat | None, config_file: Path | None) -> OutputProfile:
    """Apply the priority: --format option, then config file, then the m4a default."""
    try:
        config = load_config(config_file)
    except ConfigError as error:
        _fail(str(error))
    return get_profile(resolve_format(audio_format, config), config.mp3_bitrate)


def _fail(message: str) -> NoReturn:
    typer.secho(f"Error: {message}", err=True, fg=typer.colors.RED)
    raise typer.Exit(code=1)
