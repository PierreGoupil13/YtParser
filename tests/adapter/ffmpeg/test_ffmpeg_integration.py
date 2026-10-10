import json
import subprocess
from pathlib import Path

import pytest

from ytparser.adapters.ffmpegadapter import cut_track
from ytparser.core.models import Track


def test_cut_track_produces_readable_mp3_with_expected_duration(tmp_path: Path) -> None:
    source = tmp_path / "source audio.mp3"
    destination = tmp_path / "piste extraite.mp3"
    sample_rate = 48_000
    track = Track(1, 1.234, 3.734, "Extrait", "Artiste")

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
            f"sine=frequency=440:sample_rate={sample_rate}:duration=5",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(source),
        ],
        check=True,
    )

    cut_track(source, destination, track)

    assert destination.is_file()
    assert destination.stat().st_size > 0

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(destination),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    metadata = json.loads(probe.stdout)
    streams = metadata["streams"]
    assert len(streams) == 1
    assert streams[0]["codec_type"] == "audio"
    assert streams[0]["codec_name"] == "mp3"
    assert int(streams[0]["sample_rate"]) == sample_rate

    # Three MPEG-1 Layer III frames allow for packet rounding and MP3 padding.
    duration_tolerance = 3 * 1152 / sample_rate
    assert float(metadata["format"]["duration"]) == pytest.approx(
        track.end - track.start, abs=duration_tolerance
    )

    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-xerror",
            "-i",
            str(destination),
            "-map",
            "0:a:0",
            "-f",
            "null",
            "-",
        ],
        check=True,
    )
