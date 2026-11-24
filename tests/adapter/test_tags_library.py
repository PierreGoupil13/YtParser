import shutil
import subprocess
from pathlib import Path

import pytest
from mutagen.mp4 import MP4

from ytparser.adapters.libraryadapter import export_library
from ytparser.adapters.tagadapter import UnsupportedTagFormatError, write_tags
from ytparser.core.models import Track, Tracklist
from ytparser.core.naming import TrackTags

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg missing")


def make_m4a(path: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=duration=6", "-c:a", "aac", str(path)],
        check=True,
    )


@needs_ffmpeg
def test_write_tags_m4a(tmp_path: Path) -> None:
    path = tmp_path / "a.m4a"
    make_m4a(path)
    write_tags(path, TrackTags("Song", "Art", "Alb", "Various Artists", 2, 5))
    tags = MP4(path).tags
    assert tags["\xa9nam"] == ["Song"]
    assert tags["\xa9ART"] == ["Art"]
    assert tags["\xa9alb"] == ["Alb"]
    assert tags["aART"] == ["Various Artists"]
    assert tags["trkn"] == [(2, 5)]


def test_write_tags_unsupported_format(tmp_path: Path) -> None:
    with pytest.raises(UnsupportedTagFormatError):
        write_tags(tmp_path / "a.mp3", TrackTags("t", "a", "b", "c", 1, 1))


@needs_ffmpeg
def test_export_library(tmp_path: Path) -> None:
    source = tmp_path / "src.m4a"
    make_m4a(source)
    tracklist = Tracklist(
        (Track(1, 0, 3, "One?", "A"), Track(2, 3, 5.9, "Two", "B")),
    )
    out = tmp_path / "lib"
    created = export_library(source, tracklist, "My: Album", out)
    assert [p.relative_to(out).as_posix() for p in created] == [
        "Various Artists/My_ Album/01 - One_.m4a",
        "Various Artists/My_ Album/02 - Two.m4a",
    ]
    assert MP4(created[1]).tags["\xa9ART"] == ["B"]
    with pytest.raises(FileExistsError):
        export_library(source, tracklist, "My: Album", out)
