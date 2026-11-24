"""Pure rules for tags and library layout: album artist, Windows-safe names, relative paths."""

import re
from dataclasses import dataclass
from pathlib import PurePath

from ytparser.core.models import Track, Tracklist

VARIOUS_ARTISTS = "Various Artists"

_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{n}" for n in range(1, 10)}
    | {f"LPT{n}" for n in range(1, 10)}
)


@dataclass(frozen=True, slots=True)
class TrackTags:
    """Everything a tag writer needs for one file; independent of the audio format."""

    title: str
    artist: str
    album: str
    album_artist: str
    number: int
    total: int


def album_artist(tracklist: Tracklist) -> str:
    """Return the single artist of the compilation, or "Various Artists" if they differ."""
    artists = {track.artist.strip() for track in tracklist.tracks}
    return next(iter(artists)) if len(artists) == 1 else VARIOUS_ARTISTS


def tags_for(track: Track, tracklist: Tracklist, album: str) -> TrackTags:
    return TrackTags(
        title=track.title,
        artist=track.artist,
        album=album,
        album_artist=album_artist(tracklist),
        number=track.number,
        total=len(tracklist.tracks),
    )


def sanitize_component(name: str, fallback: str = "Unknown") -> str:
    """Make text usable as one Windows file or folder name (forbidden characters replaced)."""
    cleaned = _FORBIDDEN.sub("_", name)
    cleaned = " ".join(cleaned.split())
    # Windows refuses names ending with a dot or a space
    cleaned = cleaned.rstrip(". ")
    if not cleaned:
        return fallback
    if cleaned.split(".")[0].rstrip().upper() in _RESERVED_NAMES:
        cleaned = f"_{cleaned}"
    return cleaned[:150].rstrip(". ")


def library_path(tags: TrackTags, suffix: str) -> PurePath:
    """Relative path Artist/Album/NN - Title.ext, with NN padded to the album size."""
    width = max(2, len(str(tags.total)))
    filename = sanitize_component(f"{tags.number:0{width}d} - {tags.title}") + suffix
    return PurePath(
        sanitize_component(tags.album_artist, "Unknown Artist"),
        sanitize_component(tags.album, "Unknown Album"),
        filename,
    )
