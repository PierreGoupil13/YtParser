"""Where does the decoded sound of a cut start and end? (T-1.3)

The decoded source is the timing reference: it carries the same encoding effects
(delay compensation, pre-echo) as the cuts, so each decoded cut is located inside
it to the sample.
"""

import subprocess
import sys
from array import array
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from ytparser.adapters.ffmpegadapter import (
    cut_track_with_reencoding,
    cut_track_without_reencoding,
)
from ytparser.core.models import Track

SAMPLE_RATE = 44_100
FRAME = 1152  # samples per channel in one MPEG-1 Layer III frame
MP3_DECODER_DELAY = 529  # samples (528 + 1) that an MP3 decoder adds before the signal
# 40 ms bursts of a 1 kHz sine every 0.5 s from 0.25 s, on digital silence.
MARKERS = (
    "aevalsrc=exprs='0.5*sin(2*PI*1000*t)*lt(mod(t+0.25,0.5),0.04)'"
    f":sample_rate={SAMPLE_RATE}:duration=6"
)
# Boundaries off the frame grid; 1.234 s is 16 ms before a burst, 2.7612 s and 5.27 s inside one.
CUTS = ((0.9871, 2.2222), (1.234, 3.456), (2.7612, 4.8765), (4.4, 5.27))

# Stream copy keeps whole frames, then the decoder skips the delays announced by the
# copy's header: one frame plus the 529-sample decoder delay (38 ms) bounds both.
COPY_TOLERANCE = FRAME + MP3_DECODER_DELAY
# Re-encoding selects samples: only the rounding of the requested instants remains.
REENCODE_TOLERANCE = 2
# The bit reservoir points back at most 511 bytes (under two 128 kbit/s frames):
# a decoder starting at the cut can only miss sound within the first frames.
FIRST_FRAMES = 4 * FRAME
BLOCK = 64


@dataclass(frozen=True)
class Boundaries:
    track: Track
    start_error: float  # samples; positive when the output starts after the request
    end_error: float  # samples; positive when the output ends after the request
    missing: int  # samples where the source sounds but the output is almost silent
    missing_until: int  # end of the last such block, in output samples
    exact_from: int  # output index from which every sample equals the source


@pytest.fixture(scope="module")
def marked_source(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, array]:
    source = tmp_path_factory.mktemp("precision") / "source.mp3"
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
            MARKERS,
            "-ac",
            "2",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            str(source),
        ],
        check=True,
    )
    return source, _decode(source)


def test_stream_copy_boundaries_are_frame_accurate(
    marked_source: tuple[Path, array], tmp_path: Path
) -> None:
    results = _measure(cut_track_without_reencoding, *marked_source, tmp_path)
    _report("Copie de flux", results, exact=True)

    for result in results:
        assert abs(result.start_error) <= COPY_TOLERANCE
        assert abs(result.end_error) <= COPY_TOLERANCE
        # Past its first frames, a copy decodes exactly like the source, up to its last sample.
        assert result.exact_from <= FIRST_FRAMES
        assert result.missing_until <= FIRST_FRAMES


def test_reencoded_boundaries_are_sample_accurate(
    marked_source: tuple[Path, array], tmp_path: Path
) -> None:
    results = _measure(cut_track_with_reencoding, *marked_source, tmp_path)
    _report("Réencodage MP3", results, exact=False)

    for result in results:
        assert abs(result.start_error) <= REENCODE_TOLERANCE
        assert abs(result.end_error) <= REENCODE_TOLERANCE
        # FFmpeg also starts decoding at the cut: the first frames may lack sound.
        assert result.missing_until <= FIRST_FRAMES


def _measure(
    cut: Callable[[Path, Path, Track], None], source: Path, reference: array, tmp_path: Path
) -> list[Boundaries]:
    threshold = max(map(abs, reference)) // 2
    results = []
    for number, (start, end) in enumerate(CUTS, start=1):
        track = Track(number, start, end, f"Coupe {number}", "Repères")
        destination = tmp_path / f"coupe {number}.mp3"
        cut(source, destination, track)
        output = _decode(destination)
        offset = _locate(output, reference, start * SAMPLE_RATE, threshold)
        expected = reference[offset : offset + len(output)]
        assert len(expected) == len(output)
        results.append(
            Boundaries(
                track,
                offset - start * SAMPLE_RATE,
                offset + len(output) - end * SAMPLE_RATE,
                *_missing_sound(output, expected, threshold),
                _exact_from(output, expected),
            )
        )
    return results


def _decode(path: Path) -> array:
    # Mono 16-bit PCM on stdout; s16le is little-endian whatever the machine
    raw = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-f",
            "s16le",
            "-ac",
            "1",
            "-",
        ],
        check=True,
        capture_output=True,
    ).stdout
    samples = array("h", raw)
    if sys.byteorder == "big":
        samples.byteswap()
    return samples


def _locate(output: array, reference: array, start: float, threshold: int) -> int:
    """Index in the decoded source of the output's first sample."""
    # A burst well inside the output gives a coarse offset, refined to the sample
    marker = _next_onset(output, threshold, FIRST_FRAMES)
    coarse = _next_onset(reference, threshold, round(start) + marker - SAMPLE_RATE // 4) - marker
    window = range(marker - 256, marker + 1024)
    return min(
        range(coarse - 8, coarse + 9),
        key=lambda offset: sum((output[i] - reference[offset + i]) ** 2 for i in window),
    )


def _next_onset(samples: array, threshold: int, begin: int) -> int:
    """First loud sample after at least 1000 quiet ones (23 ms)."""
    quiet = 0
    for index in range(begin, len(samples)):
        if abs(samples[index]) < threshold:
            quiet += 1
        elif quiet >= 1000:
            return index
        else:
            quiet = 0
    pytest.fail("Aucun repère trouvé dans le signal décodé")


def _missing_sound(output: array, expected: array, threshold: int) -> tuple[int, int]:
    missing = until = 0
    for begin in range(0, len(output) - BLOCK + 1, BLOCK):
        expected_peak = max(map(abs, expected[begin : begin + BLOCK]))
        output_peak = max(map(abs, output[begin : begin + BLOCK]))
        if expected_peak >= threshold and output_peak < expected_peak / 4:
            missing += BLOCK
            until = begin + BLOCK
    return missing, until


def _exact_from(output: array, expected: array) -> int:
    index = len(output)
    while index > 0 and output[index - 1] == expected[index - 1]:
        index -= 1
    return index


def _report(title: str, results: list[Boundaries], exact: bool) -> None:
    print(f"\n{title} : écarts par rapport à la source décodée (1 ms = 44,1 échantillons)")
    for result in results:
        line = (
            f"  {result.track.start:.4f} s - {result.track.end:.4f} s : "
            f"début {result.start_error:+7.1f} éch. ({_ms(result.start_error):+7.3f} ms), "
            f"fin {result.end_error:+7.1f} éch. ({_ms(result.end_error):+7.3f} ms), "
            f"durée {_ms(result.end_error - result.start_error):+7.3f} ms, "
            f"son manquant {_ms(result.missing):4.1f} ms"
        )
        if result.missing:
            line += f" (dans les {_ms(result.missing_until):.1f} premières ms)"
        if exact:
            line += f", identique à la source dès {_ms(result.exact_from):.1f} ms"
        print(line)


def _ms(samples: float) -> float:
    return samples / SAMPLE_RATE * 1000
