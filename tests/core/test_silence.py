import numpy as np
import pytest

from ytparser.core.loudness import LoudnessCurve, rms_dbfs
from ytparser.core.signal import AudioSignal
from ytparser.core.silence import Silence, cut_points, detect_silences

RATE = 8_000


def _curve(levels: list[float], window: float = 0.5) -> LoudnessCurve:
    return LoudnessCurve(np.arange(len(levels)) * window, np.array(levels, dtype=float), window)


def _tone(seconds: float, amplitude: float = 0.5) -> np.ndarray:
    t = np.arange(round(seconds * RATE)) / RATE
    return (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


def test_silence_between_two_tones_is_found_with_its_middle() -> None:
    samples = np.concatenate([_tone(2), np.zeros(2 * RATE, dtype=np.float32), _tone(2)])
    curve = rms_dbfs(AudioSignal(samples, RATE), window_seconds=0.05)

    silences = detect_silences(curve, threshold_dbfs=-50, min_duration=1.0)

    assert len(silences) == 1
    assert silences[0].start == pytest.approx(2.0, abs=0.05)
    assert silences[0].end == pytest.approx(4.0, abs=0.05)
    assert cut_points(silences) == pytest.approx([3.0], abs=0.05)


def test_short_dip_is_ignored() -> None:
    curve = _curve([-10, -10, -90, -90, -10, -10])  # creux de 1,0 s

    assert detect_silences(curve, -50, min_duration=1.5) == []
    assert len(detect_silences(curve, -50, min_duration=1.0)) == 1


def test_threshold_is_strict_and_selects_depth() -> None:
    curve = _curve([-10, -45, -45, -10, -80, -80, -10])

    assert len(detect_silences(curve, threshold_dbfs=-40, min_duration=0.5)) == 2
    assert detect_silences(curve, threshold_dbfs=-45, min_duration=0.5) == [Silence(2.0, 3.0)]


def test_silence_at_both_ends_is_detected() -> None:
    curve = _curve([-90, -90, -10, -10, -90, -90])

    assert detect_silences(curve, -50, 1.0) == [Silence(0.0, 1.0), Silence(2.0, 3.0)]


def test_no_silence_and_all_silence() -> None:
    assert detect_silences(_curve([-10, -12, -11]), -50, 0.5) == []
    assert detect_silences(_curve([-90, -90, -90]), -50, 0.5) == [Silence(0.0, 1.5)]


def test_negative_min_duration_is_rejected() -> None:
    with pytest.raises(ValueError, match="negative"):
        detect_silences(_curve([-90]), -50, -1)
