"""Validated data models used by the pure core."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class Track:
    """One track in a compilation; start and end are measured in seconds."""

    number: int
    start: float
    end: float
    title: str
    artist: str

    def __post_init__(self) -> None:
        if isinstance(self.number, bool) or not isinstance(self.number, int) or self.number < 1:
            raise ValueError("Track number must be a positive integer.")
        for name, value in (("start", self.start), ("end", self.end)):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"Track {name} must be a number of seconds.")
            if not isfinite(value) or value < 0:
                raise ValueError(f"Track {name} must be finite and non-negative.")
        if self.start >= self.end:
            raise ValueError("Track start must be earlier than its end.")
        if not isinstance(self.title, str) or not isinstance(self.artist, str):
            raise ValueError("Track title and artist must be strings.")
        
    def asdict(self) -> dict:
        return {
            'number': self.number,
            'start': self.start, 
            'end': self.end, 
            'title': self.title,
            'artist': self.artist
        }


@dataclass(frozen=True, slots=True)
class Tracklist:
    """A chronologically ordered, non-overlapping collection of tracks."""

    tracks: tuple[Track, ...]

    def __post_init__(self) -> None:
        tracks = tuple(self.tracks)
        if not tracks:
            raise ValueError("A tracklist must contain at least one track.")
        if any(not isinstance(track, Track) for track in tracks):
            raise TypeError("Every tracklist entry must be a Track.")
        for expected_number, track in enumerate(tracks, start=1):
            if track.number != expected_number:
                raise ValueError("Track numbers must be consecutive and start at 1.")
            if expected_number > 1 and tracks[expected_number - 2].end > track.start:
                raise ValueError("Tracks must not overlap and must be ordered by start time.")
        object.__setattr__(self, "tracks", tracks)

    def asdict(self):
        return {
            'tracks' : [track.asdict() for track in self.tracks]
        }
