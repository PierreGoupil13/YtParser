from pathlib import Path

import pytest
from typer.testing import CliRunner

from ytparser import cli
from ytparser.core.download import OutputFormat

runner = CliRunner()


@pytest.fixture
def requested_format(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[OutputFormat]:
    """Fake the download and record which format the CLI asked for."""
    asked: list[OutputFormat] = []
    audio = tmp_path / "id.m4a"
    audio.write_bytes(b"x")

    def fake_download(url: str, fmt: OutputFormat, out: Path) -> Path:
        asked.append(fmt)
        return audio

    monkeypatch.setattr(cli, "download_audio", fake_download)
    monkeypatch.setattr(cli, "probe_audio_codec", lambda path: "aac")
    return asked


def write_config(no_user_config: Path, content: str) -> None:
    no_user_config.write_text(content, encoding="utf-8")


def test_default_format_is_m4a(requested_format: list[OutputFormat], tmp_path: Path) -> None:
    result = runner.invoke(cli.app, ["download", "url", "-o", str(tmp_path)])
    assert result.exit_code == 0
    assert requested_format == [OutputFormat.M4A]


def test_config_overrides_the_default(
    requested_format: list[OutputFormat], no_user_config: Path, tmp_path: Path
) -> None:
    write_config(no_user_config, "format: opus\n")
    result = runner.invoke(cli.app, ["download", "url", "-o", str(tmp_path)])
    assert result.exit_code == 0
    assert requested_format == [OutputFormat.OPUS]


def test_option_overrides_the_config(
    requested_format: list[OutputFormat], no_user_config: Path, tmp_path: Path
) -> None:
    write_config(no_user_config, "format: opus\n")
    result = runner.invoke(cli.app, ["download", "url", "-f", "mp3", "-o", str(tmp_path)])
    assert result.exit_code == 0
    assert requested_format == [OutputFormat.MP3]


def test_config_option_overrides_the_user_config(
    requested_format: list[OutputFormat], no_user_config: Path, tmp_path: Path
) -> None:
    write_config(no_user_config, "format: opus\n")
    other = tmp_path / "projet.yaml"
    other.write_text("format: mp3\n", encoding="utf-8")
    result = runner.invoke(
        cli.app, ["download", "url", "--config", str(other), "-o", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert requested_format == [OutputFormat.MP3]


def test_format_option_still_wins_over_the_config_option(
    requested_format: list[OutputFormat], tmp_path: Path
) -> None:
    other = tmp_path / "projet.yaml"
    other.write_text("format: mp3\n", encoding="utf-8")
    args = ["download", "url", "--config", str(other), "-f", "opus", "-o", str(tmp_path)]
    assert runner.invoke(cli.app, args).exit_code == 0
    assert requested_format == [OutputFormat.OPUS]


def test_config_option_requires_an_existing_file(
    requested_format: list[OutputFormat], tmp_path: Path
) -> None:
    result = runner.invoke(cli.app, ["download", "url", "--config", str(tmp_path / "absent.yaml")])
    assert result.exit_code != 0
    assert requested_format == []


def test_invalid_config_is_reported(
    requested_format: list[OutputFormat], no_user_config: Path, tmp_path: Path
) -> None:
    write_config(no_user_config, "format: wav\n")
    result = runner.invoke(cli.app, ["download", "url", "-o", str(tmp_path)])
    assert result.exit_code == 1
    assert "wav" in result.output
    assert requested_format == []


def test_export_uses_the_profile_of_the_chosen_format(
    monkeypatch: pytest.MonkeyPatch, no_user_config: Path, tmp_path: Path
) -> None:
    write_config(no_user_config, "mp3_bitrate: 128k\n")
    tracklist = tmp_path / "t.yaml"
    tracklist.write_text(
        "tracks:\n  - number: 1\n    start: '00:00:00'\n    end: '00:00:05'\n"
        "    title: T\n    artist: A\n",
        encoding="utf-8",
    )
    audio = tmp_path / "a.m4a"
    audio.write_bytes(b"x")
    received = []

    def fake_export(source, tracklist, album, output, profile):  # type: ignore[no-untyped-def]
        received.append(profile)
        return []

    monkeypatch.setattr(cli, "export_library", fake_export)

    result = runner.invoke(
        cli.app,
        [
            "export",
            str(tracklist),
            "-a",
            str(audio),
            "--album",
            "X",
            "-f",
            "mp3",
            "-o",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert received[0].format is OutputFormat.MP3
    assert received[0].codec_args[-1] == "128k"
