"""Pure description of an output profile: what varies from one audio format to another."""

import re
from dataclasses import dataclass

from ytparser.core.download import OutputFormat, SourcePlan, source_plan

DEFAULT_MP3_BITRATE = "192k"
_BITRATE = re.compile(r"[1-9]\d{1,2}k")

# Décoder une seconde avant le début de la piste : sans cela, le réencodage d'une source MP3
# perd jusqu'à 67 ms au début (réservoir de bits, mesure T-1.3)
REENCODE_PREROLL = 1.0


@dataclass(frozen=True)
class OutputProfile:
    """How to produce one output format; tagging is chosen by `format` in the tag adapter."""

    format: OutputFormat
    extension: str  # with the dot, e.g. ".m4a"
    source: SourcePlan  # which stream to download, and which codec a stream copy requires
    codec_args: tuple[str, ...]  # ffmpeg audio arguments: stream copy or re-encoding
    preroll: float = 0.0  # seconds decoded before the cut start, then discarded


STREAM_COPY_ARGS = ("-c:a", "copy")

M4A_PROFILE = OutputProfile(
    format=OutputFormat.M4A,
    extension=".m4a",
    source=source_plan(OutputFormat.M4A),
    # Copie du flux AAC : pas de réencodage
    codec_args=STREAM_COPY_ARGS,
)

# Remuxage : le flux Opus de YouTube (WebM) est recopié tel quel dans un conteneur Ogg
OPUS_PROFILE = OutputProfile(
    format=OutputFormat.OPUS,
    extension=".opus",
    source=source_plan(OutputFormat.OPUS),
    codec_args=STREAM_COPY_ARGS,
)

DEFAULT_PROFILE = M4A_PROFILE


def is_valid_bitrate(value: str) -> bool:
    return _BITRATE.fullmatch(value) is not None


def mp3_profile(bitrate: str = DEFAULT_MP3_BITRATE) -> OutputProfile:
    if not is_valid_bitrate(bitrate):
        raise ValueError(f"Invalid MP3 bitrate {bitrate!r}; expected a value such as '192k'.")
    return OutputProfile(
        format=OutputFormat.MP3,
        extension=".mp3",
        source=source_plan(OutputFormat.MP3),
        codec_args=("-c:a", "libmp3lame", "-b:a", bitrate),
        preroll=REENCODE_PREROLL,
    )


def get_profile(target: OutputFormat, mp3_bitrate: str = DEFAULT_MP3_BITRATE) -> OutputProfile:
    if target is OutputFormat.MP3:
        return mp3_profile(mp3_bitrate)
    if target is OutputFormat.OPUS:
        return OPUS_PROFILE
    return M4A_PROFILE
