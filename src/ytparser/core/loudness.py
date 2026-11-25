"""Short-term loudness of a signal: RMS energy per window, in dBFS."""

from dataclasses import dataclass

import numpy as np

from ytparser.core.signal import AudioSignal

# En dessous de ce plancher, on écrit -120 dBFS au lieu de -inf (log de zéro)
SILENCE_FLOOR_DBFS = -120.0


@dataclass(frozen=True)
class LoudnessCurve:
    """Loudness per window: values in dBFS and the start time (s) of each window."""

    times: np.ndarray
    dbfs: np.ndarray
    window_seconds: float


def rms_dbfs(signal: AudioSignal, window_seconds: float = 0.05) -> LoudnessCurve:
    """Compute the RMS level of consecutive, non-overlapping windows, in dBFS.

    0 dBFS is a full-scale square wave (RMS 1.0); a full-scale sine is about -3 dBFS.
    A trailing partial window is dropped.
    """
    window = round(window_seconds * signal.sample_rate)
    if window < 1:
        raise ValueError("window_seconds is shorter than one sample.")
    count = len(signal.samples) // window
    # Une ligne par fenêtre : (count, window)
    frames = signal.samples[: count * window].reshape(count, window).astype(np.float64)
    rms = np.sqrt(np.mean(frames**2, axis=1))
    with np.errstate(divide="ignore"):
        dbfs = 20.0 * np.log10(rms)
    dbfs = np.maximum(dbfs, SILENCE_FLOOR_DBFS)
    times = np.arange(count) * (window / signal.sample_rate)
    return LoudnessCurve(times, dbfs, window / signal.sample_rate)
