import shutil
import subprocess
from pathlib import Path

import pytest
from mutagen.id3 import ID3
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus

from ytparser.adapters import tagadapter
from ytparser.adapters.libraryadapter import export_library
from ytparser.adapters.tagadapter import UnsupportedTagFormatError, write_tags
from ytparser.core.download import OutputFormat
from ytparser.core.models import Track, Tracklist
from ytparser.core.naming import TrackTags
from ytparser.core.profiles import M4A_PROFILE, OPUS_PROFILE, mp3_profile

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg missing")

TAGS = TrackTags("Song", "Art", "Alb", "Various Artists", 2, 5)


def make_audio(path: Path, *codec_args: str) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=duration=6", *codec_args, str(path)],
        check=True,
    )


def make_m4a(path: Path) -> None:
    make_audio(path, "-c:a", "aac")


@needs_ffmpeg
def test_write_tags_m4a(tmp_path: Path) -> None:
    path = tmp_path / "a.m4a"
    make_m4a(path)
    write_tags(path, TAGS, M4A_PROFILE)
    tags = MP4(path).tags
    assert tags["\xa9nam"] == ["Song"]
    assert tags["\xa9ART"] == ["Art"]
    assert tags["\xa9alb"] == ["Alb"]
    assert tags["aART"] == ["Various Artists"]
    assert tags["trkn"] == [(2, 5)]


@needs_ffmpeg
def test_write_tags_mp3_id3(tmp_path: Path) -> None:
    path = tmp_path / "a.mp3"
    make_audio(path, "-c:a", "libmp3lame")
    write_tags(path, TrackTags("Été", "Art", "Alb", "Various Artists", 2, 5), mp3_profile())
    tags = ID3(path)
    assert tags.version == (2, 3, 0)
    assert tags["TIT2"].text == ["Été"]
    assert tags["TPE1"].text == ["Art"]
    assert tags["TALB"].text == ["Alb"]
    assert tags["TPE2"].text == ["Various Artists"]
    assert tags["TRCK"].text == ["2/5"]


@needs_ffmpeg
def test_write_tags_opus_vorbis_comments(tmp_path: Path) -> None:
    path = tmp_path / "a.opus"
    make_audio(path, "-c:a", "libopus")
    write_tags(path, TAGS, OPUS_PROFILE)
    tags = OggOpus(path).tags
    assert tags["title"] == ["Song"]
    assert tags["artist"] == ["Art"]
    assert tags["album"] == ["Alb"]
    assert tags["albumartist"] == ["Various Artists"]
    assert tags["tracknumber"] == ["2"]
    assert tags["tracktotal"] == ["5"]


def test_write_tags_without_writer_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delitem(tagadapter._WRITERS, OutputFormat.MP3)
    with pytest.raises(UnsupportedTagFormatError, match="mp3"):
        write_tags(tmp_path / "a.mp3", TAGS, mp3_profile())


TRACKLIST = Tracklist((Track(1, 0, 3, "One?", "A"), Track(2, 3, 5.9, "Two", "B")))


@needs_ffmpeg
def test_export_library(tmp_path: Path) -> None:
    source = tmp_path / "src.m4a"
    make_m4a(source)
    out = tmp_path / "lib"
    created = export_library(source, TRACKLIST, "My: Album", out)
    assert [p.relative_to(out).as_posix() for p in created] == [
        "Various Artists/My_ Album/01 - One_.m4a",
        "Various Artists/My_ Album/02 - Two.m4a",
    ]
    assert MP4(created[1]).tags["\xa9ART"] == ["B"]
    with pytest.raises(FileExistsError):
        export_library(source, TRACKLIST, "My: Album", out)


@needs_ffmpeg
def test_export_library_mp3_reencodes_and_tags(tmp_path: Path) -> None:
    source = tmp_path / "src.m4a"
    make_m4a(source)
    out = tmp_path / "lib"
    created = export_library(source, TRACKLIST, "Album", out, mp3_profile("128k"))
    assert [p.suffix for p in created] == [".mp3", ".mp3"]
    assert ID3(created[1])["TIT2"].text == ["Two"]
    assert ID3(created[1])["TRCK"].text == ["2/2"]


@needs_ffmpeg
def test_export_library_opus_remuxes_webm_and_tags(tmp_path: Path) -> None:
    source = tmp_path / "src.webm"
    make_audio(source, "-c:a", "libopus")
    out = tmp_path / "lib"
    created = export_library(source, TRACKLIST, "Album", out, OPUS_PROFILE)
    assert [p.suffix for p in created] == [".opus", ".opus"]
    audio = OggOpus(created[0])
    assert audio.tags["title"] == ["One?"]
    assert audio.info.length == pytest.approx(3, abs=0.1)


@needs_ffmpeg
def test_export_library_rejects_a_source_with_the_wrong_codec(tmp_path: Path) -> None:
    source = tmp_path / "src.m4a"
    make_m4a(source)
    out = tmp_path / "lib"
    with pytest.raises(ValueError, match="aac codec.*opus"):
        export_library(source, TRACKLIST, "Album", out, OPUS_PROFILE)
    assert not out.exists()
