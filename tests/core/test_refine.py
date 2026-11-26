import numpy as np
import pytest

from ytparser.core.loudness import LoudnessCurve
from ytparser.core.models import Track, Tracklist
from ytparser.core.refine import refine_boundary, refine_tracklist

WINDOW = 0.05


def _curve(segments: list[tuple[float, float]]) -> LoudnessCurve:
    """Loudness built from (seconds, dBFS) segments."""
    levels = np.concatenate([np.full(round(s / WINDOW), db) for s, db in segments])
    return LoudnessCurve(np.arange(len(levels)) * WINDOW, levels, WINDOW)


def _gap_curve() -> LoudnessCurve:
    # Musique jusqu'à 100 s, creux de 100 s à 106 s, nouvelle musique ensuite
    return _curve([(100, -20), (6, -80), (94, -20)])


def test_early_timestamp_moves_to_the_arrival_of_the_next_track() -> None:
    refined, method = refine_boundary(_gap_curve(), [], moment=95.0)

    assert method == "silence"
    assert refined == pytest.approx(106.0, abs=0.6)


def test_position_chooses_between_start_of_gap_and_arrival() -> None:
    curve = _gap_curve()

    start, _ = refine_boundary(curve, [], 95.0, position=0.0)
    middle, _ = refine_boundary(curve, [], 95.0, position=0.5)

    assert start == pytest.approx(100.0, abs=0.6)
    assert middle == pytest.approx(103.0, abs=0.6)


def test_late_timestamp_moves_back_into_the_gap() -> None:
    refined, _ = refine_boundary(_gap_curve(), [], moment=110.0)

    assert refined == pytest.approx(106.0, abs=0.6)


def test_slow_fade_out_ends_at_the_return_of_the_sound() -> None:
    # Fondu de 20 dB à -80 dB sur 10 s, puis quasi-silence 4 s, puis la musique
    fade = np.linspace(-20, -80, round(10 / WINDOW))
    levels = np.concatenate([np.full(1000, -20.0), fade, np.full(80, -80.0), np.full(1000, -20.0)])
    curve = LoudnessCurve(np.arange(len(levels)) * WINDOW, levels, WINDOW)

    refined, method = refine_boundary(curve, [], moment=62.0, radius=12)

    assert method == "silence"
    assert refined == pytest.approx(50 + 10 + 4, abs=0.8)


def test_no_dip_falls_back_on_the_nearest_spectral_candidate() -> None:
    curve = _curve([(200, -20)])

    assert refine_boundary(curve, [60.0, 105.0, 180.0], 100.0) == (105.0, "spectral")


def test_no_dip_and_no_candidate_keeps_the_timestamp() -> None:
    assert refine_boundary(_curve([(200, -20)]), [10.0], 100.0) == (100.0, "unchanged")


def test_invalid_position_is_rejected() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        refine_boundary(_gap_curve(), [], 95.0, position=1.5)


def _tracklist() -> Tracklist:
    return Tracklist(
        (
            Track(1, 0, 95, "A", "X"),
            Track(2, 95, 200, "B", "X"),
        )
    )


def test_tracklist_boundaries_move_together_and_edges_stay() -> None:
    refined, refinements = refine_tracklist(_tracklist(), _gap_curve(), [])

    first, second = refined.tracks
    assert first.start == 0
    assert first.end == second.start == pytest.approx(106.0, abs=0.6)
    assert second.end == 200
    assert (refinements[0].track, refinements[0].method) == (2, "silence")
    assert refinements[0].shift == pytest.approx(11.0, abs=0.6)


def test_a_boundary_that_would_break_the_order_is_ignored() -> None:
    # L'arrivée détectée (106 s) laisserait moins d'une seconde à la piste 1 (début 105,5 s)
    tracks = Tracklist((Track(1, 105.5, 108, "A", "X"), Track(2, 108, 200, "B", "X")))
    curve = _curve([(100, -20), (6, -80), (94, -20)])

    refined, refinements = refine_tracklist(tracks, curve, [], radius=12)

    assert refinements[0].method == "unchanged"
    assert refined.tracks[1].start == 108


def test_gap_left_by_hand_between_tracks_is_preserved() -> None:
    tracks = Tracklist((Track(1, 0, 90, "A", "X"), Track(2, 95, 200, "B", "X")))

    refined, _ = refine_tracklist(tracks, _gap_curve(), [])

    assert refined.tracks[0].end == 90
