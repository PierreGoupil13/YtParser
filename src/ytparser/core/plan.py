"""Turn timestamp entries into a validated tracklist."""

from ytparser.core.models import Track, Tracklist
from ytparser.core.timestamps import TimestampEntry
from ytparser.core.tracklabel import split_artist_title

UNKNOWN_ARTIST = "Artiste inconnu"


def build_tracklist(
    entries: tuple[TimestampEntry, ...] | list[TimestampEntry],
    duration: float,
    default_artist: str | None = None,
) -> Tracklist:
    """Build a tracklist where each track ends where the next starts.

    The last track ends at duration. Entries are sorted by time; those sharing a start time
    (the first one wins) or starting at or after duration are dropped. An artist found in a
    label wins over default_artist; a missing title becomes "Titre N".
    """
    usable: dict[float, TimestampEntry] = {}
    for entry in sorted(entries, key=lambda e: e.start):
        if entry.start < duration:
            usable.setdefault(entry.start, entry)
    if not usable:
        raise ValueError("No timestamp falls inside the video duration.")

    ordered = list(usable.values())
    ends = [entry.start for entry in ordered[1:]] + [duration]
    fallback_artist = (default_artist or "").strip() or UNKNOWN_ARTIST

    tracks = []
    for number, (entry, end) in enumerate(zip(ordered, ends, strict=True), start=1):
        label = split_artist_title(entry.label)
        tracks.append(
            Track(
                number=number,
                start=entry.start,
                end=end,
                title=label.title or f"Titre {number}",
                artist=label.artist or fallback_artist,
            )
        )
    return Tracklist(tuple(tracks))
