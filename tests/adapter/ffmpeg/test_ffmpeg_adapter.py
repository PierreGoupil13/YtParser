import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from ytparser.adapters.ffmpegadapter import cut_track
from ytparser.core.models import Track


def test_cut_track_requests_audio_stream_copy(tmp_path: Path) -> None:
    source = tmp_path / "source audio.mp3"
    destination = tmp_path / "piste extraite.mp3"
    track = Track(1, 1.234, 3.734, "Extrait", "Artiste")

    with patch("subprocess.run") as run:
        cut_track(source, destination, track)

    run.assert_called_once()
    arguments = run.call_args.args[0]
    assert isinstance(arguments, list)
    assert arguments[0] == "ffmpeg"
    assert arguments[arguments.index("-i") + 1] == str(source)
    assert arguments[arguments.index("-c:a") + 1] == "copy"
    assert arguments[-1] == str(destination)


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (0, 5),
        (10, 25),
        (1.234, 3.734),
        (65.123, 3723.486),
    ],
)
def test_cut_track_uses_start_and_duration(tmp_path: Path, start: float, end: float) -> None:
    track = Track(1, start, end, "Extrait", "Artiste")

    with patch("subprocess.run") as run:
        cut_track(tmp_path / "source.mp3", tmp_path / "destination.mp3", track)

    arguments = run.call_args.args[0]
    assert all(isinstance(argument, str) for argument in arguments)
    assert float(arguments[arguments.index("-ss") + 1]) == pytest.approx(start)
    assert float(arguments[arguments.index("-t") + 1]) == pytest.approx(end - start)


def test_cut_track_selects_first_audio_stream(tmp_path: Path) -> None:
    track = Track(1, 0, 5, "Extrait", "Artiste")

    with patch("subprocess.run") as run:
        cut_track(tmp_path / "source.mp3", tmp_path / "destination.mp3", track)

    arguments = run.call_args.args[0]
    assert arguments[arguments.index("-map") + 1] == "0:a:0"


def test_cut_track_disables_interaction_and_overwriting(tmp_path: Path) -> None:
    track = Track(1, 0, 5, "Extrait", "Artiste")

    with patch("subprocess.run") as run:
        cut_track(tmp_path / "source.mp3", tmp_path / "destination.mp3", track)

    arguments = run.call_args.args[0]
    assert "-nostdin" in arguments
    assert "-n" in arguments
    assert "-y" not in arguments
    assert run.call_args.kwargs.get("shell", False) is False


def test_cut_track_checks_process_exit_status(tmp_path: Path) -> None:
    track = Track(1, 0, 5, "Extrait", "Artiste")

    with patch("subprocess.run") as run:
        cut_track(tmp_path / "source.mp3", tmp_path / "destination.mp3", track)

    assert run.call_args.kwargs.get("check") is True


@pytest.mark.parametrize(
    "error",
    [
        subprocess.CalledProcessError(1, ["ffmpeg"], stderr="Invalid input"),
        FileNotFoundError("FFmpeg executable not found"),
    ],
    ids=["ffmpeg-failure", "missing-executable"],
)
def test_cut_track_propagates_process_errors(tmp_path: Path, error: Exception) -> None:
    track = Track(1, 0, 5, "Extrait", "Artiste")

    with patch("subprocess.run", side_effect=error):
        with pytest.raises(type(error)) as raised:
            cut_track(tmp_path / "source.mp3", tmp_path / "destination.mp3", track)

    assert raised.value is error
