import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from ytparser.adapters import ffmpegadapter
from ytparser.core.models import Track, Tracklist
from ytparser.core.profiles import M4A_PROFILE, mp3_profile

TRACKLIST = Tracklist(
    (
        Track(1, 0, 4.5, "Intro", "Artiste A"),
        Track(2, 4.5, 10, "Été", "Artiste B"),
    )
)


@pytest.fixture(autouse=True)
def tools_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep these mocked tests independent of the local FFmpeg installation."""
    monkeypatch.setattr("shutil.which", lambda tool: tool)


def test_cut_tracklist_cuts_each_track_in_order(tmp_path: Path) -> None:
    source = tmp_path / "compilation.mp3"
    output_dir = tmp_path / "sortie" / "UC1"

    with (
        patch.object(ffmpegadapter, "probe_duration", return_value=10.0),
        patch.object(ffmpegadapter, "cut_track_without_reencoding") as cut,
    ):
        created = ffmpegadapter.cut_tracklist(source, TRACKLIST, output_dir)

    assert created == [output_dir / "01.mp3", output_dir / "02.mp3"]
    assert output_dir.is_dir()
    assert [call.args for call in cut.call_args_list] == [
        (source, output_dir / "01.mp3", TRACKLIST.tracks[0]),
        (source, output_dir / "02.mp3", TRACKLIST.tracks[1]),
    ]


def test_cut_tracklist_with_profile_uses_its_extension_and_codec_args(tmp_path: Path) -> None:
    source = tmp_path / "compilation.m4a"
    output_dir = tmp_path / "sortie"

    with (
        patch.object(ffmpegadapter, "probe_duration", return_value=10.0),
        patch.object(ffmpegadapter, "probe_audio_codec", return_value="aac"),
        patch.object(ffmpegadapter, "_run_cut") as run_cut,
    ):
        created = ffmpegadapter.cut_tracklist(source, TRACKLIST, output_dir, M4A_PROFILE)

    assert created == [output_dir / "01.m4a", output_dir / "02.m4a"]
    assert [call.args for call in run_cut.call_args_list] == [
        (source, output_dir / "01.m4a", TRACKLIST.tracks[0], ["-c:a", "copy"], 0.0),
        (source, output_dir / "02.m4a", TRACKLIST.tracks[1], ["-c:a", "copy"], 0.0),
    ]


def test_cut_tracklist_refuses_a_stream_copy_with_the_wrong_codec(tmp_path: Path) -> None:
    output_dir = tmp_path / "sortie"

    with (
        patch.object(ffmpegadapter, "probe_duration", return_value=10.0),
        patch.object(ffmpegadapter, "probe_audio_codec", return_value="mp3"),
        patch.object(ffmpegadapter, "_run_cut") as run_cut,
    ):
        with pytest.raises(ValueError, match="mp3 codec.*aac"):
            ffmpegadapter.cut_tracklist(tmp_path / "c.mp3", TRACKLIST, output_dir, M4A_PROFILE)

    run_cut.assert_not_called()
    assert not output_dir.exists()


def test_cut_tracklist_reencoding_profile_accepts_any_source_codec(tmp_path: Path) -> None:
    with (
        patch.object(ffmpegadapter, "probe_duration", return_value=10.0),
        patch.object(ffmpegadapter, "probe_audio_codec") as probe,
        patch.object(ffmpegadapter, "_run_cut") as run_cut,
    ):
        ffmpegadapter.cut_tracklist(tmp_path / "c.m4a", TRACKLIST, tmp_path / "o", mp3_profile())

    probe.assert_not_called()
    assert run_cut.call_args_list[0].args[3:] == (["-c:a", "libmp3lame", "-b:a", "192k"], 1.0)


def test_cut_tracklist_refuses_existing_files_before_cutting(tmp_path: Path) -> None:
    existing = tmp_path / "02.mp3"
    existing.write_bytes(b"previous track")

    with (
        patch.object(ffmpegadapter, "probe_duration", return_value=10.0),
        patch.object(ffmpegadapter, "cut_track_without_reencoding") as cut,
    ):
        with pytest.raises(FileExistsError, match="02.mp3"):
            ffmpegadapter.cut_tracklist(tmp_path / "compilation.mp3", TRACKLIST, tmp_path)

    cut.assert_not_called()
    assert existing.read_bytes() == b"previous track"


def test_cut_tracklist_rejects_audio_shorter_than_tracklist(tmp_path: Path) -> None:
    output_dir = tmp_path / "sortie"

    with (
        patch.object(ffmpegadapter, "probe_duration", return_value=5.0),
        patch.object(ffmpegadapter, "cut_track_without_reencoding") as cut,
    ):
        with pytest.raises(ValueError, match="Track 2"):
            ffmpegadapter.cut_tracklist(tmp_path / "compilation.mp3", TRACKLIST, output_dir)

    cut.assert_not_called()
    assert not output_dir.exists()


def test_probe_duration_rejects_output_without_duration(tmp_path: Path) -> None:
    completed = subprocess.CompletedProcess(args=["ffprobe"], returncode=0, stdout='{"format": {}}')

    with patch("subprocess.run", return_value=completed):
        with pytest.raises(ValueError, match="duration"):
            ffmpegadapter.probe_duration(tmp_path / "compilation.mp3")
