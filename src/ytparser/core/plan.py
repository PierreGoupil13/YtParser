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


# Une piste plus courte que cela est presque sûrement un creux interne, pas un morceau
MIN_TRACK_SECONDS = 20.0


def build_tracklist_from_cut_points(
    cut_points: list[float], duration: float, default_artist: str | None = None
) -> Tracklist:
    """Build a tracklist from boundaries found in the audio (no titles available).

    The first track starts at 0. A boundary closer than MIN_TRACK_SECONDS to the previous
    start or to the end is ignored. Tracks are titled "Titre N".
    """
    starts = [0.0]
    for point in sorted(cut_points):
        if point - starts[-1] >= MIN_TRACK_SECONDS and duration - point >= MIN_TRACK_SECONDS:
            starts.append(round(point, 3))
    return build_tracklist(
        [TimestampEntry(start, "") for start in starts], duration, default_artist
    )
