from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from ytparser import cli
from ytparser.adapters.yamladapter import load_tracklist
from ytparser.adapters.ytdlpadapter import AudioDownloadError, VideoFetchError
from ytparser.core.signal import AudioSignal
from ytparser.core.video import Chapter, Comment, VideoInfo

runner = CliRunner()


def patch_video(monkeypatch: pytest.MonkeyPatch, info: VideoInfo) -> None:
    monkeypatch.setattr(cli, "fetch_video_info", lambda url: info)


def test_plan_from_chapters_writes_a_loadable_tracklist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch_video(
        monkeypatch,
        VideoInfo("Mix", 300, chapters=(Chapter(0, "A - One"), Chapter(100, "Two"))),
    )
    output = tmp_path / "tracklist.yaml"

    result = runner.invoke(cli.app, ["plan", "URL", "--artist", "Me", "-o", str(output)])

    assert result.exit_code == 0, result.output
    assert "2 tracks from chapters" in result.output
    tracks = load_tracklist(output).tracks
    assert [(t.artist, t.title, t.start, t.end) for t in tracks] == [
        ("A", "One", 0.0, 100.0),
        ("Me", "Two", 100.0, 300.0),
    ]


def test_plan_lists_comment_candidates_and_manual_choice_works(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    comments = (
        Comment("0:00 Best\n1:00 Best 2\n2:00 Best 3", like_count=10),
        Comment("0:00 Other\n1:00 Other 2", like_count=99),
    )
    patch_video(monkeypatch, VideoInfo("Mix", 300, comments=comments))
    output = tmp_path / "tracklist.yaml"

    default = runner.invoke(cli.app, ["plan", "URL", "-o", str(output)])
    assert default.exit_code == 0, default.output
    assert "1. 3 timestamps" in default.output and "2. 2 timestamps" in default.output
    assert "--comment N" in default.output
    assert len(load_tracklist(output).tracks) == 3

    manual = runner.invoke(cli.app, ["plan", "URL", "-o", str(output), "--comment", "2", "--force"])
    assert manual.exit_code == 0, manual.output
    assert [t.title for t in load_tracklist(output).tracks] == ["Other", "Other 2"]


def test_plan_refuses_to_overwrite_without_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch_video(monkeypatch, VideoInfo("Mix", 300, chapters=(Chapter(0, "A"), Chapter(5, "B"))))
    output = tmp_path / "tracklist.yaml"
    output.write_text("keep me", encoding="utf-8")

    result = runner.invoke(cli.app, ["plan", "URL", "-o", str(output)])

    assert result.exit_code == 1
    assert "already exists" in result.output
    assert output.read_text(encoding="utf-8") == "keep me"


@pytest.mark.parametrize(
    ("error", "message"),
    [(VideoFetchError("Video unavailable"), "Video unavailable")],
)
def test_plan_reports_errors_without_a_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error, message: str
) -> None:
    def fetch(url: str) -> VideoInfo:
        raise error

    monkeypatch.setattr(cli, "fetch_video_info", fetch)
    output = tmp_path / "tracklist.yaml"

    result = runner.invoke(cli.app, ["plan", "URL", "-o", str(output)])

    assert result.exit_code == 1
    assert message in result.output
    assert not output.exists()


def test_plan_reports_a_failed_download_of_the_silence_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(url: str, fmt: object, folder: Path) -> Path:
        raise AudioDownloadError("Download failed")

    patch_video(monkeypatch, VideoInfo("Mix", 300))
    monkeypatch.setattr(cli, "download_audio", fail)
    output = tmp_path / "tracklist.yaml"

    result = runner.invoke(cli.app, ["plan", "URL", "-o", str(output)])

    assert result.exit_code == 1
    assert "Download failed" in result.output
    assert not output.exists()


def test_plan_falls_back_on_silences_when_no_timestamp_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rate = 8_000
    tone = np.sin(2 * np.pi * 440 * np.arange(40 * rate) / rate).astype(np.float32) * 0.5
    quiet = np.zeros(3 * rate, dtype=np.float32)
    signal = AudioSignal(np.concatenate([tone, quiet, tone]), rate)
    patch_video(monkeypatch, VideoInfo("Mix", signal.duration))
    monkeypatch.setattr(cli, "download_audio", lambda url, fmt, folder: tmp_path / "x.m4a")
    monkeypatch.setattr(cli, "load_signal", lambda path: signal)
    output = tmp_path / "tracklist.yaml"

    result = runner.invoke(cli.app, ["plan", "URL", "-o", str(output)])

    assert result.exit_code == 0, result.output
    assert "2 tracks from silence" in result.output
    assert "No timestamps found" in result.output
    tracks = load_tracklist(output).tracks
    assert tracks[0].end == pytest.approx(41.5, abs=0.1)
    assert [t.title for t in tracks] == ["Titre 1", "Titre 2"]


def test_plan_manual_comment_choice_does_not_fall_back_on_silences(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch_video(monkeypatch, VideoInfo("Mix", 300))

    result = runner.invoke(cli.app, ["plan", "URL", "-o", str(tmp_path / "t.yaml"), "-c", "1"])

    assert result.exit_code == 1
    assert "silence" not in result.output.lower()


def _refine_setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rate = 8_000
    tone = np.sin(2 * np.pi * 440 * np.arange(60 * rate) / rate).astype(np.float32) * 0.5
    signal = AudioSignal(np.concatenate([tone, np.zeros(6 * rate, dtype=np.float32), tone]), rate)
    patch_video(
        monkeypatch,
        VideoInfo("Mix", signal.duration, chapters=(Chapter(0, "A - One"), Chapter(56, "B - Two"))),
    )
    monkeypatch.setattr(cli, "download_audio", lambda url, fmt, folder: tmp_path / "x.m4a")
    monkeypatch.setattr(cli, "load_signal", lambda path: signal)


def test_plan_refine_moves_timestamps_and_keeps_the_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _refine_setup(tmp_path, monkeypatch)
    output = tmp_path / "tracklist.yaml"

    result = runner.invoke(cli.app, ["plan", "URL", "-o", str(output), "--refine"])

    assert result.exit_code == 0, result.output
    assert load_tracklist(output).tracks[1].start == pytest.approx(66.0, abs=0.6)
    assert load_tracklist(tmp_path / "tracklist.original.yaml").tracks[1].start == 56.0
    assert "track 2: 56.0s ->" in result.output


def test_plan_refine_refuses_to_overwrite_the_original_without_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _refine_setup(tmp_path, monkeypatch)
    (tmp_path / "tracklist.original.yaml").write_text("keep me", encoding="utf-8")

    result = runner.invoke(
        cli.app, ["plan", "URL", "-o", str(tmp_path / "tracklist.yaml"), "--refine"]
    )

    assert result.exit_code == 1
    assert "already exists" in result.output
