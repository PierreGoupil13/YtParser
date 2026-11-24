from pathlib import PurePath

import pytest

from ytparser.core.models import Track, Tracklist
from ytparser.core.naming import (
    VARIOUS_ARTISTS,
    album_artist,
    library_path,
    sanitize_component,
    tags_for,
)


def make(*artists: str) -> Tracklist:
    return Tracklist(
        tuple(Track(i, i * 10.0, i * 10.0 + 10, f"T{i}", a) for i, a in enumerate(artists, 1))
    )


def test_album_artist_single() -> None:
    assert album_artist(make("A", "A", " A ")) == "A"


def test_album_artist_various() -> None:
    assert album_artist(make("A", "B")) == VARIOUS_ARTISTS


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('What? "Yes": a/b', "What_ _Yes__ a_b"),
        ("a<b>c|d*e\\f", "a_b_c_d_e_f"),
        ("Trailing...  ", "Trailing"),
        ("CON", "_CON"),
        ("", "Unknown"),
        ("???", "___"),
    ],
)
def test_sanitize_component(raw: str, expected: str) -> None:
    assert sanitize_component(raw) == expected


def test_library_path_with_forbidden_characters() -> None:
    tracklist = make("AC/DC", "AC/DC")
    tags = tags_for(tracklist.tracks[0], tracklist, 'Best: "Of"?')
    path = library_path(tags, ".m4a")
    assert path == PurePath("AC_DC", "Best_ _Of__", "01 - T1.m4a")
    assert not any(c in str(path.name) for c in '<>:"/\\|?*')
