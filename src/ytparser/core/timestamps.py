"""Extract (start time, label) pairs from raw text such as a video description."""

import re
from typing import NamedTuple


class TimestampEntry(NamedTuple):
    """A timestamp found in a text; start is measured in seconds."""

    start: float
    label: str


_TIME = r"(?:(?P<h>\d{1,2}):)?(?P<m>\d{1,2}):(?P<s>\d{2})(?!\d|:\d)"
_OPEN = r"[\[(]?"
_CLOSE = r"[\])]?"
_SEPARATORS = " \t-–—:|~>"

# Timestamp at the start of the line, after an optional bullet or "1." / "01)" numbering.
_LEADING = re.compile(rf"^\s*(?:[-*•]\s*)?(?:\d{{1,3}}[.)]\s+)?{_OPEN}{_TIME}{_CLOSE}(?P<rest>.*)$")
# Second timestamp right after the first one: "0:00 - 3:45 Title" is a range, not a title.
_RANGE_END = re.compile(rf"^\s*[-–—~]+\s*{_OPEN}{_TIME}{_CLOSE}")
# Fallback: timestamp at the end of the line, "Artist - Title 3:45".
_TRAILING = re.compile(rf"^(?P<label>.*\S)\s+{_OPEN}{_TIME}{_CLOSE}\s*$")


def parse_timestamps(text: str) -> list[TimestampEntry]:
    """Return one entry per line holding a valid timestamp, in order of appearance.

    Supports ``m:ss`` and ``h:mm:ss``, optional brackets, numbering, ranges and
    a timestamp placed at the end of the line. The label may be empty.
    """
    entries: list[TimestampEntry] = []
    for line in text.splitlines():
        entry = _parse_line(line)
        if entry is not None:
            entries.append(entry)
    return entries


def _parse_line(line: str) -> TimestampEntry | None:
    match = _LEADING.match(line)
    if match is not None:
        seconds = _to_seconds(match)
        if seconds is None:
            return None
        rest = _RANGE_END.sub("", match["rest"], count=1)
        return TimestampEntry(seconds, rest.strip(_SEPARATORS))

    match = _TRAILING.match(line)
    if match is not None:
        seconds = _to_seconds(match)
        if seconds is not None:
            return TimestampEntry(seconds, match["label"].strip(_SEPARATORS))
    return None


def _to_seconds(match: re.Match[str]) -> float | None:
    hours = int(match["h"]) if match["h"] is not None else None
    minutes, seconds = int(match["m"]), int(match["s"])
    if seconds >= 60 or (hours is not None and minutes >= 60):
        return None
    return float((hours or 0) * 3600 + minutes * 60 + seconds)
