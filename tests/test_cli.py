import io
import subprocess
import sys
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from ytparser.cli import app, main

runner = CliRunner()

TRACKLIST_YAML = """\
tracks:
  - number: 1
    start: "00:00:00"
    end: "00:00:01"
    title: "Intro"
    artist: "Artiste A"
  - number: 2
    start: "00:00:01"
    end: "00:00:02.5"
    title: "Été"
    artist: "Artiste B"
  - number: 3
    start: "00:00:02.5"
    end: "00:00:04"
    title: "Final"
    artist: "Artiste B"
"""


@pytest.fixture
def compilation(tmp_path: Path) -> tuple[Path, Path]:
    """Write a 4-second synthetic MP3 and the YAML tracklist that describes it."""
    audio = tmp_path / "compilation.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-n",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100:duration=4",
            "-c:a",
            "libmp3lame",
            str(audio),
        ],
        check=True,
    )
    tracklist = tmp_path / "tracklist.yaml"
    tracklist.write_text(TRACKLIST_YAML, encoding="utf-8")
    return tracklist, audio


def test_hello() -> None:
    result = runner.invoke(app, ["hello"])

    assert result.exit_code == 0
    assert result.output == "Hello from YtParser!\n"


def test_help() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "hello" in result.output


def test_unknown_command() -> None:
    result = runner.invoke(app, ["unknown"])

    assert result.exit_code != 0
    assert "No such command" in result.output


def test_cut_writes_one_file_per_track(tmp_path: Path, compilation: tuple[Path, Path]) -> None:
    tracklist, audio = compilation
    output = tmp_path / "pistes"

    result = runner.invoke(
        app, ["cut", str(tracklist), "--audio", str(audio), "--output", str(output)]
    )

    assert result.exit_code == 0, result.output
    assert sorted(path.name for path in output.iterdir()) == ["01.mp3", "02.mp3", "03.mp3"]
    assert all(path.stat().st_size > 0 for path in output.iterdir())
    assert "02.mp3  Artiste B - Été" in result.output
    assert "3 tracks written" in result.output


def test_cut_refuses_to_overwrite_existing_tracks(
    tmp_path: Path, compilation: tuple[Path, Path]
) -> None:
    tracklist, audio = compilation
    output = tmp_path / "pistes"
    output.mkdir()
    (output / "02.mp3").write_bytes(b"previous track")

    result = runner.invoke(app, ["cut", str(tracklist), "-a", str(audio), "-o", str(output)])

    assert result.exit_code == 1
    assert "already exists" in result.stderr
    assert [path.name for path in output.iterdir()] == ["02.mp3"]
    assert (output / "02.mp3").read_bytes() == b"previous track"


@pytest.mark.parametrize(
    ("yaml_text", "message"),
    [
        pytest.param("tracks: [", "", id="invalid-yaml-syntax"),
        pytest.param(
            TRACKLIST_YAML.replace('"00:00:04"', '"00:00:09"'), "Track 3", id="longer-than-audio"
        ),
    ],
)
def test_cut_reports_invalid_tracklist(
    tmp_path: Path, compilation: tuple[Path, Path], yaml_text: str, message: str
) -> None:
    tracklist, audio = compilation
    tracklist.write_text(yaml_text, encoding="utf-8")

    result = runner.invoke(app, ["cut", str(tracklist), "-a", str(audio), "-o", str(tmp_path)])

    assert result.exit_code == 1
    assert result.stderr.startswith("Error: ")
    assert message in result.stderr
    assert not list(tmp_path.glob("0*.mp3"))


def test_cut_reports_unreadable_audio(tmp_path: Path, compilation: tuple[Path, Path]) -> None:
    tracklist, _ = compilation
    fake_audio = tmp_path / "not-audio.mp3"
    fake_audio.write_text("not an audio file", encoding="utf-8")

    result = runner.invoke(app, ["cut", str(tracklist), "-a", str(fake_audio), "-o", str(tmp_path)])

    assert result.exit_code == 1
    assert result.stderr.startswith("Error: ffprobe failed")


def test_cut_explains_missing_ffmpeg(
    tmp_path: Path, compilation: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    tracklist, audio = compilation
    monkeypatch.setattr("shutil.which", lambda tool: None)

    result = runner.invoke(app, ["cut", str(tracklist), "-a", str(audio), "-o", str(tmp_path)])

    assert result.exit_code == 1
    assert result.stderr.startswith("Error: ffmpeg and ffprobe not found")
    assert "PATH" in result.stderr


def test_redirected_ansi_output_does_not_crash_on_any_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    buffer = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(buffer, encoding="cp1252", newline=""))

    main()
    typer.echo("01.mp3  Önigirisu - 日本")
    sys.stdout.flush()

    assert buffer.getvalue().decode("cp1252") == "01.mp3  Önigirisu - ??\n"
