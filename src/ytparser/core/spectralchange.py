"""Spectral change over time: where the frequency content of a signal shifts."""

from dataclasses import dataclass

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from ytparser.core.spectrum import Spectrogram

# Au-dessus de ce rapport au pic, les composantes sont du bruit de fond sans intérêt
_FLOOR_DB = -80.0
_BANDS = 64


@dataclass(frozen=True)
class ChangeCurve:
    """A spectral change value for each time in times (seconds)."""

    times: np.ndarray
    values: np.ndarray


def _band_levels(spectrogram: Spectrogram) -> np.ndarray:
    """Return the level (dB) of 64 equal frequency bands for each frame (frames x 64)."""
    levels = np.maximum(spectrogram.db, _FLOOR_DB)
    usable = (levels.shape[1] - 1) // _BANDS * _BANDS
    # On regroupe les cases voisines : moins de dimensions, moins de bruit
    return levels[:, 1 : usable + 1].reshape(len(levels), _BANDS, -1).mean(axis=2)


def spectral_flux(spectrogram: Spectrogram) -> ChangeCurve:
    """Measure how much the spectrum differs from the previous frame (classic spectral flux).

    The value is the mean absolute difference, in dB, between the band levels of two
    consecutive frames. It peaks at every note attack, not only at track changes.
    """
    levels = _band_levels(spectrogram)
    flux = np.abs(np.diff(levels, axis=0)).mean(axis=1)
    return ChangeCurve(spectrogram.times[1:], flux)


def spectral_change(spectrogram: Spectrogram, window_seconds: float = 3.0) -> ChangeCurve:
    """Compare the average spectrum just before and just after each instant.

    The value is the mean absolute difference, in dB, between the band levels averaged over
    window_seconds before the instant and over window_seconds after it. Averaging smooths
    out individual notes: within one track the two sides look alike, across a track change
    they differ. Instants closer than window_seconds to an edge are not evaluated.
    """
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive.")
    levels = _band_levels(spectrogram)
    step = float(spectrogram.times[1] - spectrogram.times[0]) if len(levels) > 1 else 0.0
    span = round(window_seconds / step) if step > 0 else 0
    if span < 1 or len(levels) < 2 * span + 1:
        raise ValueError("The signal is too short for this window.")
    # Sommes cumulées : la moyenne de n'importe quelle plage en deux soustractions
    cumulative = np.concatenate(
        [
            np.zeros((1, levels.shape[1]), dtype=np.float64),
            np.cumsum(levels, axis=0, dtype=np.float64),
        ]
    )
    centres = np.arange(span, len(levels) - span + 1)
    before = (cumulative[centres] - cumulative[centres - span]) / span
    after = (cumulative[centres + span] - cumulative[centres]) / span
    change = np.abs(after - before).mean(axis=1)
    # Le centre `c` sépare la trame c-1 de la trame c : on le date entre les deux
    moments = (spectrogram.times[centres - 1] + spectrogram.times[centres]) / 2
    return ChangeCurve(moments, change)


def find_candidates(
    curve: ChangeCurve, min_separation: float = 8.0, sensitivity: float = 4.0
) -> list[float]:
    """Return the times of the clear peaks of a change curve, in seconds.

    A peak is the maximum of the curve within min_separation seconds on each side and must
    exceed median + sensitivity * MAD (median absolute deviation), a threshold that adapts
    to each file. Raise sensitivity to keep fewer, clearer candidates.
    """
    values = curve.values
    if len(values) < 3:
        return []
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    threshold = median + sensitivity * mad
    step = float(curve.times[1] - curve.times[0])
    half = max(1, round(min_separation / step))
    padded = np.pad(values, half, constant_values=-np.inf)
    # Maximum glissant : un point est un pic s'il égale le maximum de son voisinage
    neighbourhood_max = sliding_window_view(padded, 2 * half + 1).max(axis=1)
    peaks = np.flatnonzero((values == neighbourhood_max) & (values > threshold))
    return [float(curve.times[index]) for index in peaks]
