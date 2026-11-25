"""Silence detection on a loudness curve."""

from dataclasses import dataclass

import numpy as np

from ytparser.core.loudness import LoudnessCurve


@dataclass(frozen=True)
class Silence:
    """A quiet stretch, in seconds. The cut point is its middle."""

    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def middle(self) -> float:
        return (self.start + self.end) / 2


def detect_silences(
    curve: LoudnessCurve, threshold_dbfs: float = -50.0, min_duration: float = 1.0
) -> list[Silence]:
    """Return the stretches where the level stays below threshold_dbfs for min_duration s.

    A window is quiet when its level is strictly below the threshold. Consecutive quiet
    windows form a run; runs shorter than min_duration are ignored (a short dip is not a gap).
    """
    if min_duration < 0:
        raise ValueError("min_duration must not be negative.")
    quiet = curve.dbfs < threshold_dbfs
    if not quiet.any():
        return []
    # Frontières des séquences : +1 là où "silencieux" commence, -1 là où il s'arrête
    padded = np.concatenate(([0], quiet.astype(np.int8), [0]))
    changes = np.diff(padded)
    starts = np.flatnonzero(changes == 1)
    stops = np.flatnonzero(changes == -1)
    silences = []
    for first, stop in zip(starts, stops, strict=True):
        start = float(curve.times[first])
        end = start + (stop - first) * curve.window_seconds
        if end - start >= min_duration:
            silences.append(Silence(start, end))
    return silences


def cut_points(silences: list[Silence]) -> list[float]:
    """Return the middle of each silence: the proposed boundaries between tracks."""
    return [silence.middle for silence in silences]
