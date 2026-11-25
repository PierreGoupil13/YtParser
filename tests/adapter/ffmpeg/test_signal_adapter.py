import subprocess
from pathlib import Path

import pytest

from ytparser.adapters.ffmpegadapter import probe_duration
from ytparser.adapters.signaladapter import load_signal


def _make_stereo_mp3(path: Path, duration: int, source_rate: int) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-n",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:sample_rate={source_rate}:duration={duration}",
            "-ac",
            "2",
            "-c:a",
            "libmp3lame",
            str(path),
        ],
        check=True,
    )


@pytest.mark.parametrize("sample_rate", [8_000, 16_000])
def test_load_signal_is_mono_with_consistent_duration(tmp_path: Path, sample_rate: int) -> None:
    source = tmp_path / "tone.mp3"
    _make_stereo_mp3(source, duration=3, source_rate=44_100)

    signal = load_signal(source, sample_rate)

    assert signal.sample_rate == sample_rate
    assert signal.samples.ndim == 1
    # Le nombre d'échantillons colle à la durée annoncée par ffprobe (marge : trames MP3)
    assert len(signal.samples) == pytest.approx(
        probe_duration(source) * sample_rate, abs=0.05 * sample_rate
    )
    assert signal.duration == pytest.approx(3, abs=0.1)
    # Un sinus d'amplitude 1/8 environ : valeurs bien comprises dans [-1, 1], pas nulles
    assert 0.05 < abs(signal.samples).max() <= 1.0
