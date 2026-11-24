"""Tag adapter: write metadata into audio files. One writer per format, chosen by profile."""

from collections.abc import Callable
from pathlib import Path

from mutagen.id3 import ID3, TALB, TIT2, TPE1, TPE2, TRCK, Encoding, ID3NoHeaderError
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus

from ytparser.core.download import OutputFormat
from ytparser.core.naming import TrackTags
from ytparser.core.profiles import OutputProfile


class UnsupportedTagFormatError(ValueError):
    """No tag writer exists yet for this output format."""


def write_tags(path: Path, tags: TrackTags, profile: OutputProfile) -> None:
    writer = _WRITERS.get(profile.format)
    if writer is None:
        raise UnsupportedTagFormatError(
            f"Tagging {profile.format.value} is not supported yet "
            f"(supported: {', '.join(fmt.value for fmt in _WRITERS)})."
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


def _write_mp3(path: Path, tags: TrackTags) -> None:
    try:
        audio = ID3(path)
    except ID3NoHeaderError:
        audio = ID3()
    # ID3v2.3 est lu par tous les lecteurs courants ; add() remplace une trame de même type
    audio.add(TIT2(encoding=Encoding.UTF16, text=tags.title))
    audio.add(TPE1(encoding=Encoding.UTF16, text=tags.artist))
    audio.add(TALB(encoding=Encoding.UTF16, text=tags.album))
    audio.add(TPE2(encoding=Encoding.UTF16, text=tags.album_artist))
    audio.add(TRCK(encoding=Encoding.UTF16, text=f"{tags.number}/{tags.total}"))
    audio.save(path, v2_version=3)


def _write_opus(path: Path, tags: TrackTags) -> None:
    # Un fichier Ogg Opus porte des commentaires Vorbis : paires NOM=valeur
    audio = OggOpus(path)
    audio["title"] = [tags.title]
    audio["artist"] = [tags.artist]
    audio["album"] = [tags.album]
    audio["albumartist"] = [tags.album_artist]
    audio["tracknumber"] = [str(tags.number)]
    audio["tracktotal"] = [str(tags.total)]
    audio.save()


_WRITERS: dict[OutputFormat, Callable[[Path, TrackTags], None]] = {
    OutputFormat.M4A: _write_m4a,
    OutputFormat.MP3: _write_mp3,
    OutputFormat.OPUS: _write_opus,
}
