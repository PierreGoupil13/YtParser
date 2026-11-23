from pathlib import Path

import pytest
from typer.testing import CliRunner

from ytparser import cli
from ytparser.adapters.yamladapter import load_tracklist
from ytparser.adapters.ytdlpadapter import VideoFetchError
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
    [(VideoFetchError("Video unavailable"), "Video unavailable"), (None, "No usable timestamps")],
)
def test_plan_reports_errors_without_a_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error, message: str
) -> None:
    def fetch(url: str) -> VideoInfo:
        if error:
            raise error
        return VideoInfo("Mix", 300)

    monkeypatch.setattr(cli, "fetch_video_info", fetch)
    output = tmp_path / "tracklist.yaml"

    result = runner.invoke(cli.app, ["plan", "URL", "-o", str(output)])

    assert result.exit_code == 1
    assert message in result.output
    assert not output.exists()
