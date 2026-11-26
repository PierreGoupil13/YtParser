"""Short-time Fourier transform: how the frequency content of a signal evolves over time."""

from dataclasses import dataclass

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from ytparser.core.signal import AudioSignal

# Même plancher que pour l'énergie : évite le logarithme de zéro
FLOOR_DB = -120.0
_BATCH_FRAMES = 4096


@dataclass(frozen=True)
class Spectrogram:
    """Magnitudes (linear, shape frames x bins), with the time of each frame and bin frequency."""

    magnitude: np.ndarray
    times: np.ndarray
    frequencies: np.ndarray

    @property
    def db(self) -> np.ndarray:
        """Magnitudes in dB relative to the largest value of the spectrogram."""
        peak = self.magnitude.max()
        if peak <= 0:
            return np.full(self.magnitude.shape, FLOOR_DB)
        with np.errstate(divide="ignore"):
            levels = 20.0 * np.log10(self.magnitude / peak)
        return np.maximum(levels, FLOOR_DB)


def stft(signal: AudioSignal, n_fft: int = 1024, hop: int = 256) -> Spectrogram:
    """Compute the magnitude spectrogram with a Hann window.

    Each frame holds n_fft samples and starts hop samples after the previous one. A frame
    is stamped with the time of its centre. A signal shorter than n_fft gives no frame.
    """
    if n_fft < 2 or hop < 1:
        raise ValueError("n_fft must be at least 2 and hop at least 1.")
    if len(signal.samples) < n_fft:
        raise ValueError("The signal is shorter than one analysis window.")
    # Vue sans copie : une ligne par trame, décalée de `hop` échantillons
    frames = sliding_window_view(signal.samples, n_fft)[::hop]
    # La fenêtre de Hann adoucit les bords de la trame, sinon la coupure brutale
    # crée de fausses fréquences (fuite spectrale)
    window = np.hanning(n_fft).astype(np.float32)
    # Par lots : sinon un long fichier alloue d'un coup toutes les trames fenêtrées
    batches = [
        np.abs(np.fft.rfft(frames[first : first + _BATCH_FRAMES] * window, axis=1))
        for first in range(0, len(frames), _BATCH_FRAMES)
    ]
    magnitude = np.concatenate(batches).astype(np.float32)
    times = (np.arange(len(frames)) * hop + n_fft / 2) / signal.sample_rate
    frequencies = np.fft.rfftfreq(n_fft, d=1 / signal.sample_rate)
    return Spectrogram(magnitude, times, frequencies)
