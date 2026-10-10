import pytest

from ytparser.core.models import Track, Tracklist


def make_track(number: int, start: float, end: float) -> Track:
    return Track(number, start, end, f"Track {number}", "Artist")


def test_track_accepts_valid_boundaries() -> None:
    track = Track(1, 0, 12.5, "Title", "Artist")

    assert track.start == 0
    assert track.end == 12.5


@pytest.mark.parametrize(
    ("number", "start", "end"),
    [
        (0, 0, 10),
        (1, -1, 10),
        (1, 10, 10),
        (1, 11, 10),
        (1, 0, float("inf")),
        (1, 0, float("nan")),
    ],
)
def test_track_rejects_invalid_number_or_boundaries(number: int, start: float, end: float) -> None:
    with pytest.raises(ValueError):
        make_track(number, start, end)


def test_tracklist_accepts_consecutive_adjacent_tracks() -> None:
    tracklist = Tracklist((make_track(1, 0, 10), make_track(2, 10, 20)))

    assert [track.number for track in tracklist.tracks] == [1, 2]


def test_tracklist_copies_track_sequence_to_immutable_tuple() -> None:
    tracks = [make_track(1, 0, 10)]

    tracklist = Tracklist(tracks)
    tracks.clear()

    assert len(tracklist.tracks) == 1


@pytest.mark.parametrize(
    "tracks",
    [
        (),
        (make_track(2, 0, 10),),
        (make_track(1, 0, 10), make_track(3, 10, 20)),
        (make_track(1, 0, 12), make_track(2, 10, 20)),
        (make_track(1, 10, 20), make_track(2, 0, 10)),
    ],
)
def test_tracklist_rejects_empty_inconsistent_or_overlapping_tracks(
    tracks: tuple[Track, ...],
) -> None:
    with pytest.raises(ValueError):
        Tracklist(tracks)
