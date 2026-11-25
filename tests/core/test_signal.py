import numpy as np
import pytest

from ytparser.core.signal import AudioSignal, pcm16_to_signal


def test_pcm16_is_normalised_to_unit_range() -> None:
    pcm = np.array([0, 16384, -16384, -32768, 32767], dtype="<i2").tobytes()

    signal = pcm16_to_signal(pcm, 8_000)

    assert signal.samples.tolist() == pytest.approx([0.0, 0.5, -0.5, -1.0, 0.99997], abs=1e-4)


def test_duration_is_samples_over_sample_rate() -> None:
    signal = AudioSignal(np.zeros(24_000, dtype=np.float32), 16_000)

    assert signal.duration == 1.5


def test_odd_byte_count_is_rejected() -> None:
    with pytest.raises(ValueError, match="even"):
        pcm16_to_signal(b"\x00\x01\x02", 8_000)


def test_non_mono_array_is_rejected() -> None:
    with pytest.raises(ValueError, match="mono"):
        AudioSignal(np.zeros((2, 10), dtype=np.float32), 8_000)
