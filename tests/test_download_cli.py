from pathlib import Path

import pytest
from typer.testing import CliRunner
from yt_dlp.utils import DownloadError

from ytparser import cli
from ytparser.adapters import ytdlpadapter
from ytparser.adapters.ytdlpadapter import AudioDownloadError, download_audio
from ytparser.core.download import OutputFormat, source_plan

runner = CliRunner()


class FakeYoutubeDL:
    captured: dict = {}
    error: Exception | None = None
    filepath: str | None = None

    def __init__(self, options: dict) -> None:
        FakeYoutubeDL.captured = options

    def __enter__(self) -> "FakeYoutubeDL":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def extract_info(self, url: str, download: bool) -> dict:
        if FakeYoutubeDL.error:
            raise FakeYoutubeDL.error
        return {"requested_downloads": [{"filepath": FakeYoutubeDL.filepath}]}


@pytest.fixture
def fake_ytdlp(monkeypatch: pytest.MonkeyPatch) -> type[FakeYoutubeDL]:
    FakeYoutubeDL.error = None
    FakeYoutubeDL.filepath = None
    monkeypatch.setattr(ytdlpadapter, "YoutubeDL", FakeYoutubeDL)
    return FakeYoutubeDL


@pytest.mark.parametrize("target", list(OutputFormat))
def test_download_uses_the_selector_of_the_target_format(
    fake_ytdlp: type[FakeYoutubeDL], tmp_path: Path, target: OutputFormat
) -> None:
    audio = tmp_path / "id.m4a"
    audio.write_bytes(b"x")
    fake_ytdlp.filepath = str(audio)

    assert download_audio("url", target, tmp_path) == audio
    assert fake_ytdlp.captured["format"] == source_plan(target).selector
    assert not fake_ytdlp.captured.get("postprocessors")


def test_unavailable_video_gives_a_clear_error(
    fake_ytdlp: type[FakeYoutubeDL], tmp_path: Path
) -> None:
    fake_ytdlp.error = DownloadError("ERROR: [youtube] x: This video is unavailable")

    with pytest.raises(AudioDownloadError, match="unavailable"):
        download_audio("url", OutputFormat.M4A, tmp_path)


def test_ytdlp_failure_suggests_an_update(fake_ytdlp: type[FakeYoutubeDL], tmp_path: Path) -> None:
    fake_ytdlp.error = DownloadError("ERROR: unable to extract player response")

    with pytest.raises(AudioDownloadError, match="Update yt-dlp"):
        download_audio("url", OutputFormat.M4A, tmp_path)


def test_bot_check_is_not_reported_as_unavailable(
    fake_ytdlp: type[FakeYoutubeDL], tmp_path: Path
) -> None:
    fake_ytdlp.error = DownloadError("ERROR: [youtube] x: Sign in to confirm you're not a bot")

    with pytest.raises(AudioDownloadError, match="Update yt-dlp") as raised:
        download_audio("url", OutputFormat.M4A, tmp_path)

    assert "unavailable" not in str(raised.value)


def test_missing_downloaded_file_is_an_error(
    fake_ytdlp: type[FakeYoutubeDL], tmp_path: Path
) -> None:
    fake_ytdlp.filepath = str(tmp_path / "absent.m4a")

    with pytest.raises(AudioDownloadError):
        download_audio("url", OutputFormat.M4A, tmp_path)


def test_download_command_reports_codec_and_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    audio = tmp_path / "id.webm"
    audio.write_bytes(b"x")
    monkeypatch.setattr(cli, "download_audio", lambda url, fmt, out: audio)
    monkeypatch.setattr(cli, "probe_audio_codec", lambda path: "opus")

    result = runner.invoke(cli.app, ["download", "url", "--format", "m4a", "-o", str(tmp_path)])

    assert result.exit_code == 0
    assert "codec: opus" in result.output
    assert "fell back" in result.output


def test_download_command_fails_cleanly(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def boom(url: str, fmt: OutputFormat, out: Path) -> Path:
        raise AudioDownloadError("The video is unavailable")

    monkeypatch.setattr(cli, "download_audio", boom)

    result = runner.invoke(cli.app, ["download", "url", "-o", str(tmp_path)])

    assert result.exit_code == 1
    assert "unavailable" in result.output
