import pytest

from ytparser.core.plan import (
    UNKNOWN_ARTIST,
    build_tracklist,
    build_tracklist_from_cut_points,
)
from ytparser.core.timestamps import TimestampEntry


def test_each_track_ends_where_the_next_starts_and_last_ends_at_duration() -> None:
    entries = [
        TimestampEntry(0, "A - One"),
        TimestampEntry(60, "B - Two"),
        TimestampEntry(150, "C - Three"),
    ]

    tracklist = build_tracklist(entries, duration=300)

    assert [(t.start, t.end) for t in tracklist.tracks] == [(0, 60), (60, 150), (150, 300)]
    assert [(t.number, t.artist, t.title) for t in tracklist.tracks] == [
        (1, "A", "One"),
        (2, "B", "Two"),
        (3, "C", "Three"),
    ]


def test_missing_titles_become_numbered_and_use_the_default_artist() -> None:
    entries = [TimestampEntry(0, ""), TimestampEntry(60, "")]

    tracklist = build_tracklist(entries, duration=120, default_artist="Daft Punk")

    assert [(t.artist, t.title) for t in tracklist.tracks] == [
        ("Daft Punk", "Titre 1"),
        ("Daft Punk", "Titre 2"),
    ]


def test_label_artist_wins_over_default_artist_and_title_only_uses_default() -> None:
    entries = [TimestampEntry(0, "Other - Song"), TimestampEntry(60, "Song 2")]

    tracklist = build_tracklist(entries, duration=120, default_artist="Me")

    assert [(t.artist, t.title) for t in tracklist.tracks] == [("Other", "Song"), ("Me", "Song 2")]


def test_without_any_artist_a_placeholder_is_used() -> None:
    tracklist = build_tracklist([TimestampEntry(0, "Song")], duration=10, default_artist="  ")

    assert tracklist.tracks[0].artist == UNKNOWN_ARTIST


def test_entries_are_sorted_and_duplicate_starts_keep_the_first() -> None:
    entries = [TimestampEntry(60, "B"), TimestampEntry(0, "A"), TimestampEntry(60, "Dup")]

    tracklist = build_tracklist(entries, duration=120)

    assert [(t.title, t.start, t.end) for t in tracklist.tracks] == [("A", 0, 60), ("B", 60, 120)]


def test_entries_at_or_after_the_duration_are_dropped() -> None:
    entries = [TimestampEntry(0, "A"), TimestampEntry(100, "Past the end")]

    tracklist = build_tracklist(entries, duration=100)

    assert [(t.title, t.end) for t in tracklist.tracks] == [("A", 100)]


def test_no_entry_inside_the_video_raises() -> None:
    with pytest.raises(ValueError, match="inside the video duration"):
        build_tracklist([TimestampEntry(500, "Late")], duration=100)


def test_cut_points_become_generic_tracks() -> None:
    tracklist = build_tracklist_from_cut_points([100.0, 250.5], duration=400)

    assert [(t.title, t.start, t.end) for t in tracklist.tracks] == [
        ("Titre 1", 0.0, 100.0),
        ("Titre 2", 100.0, 250.5),
        ("Titre 3", 250.5, 400.0),
    ]
    assert {t.artist for t in tracklist.tracks} == {UNKNOWN_ARTIST}


def test_cut_points_too_close_to_a_neighbour_or_the_edges_are_dropped() -> None:
    # 5 s après le début, 105 s après le précédent (ok), 8 s avant la fin
    tracklist = build_tracklist_from_cut_points([5.0, 100.0, 110.0, 392.0], duration=400)

    assert [t.start for t in tracklist.tracks] == [0.0, 100.0]


def test_no_cut_point_gives_a_single_track() -> None:
    tracklist = build_tracklist_from_cut_points([], duration=300, default_artist="Me")

    assert len(tracklist.tracks) == 1
    assert tracklist.tracks[0].artist == "Me"
