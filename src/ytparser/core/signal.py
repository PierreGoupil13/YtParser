"""Mono audio signal held in memory, as a numeric array."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AudioSignal:
    """Mono PCM samples normalised to [-1.0, 1.0], with their sampling rate in Hz."""

    samples: np.ndarray
    sample_rate: int

    def __post_init__(self) -> None:
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive.")
        if self.samples.ndim != 1:
            raise ValueError("samples must be a one-dimensional (mono) array.")

    @property
    def duration(self) -> float:
        """Duration in seconds: number of samples divided by the sampling rate."""
        return len(self.samples) / self.sample_rate


def pcm16_to_signal(pcm: bytes, sample_rate: int) -> AudioSignal:
    """Turn raw little-endian signed 16-bit mono PCM bytes into a normalised signal."""
    if len(pcm) % 2:
        raise ValueError("16-bit PCM data must contain an even number of bytes.")
    integers = np.frombuffer(pcm, dtype="<i2")
    # 32768 = 2**15 : la plus grande amplitude d'un entier signé sur 16 bits
    return AudioSignal(integers.astype(np.float32) / 32768.0, sample_rate)
