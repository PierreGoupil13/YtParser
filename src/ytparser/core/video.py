"""Pure description of what is known about a video, independent of where it comes from."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Chapter:
    """A YouTube chapter; start is measured in seconds."""

    start: float
    title: str


@dataclass(frozen=True, slots=True)
class Comment:
    text: str
    like_count: int = 0


@dataclass(frozen=True, slots=True)
class VideoInfo:
    """Metadata used to build a tracklist; duration is measured in seconds."""

    title: str
    duration: float
    description: str = ""
    chapters: tuple[Chapter, ...] = ()
    comments: tuple[Comment, ...] = ()
