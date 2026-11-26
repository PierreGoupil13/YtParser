import numpy as np
import pytest

from ytparser.core.loudness import rms_dbfs
from ytparser.core.signal import AudioSignal
from ytparser.core.spectralchange import (
    ChangeCurve,
    find_candidates,
    spectral_change,
    spectral_flux,
)
from ytparser.core.spectrum import stft

RATE = 8_000


def _tone(frequency: float, seconds: float, amplitude: float = 0.5) -> np.ndarray:
    t = np.arange(round(seconds * RATE)) / RATE
    return (amplitude * np.sin(2 * np.pi * frequency * t)).astype(np.float32)


def _two_notes(first: float = 500, second: float = 2_000) -> AudioSignal:
    # Même amplitude des deux côtés : l'énergie ne bouge pas, seul le contenu change
    return AudioSignal(np.concatenate([_tone(first, 20), _tone(second, 20)]), RATE)


def test_change_peaks_at_a_transition_that_loudness_does_not_see() -> None:
    signal = _two_notes()

    levels = rms_dbfs(signal).dbfs
    assert levels.max() - levels.min() < 0.5

    curve = spectral_change(stft(signal, hop=512), window_seconds=3.0)
    assert curve.times[curve.values.argmax()] == pytest.approx(20.0, abs=0.2)
    assert find_candidates(curve) == pytest.approx([20.0], abs=0.2)


def test_a_steady_signal_has_no_candidate() -> None:
    signal = AudioSignal(_tone(500, 40), RATE)

    curve = spectral_change(stft(signal, hop=512), window_seconds=3.0)

    assert curve.values.max() < 1.0
    assert find_candidates(curve) == []


def test_spectral_flux_spikes_on_the_frame_where_the_note_changes() -> None:
    spectrogram = stft(_two_notes(), hop=512)

    flux = spectral_flux(spectrogram)

    # Dans une note tenue le spectre est stable, au changement il bondit
    assert flux.times[flux.values.argmax()] == pytest.approx(20.0, abs=0.2)
    assert flux.values.max() > 10 * np.median(flux.values)


def test_a_crossfade_is_bracketed_by_candidates_at_its_two_edges() -> None:
    fade = np.linspace(0, 1, 10 * RATE, dtype=np.float32)
    mixed = _tone(500, 10) * (1 - fade) + _tone(2_000, 10) * fade
    signal = AudioSignal(np.concatenate([_tone(500, 15), mixed, _tone(2_000, 15)]), RATE)

    curve = spectral_change(stft(signal, hop=512), window_seconds=3.0)
    candidates = find_candidates(curve)

    # En dB, une note encore très faible compte déjà beaucoup : le changement est maximal
    # quand la nouvelle note apparaît (15 s) et quand l'ancienne disparaît (25 s),
    # pas au milieu du fondu. Le milieu (20 s) se situe entre les deux candidats.
    assert candidates == pytest.approx([15.0, 25.0], abs=1.0)
    assert sum(candidates) / 2 == pytest.approx(20.0, abs=1.0)


def test_candidates_closer_than_min_separation_keep_only_the_strongest() -> None:
    times = np.arange(0, 60, 0.5)
    values = np.zeros_like(times)
    values[20], values[24], values[50] = 5.0, 8.0, 6.0  # 10 s, 12 s, 25 s
    curve = ChangeCurve(times, values)

    assert find_candidates(curve, min_separation=5.0, sensitivity=1.0) == [12.0, 25.0]


def test_invalid_inputs_are_rejected() -> None:
    spectrogram = stft(AudioSignal(_tone(500, 2), RATE), hop=512)

    with pytest.raises(ValueError, match="positive"):
        spectral_change(spectrogram, window_seconds=0)
    with pytest.raises(ValueError, match="too short"):
        spectral_change(spectrogram, window_seconds=3.0)
