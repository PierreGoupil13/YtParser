"""Tag adapter: write metadata into audio files. One writer per format, chosen by extension."""

from collections.abc import Callable
from pathlib import Path

from mutagen.mp4 import MP4

from ytparser.core.naming import TrackTags


class UnsupportedTagFormatError(ValueError):
    """No tag writer exists yet for this file extension."""


def write_tags(path: Path, tags: TrackTags) -> None:
    writer = _WRITERS.get(path.suffix.lower())
    if writer is None:
        raise UnsupportedTagFormatError(
            f"Tagging {path.suffix or 'this file type'} is not supported yet (only .m4a)."
        )
    writer(path, tags)


def _write_m4a(path: Path, tags: TrackTags) -> None:
    # Un fichier MP4 est une suite d'atomes ; les tags vivent dans moov/udta/meta/ilst
    audio = MP4(path)
    audio["\xa9nam"] = [tags.title]
    audio["\xa9ART"] = [tags.artist]
    audio["\xa9alb"] = [tags.album]
    audio["aART"] = [tags.album_artist]
    audio["trkn"] = [(tags.number, tags.total)]
    audio.save()


_WRITERS: dict[str, Callable[[Path, TrackTags], None]] = {".m4a": _write_m4a}
