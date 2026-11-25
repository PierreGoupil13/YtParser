"""Decode an audio file into an in-memory mono signal with FFmpeg."""

import io
import shutil
import subprocess
import wave
from pathlib import Path

from ytparser.adapters.ffmpegadapter import ToolNotFoundError, _arg
from ytparser.core.signal import AudioSignal, pcm16_to_signal

# 16 kHz suffit pour mesurer une énergie (Nyquist : fréquences jusqu'à 8 kHz) et reste léger
DEFAULT_SAMPLE_RATE = 16_000


def load_signal(source: Path, sample_rate: int = DEFAULT_SAMPLE_RATE) -> AudioSignal:
    """Decode source to mono 16-bit PCM at sample_rate and load it as an AudioSignal."""
    if shutil.which("ffmpeg") is None:
        raise ToolNotFoundError("ffmpeg not found. Install FFmpeg and add it to the PATH.")
    result = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-i",
            _arg(source),
            # Premier flux audio, mélangé en mono, rééchantillonné, sans image ni métadonnées
            "-map",
            "0:a:0",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-c:a",
            "pcm_s16le",
            # WAV sur la sortie standard : pas de fichier temporaire sur le disque
            "-f",
            "wav",
            "pipe:1",
        ],
        check=True,
        capture_output=True,
    )
    with wave.open(io.BytesIO(result.stdout)) as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise ValueError("FFmpeg did not produce mono 16-bit PCM.")
        return pcm16_to_signal(wav.readframes(wav.getnframes()), wav.getframerate())
