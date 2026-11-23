import pytest

from ytparser.core.cutplan import check_tracklist_fits, track_filenames
from ytparser.core.models import Track, Tracklist


def make_tracklist(*bounds: tuple[float, float]) -> Tracklist:
    return Tracklist(
        tuple(
            Track(number, start, end, f"Title {number}", "Artist")
            for number, (start, end) in enumerate(bounds, start=1)
        )
    )


def test_track_filenames_are_zero_padded_in_track_order() -> None:
    tracklist = make_tracklist((0, 10), (10, 20), (20, 30))

    assert track_filenames(tracklist, ".mp3") == ("01.mp3", "02.mp3", "03.mp3")


def test_track_filenames_widen_padding_beyond_99_tracks() -> None:
    tracklist = make_tracklist(*((n, n + 1) for n in range(100)))

    names = track_filenames(tracklist, ".m4a")

    assert names[0] == "001.m4a"
    assert names[-1] == "100.m4a"
    assert sorted(names) == list(names)


@pytest.mark.parametrize("suffix", ["", ".", "mp3"])
def test_track_filenames_require_an_extension(suffix: str) -> None:
    with pytest.raises(ValueError, match="extension"):
        track_filenames(make_tracklist((0, 10)), suffix)


@pytest.mark.parametrize(
    "last_end",
    [
        pytest.param(80.0, id="ends-before-audio-end"),
        pytest.param(100.0, id="ends-at-audio-end"),
        pytest.param(101.0, id="ends-within-tolerance"),
    ],
)
def test_check_tracklist_fits_accepts_matching_audio(last_end: float) -> None:
    check_tracklist_fits(make_tracklist((0, 50), (50, last_end)), audio_duration=100.0)


@pytest.mark.parametrize(
    "last_track",
    [
        pytest.param((50, 101.5), id="ends-beyond-tolerance"),
        pytest.param((100, 100.5), id="starts-at-audio-end"),
    ],
)
def test_check_tracklist_fits_rejects_tracks_beyond_audio(
    last_track: tuple[float, float],
) -> None:
    with pytest.raises(ValueError, match="Track 2"):
        check_tracklist_fits(make_tracklist((0, 50), last_track), audio_duration=100.0)
