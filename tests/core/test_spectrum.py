import numpy as np
import pytest

from ytparser.core.signal import AudioSignal
from ytparser.core.spectrum import FLOOR_DB, stft

RATE = 8_000


def _tone(frequency: float, seconds: float) -> AudioSignal:
    t = np.arange(round(seconds * RATE)) / RATE
    return AudioSignal(np.sin(2 * np.pi * frequency * t).astype(np.float32), RATE)


def test_a_pure_tone_peaks_at_its_frequency() -> None:
    spectrogram = stft(_tone(1_000, 1.0), n_fft=1024, hop=256)

    peak_bins = spectrogram.magnitude.argmax(axis=1)

    # Résolution = 8000 / 1024 = 7,8 Hz par case
    assert spectrogram.frequencies[peak_bins] == pytest.approx(1_000, abs=8)


def test_frequency_axis_goes_up_to_nyquist() -> None:
    spectrogram = stft(_tone(440, 0.5), n_fft=512, hop=128)

    assert spectrogram.frequencies[0] == 0
    assert spectrogram.frequencies[-1] == RATE / 2
    assert spectrogram.magnitude.shape[1] == 257


def test_frames_are_timed_at_their_centre() -> None:
    spectrogram = stft(_tone(440, 1.0), n_fft=1024, hop=512)

    assert spectrogram.times[0] == pytest.approx(512 / RATE)
    assert spectrogram.times[1] - spectrogram.times[0] == pytest.approx(512 / RATE)
    assert len(spectrogram.times) == (RATE - 1024) // 512 + 1


def test_change_of_note_moves_the_peak_in_time() -> None:
    signal = AudioSignal(np.concatenate([_tone(500, 1.0).samples, _tone(2_000, 1.0).samples]), RATE)
    spectrogram = stft(signal, n_fft=1024, hop=256)

    peaks = spectrogram.frequencies[spectrogram.magnitude.argmax(axis=1)]

    assert peaks[0] == pytest.approx(500, abs=8)
    assert peaks[-1] == pytest.approx(2_000, abs=8)


def test_db_is_relative_to_the_peak_and_floored() -> None:
    silent = stft(AudioSignal(np.zeros(4_096, dtype=np.float32), RATE))
    tone = stft(_tone(1_000, 0.5))

    assert (silent.db == FLOOR_DB).all()
    assert tone.db.max() == pytest.approx(0.0)
    assert tone.db.min() >= FLOOR_DB


def test_invalid_parameters_are_rejected() -> None:
    with pytest.raises(ValueError, match="shorter"):
        stft(_tone(440, 0.01), n_fft=1024)
    with pytest.raises(ValueError, match="at least"):
        stft(_tone(440, 1.0), n_fft=1, hop=1)
