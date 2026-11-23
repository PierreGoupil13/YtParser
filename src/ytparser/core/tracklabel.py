"""Split a timestamp label such as "01. Artist - Title" into artist and title."""

import re
from typing import NamedTuple


class TrackLabel(NamedTuple):
    """Result of splitting a label; artist is None when it cannot be told apart."""

    artist: str | None
    title: str


# Leading track number: "1.", "01)", "#1", "#1 -", "(1)", "[1]", or "01 -" (at most 2 digits,
# so that artists such as "311 - Down" or "1999 - Prince" are left alone).
_NUMBERING = re.compile(
    r"^\s*(?:"
    r"#\s*\d{1,3}(?:\s*[.):\-–—])?\s+"
    r"|\(\d{1,3}\)\s*"
    r"|\[\d{1,3}\]\s*"
    r"|\d{1,3}[.)]\s+"
    r"|\d{1,2}\s*[-–—:]\s+"
    r")"
)
# A hyphen needs whitespace on one side at least ("Jay-Z" is not a separator);
# en and em dashes are unambiguous.
_SEPARATOR = re.compile(r"\s+-\s*|\s*-\s+|\s*[–—―‒]\s*")


def split_artist_title(label: str) -> TrackLabel:
    """Split "Artist - Title" and its common variants, falling back on the raw label.

    Only the first separator counts, so "Artist - Title - Live" keeps "Title - Live"
    as the title. When no artist can be identified, the whole cleaned label is the title.
    """
    cleaned = _clean(_NUMBERING.sub("", label, count=1)) or _clean(label)

    parts = _SEPARATOR.split(cleaned, maxsplit=1)
    if len(parts) == 2 and parts[0] and parts[1]:
        return TrackLabel(parts[0], parts[1])

    # Dangling separator ("Artist -" or "- Title"): keep the text, drop the separator.
    return TrackLabel(None, " ".join(part for part in parts if part))


def _clean(text: str) -> str:
    return " ".join(text.split())
