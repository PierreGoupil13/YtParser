import pytest

from ytparser.core.tracklabel import TrackLabel, split_artist_title


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Daft Punk - One More Time", ("Daft Punk", "One More Time")),
        ("Daft Punk – One More Time", ("Daft Punk", "One More Time")),
        ("Daft Punk — One More Time", ("Daft Punk", "One More Time")),
        ("Daft Punk–One More Time", ("Daft Punk", "One More Time")),
        ("Daft Punk- One More Time", ("Daft Punk", "One More Time")),
        ("Daft Punk -One More Time", ("Daft Punk", "One More Time")),
        ("  Daft   Punk  -   One More Time  ", ("Daft Punk", "One More Time")),
        ("1. Daft Punk - One More Time", ("Daft Punk", "One More Time")),
        ("01) Daft Punk - One More Time", ("Daft Punk", "One More Time")),
        ("01 - Daft Punk - One More Time", ("Daft Punk", "One More Time")),
        ("#7 Daft Punk - One More Time", ("Daft Punk", "One More Time")),
        ("#7 - Daft Punk - One More Time", ("Daft Punk", "One More Time")),
        ("(07) Daft Punk - One More Time", ("Daft Punk", "One More Time")),
        ("[07] Daft Punk - One More Time", ("Daft Punk", "One More Time")),
        ("Wu-Tang Clan - Triumph", ("Wu-Tang Clan", "Triumph")),
        ("Artist - Title - Live", ("Artist", "Title - Live")),
        ("Artist - Song (feat. Someone)", ("Artist", "Song (feat. Someone)")),
        ("311 - Down", ("311", "Down")),
        ("50 Cent - In Da Club", ("50 Cent", "In Da Club")),
    ],
)
def test_split_artist_title_splits_known_variants(label: str, expected: tuple[str, str]) -> None:
    assert split_artist_title(label) == TrackLabel(*expected)


@pytest.mark.parametrize(
    ("label", "title"),
    [
        ("One More Time", "One More Time"),
        ("Jay-Z", "Jay-Z"),
        ("Intro", "Intro"),
        ("", ""),
        ("1. One More Time", "One More Time"),
        ("01 - One More Time", "One More Time"),
        ("Artist -", "Artist"),
        ("- Title", "Title"),
        ("1999", "1999"),
        ("01", "01"),
    ],
)
def test_split_artist_title_falls_back_on_the_title_only(label: str, title: str) -> None:
    assert split_artist_title(label) == TrackLabel(None, title)
