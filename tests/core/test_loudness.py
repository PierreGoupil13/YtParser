import numpy as np
import pytest

from ytparser.core.loudness import SILENCE_FLOOR_DBFS, rms_dbfs
from ytparser.core.signal import AudioSignal

RATE = 8_000


def _sine(amplitude: float, seconds: float) -> np.ndarray:
    t = np.arange(round(seconds * RATE)) / RATE
    return (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


def test_full_scale_sine_is_minus_3_dbfs() -> None:
    curve = rms_dbfs(AudioSignal(_sine(1.0, 1.0), RATE))

    assert curve.dbfs == pytest.approx(-3.01, abs=0.05)


def test_halving_amplitude_lowers_level_by_6_db() -> None:
    loud = rms_dbfs(AudioSignal(_sine(0.8, 1.0), RATE)).dbfs[0]
    quiet = rms_dbfs(AudioSignal(_sine(0.4, 1.0), RATE)).dbfs[0]

    assert loud - quiet == pytest.approx(6.02, abs=0.05)


def test_digital_silence_is_clamped_to_floor() -> None:
    curve = rms_dbfs(AudioSignal(np.zeros(RATE, dtype=np.float32), RATE))

    assert (curve.dbfs == SILENCE_FLOOR_DBFS).all()


def test_windows_and_times() -> None:
    signal = AudioSignal(np.concatenate([_sine(0.5, 1.0), np.zeros(RATE)]), RATE)

    curve = rms_dbfs(signal, window_seconds=0.5)

    assert len(curve.dbfs) == 4
    assert curve.times.tolist() == [0.0, 0.5, 1.0, 1.5]
    assert curve.dbfs[0] > -10
    assert curve.dbfs[3] == SILENCE_FLOOR_DBFS


def test_partial_trailing_window_is_dropped() -> None:
    curve = rms_dbfs(AudioSignal(_sine(0.5, 1.05), RATE), window_seconds=0.5)

    assert len(curve.dbfs) == 2


def test_window_shorter_than_a_sample_is_rejected() -> None:
    with pytest.raises(ValueError, match="shorter"):
        rms_dbfs(AudioSignal(_sine(0.5, 1.0), RATE), window_seconds=0.00001)
