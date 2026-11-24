"""Pure rules for audio downloads: target format -> source stream, error messages."""

from dataclasses import dataclass
from enum import StrEnum


class OutputFormat(StrEnum):
    M4A = "m4a"
    MP3 = "mp3"
    OPUS = "opus"


@dataclass(frozen=True)
class SourcePlan:
    """Preferred stream for a target format, with yt-dlp fallbacks."""

    selector: str  # yt-dlp format expression: alternatives separated by "/", best first
    preferred_codec: str | None  # ffprobe codec_name of the ideal stream; None = any stream

    def is_preferred(self, codec: str) -> bool:
        return self.preferred_codec is None or codec == self.preferred_codec


# Sur YouTube, l'audio est un flux séparé de la vidéo : AAC (m4a) ou Opus (webm)
SOURCE_PLANS: dict[OutputFormat, SourcePlan] = {
    OutputFormat.M4A: SourcePlan("bestaudio[acodec^=mp4a]/bestaudio[ext=m4a]/bestaudio", "aac"),
    OutputFormat.OPUS: SourcePlan("bestaudio[acodec=opus]/bestaudio", "opus"),
    # Le MP3 est réencodé plus tard : la meilleure source disponible suffit
    OutputFormat.MP3: SourcePlan("bestaudio", None),
}

UPDATE_HINT = "Update yt-dlp (uv lock --upgrade-package yt-dlp, then uv sync) and try again."

_UNAVAILABLE_MARKERS = (
    "video unavailable",
    "private video",
    "has been removed",
    "video is unavailable",
    "this video is not available",
)


def source_plan(target: OutputFormat) -> SourcePlan:
    return SOURCE_PLANS[target]


def explain_download_error(message: str) -> str:
    """Turn a raw yt-dlp error into an actionable message."""
    cleaned = message.removeprefix("ERROR: ").strip()
    lowered = cleaned.lower()
    if any(marker in lowered for marker in _UNAVAILABLE_MARKERS):
        return f"The video is unavailable (private, removed or restricted): {cleaned}"
    return f"yt-dlp failed: {cleaned}\n{UPDATE_HINT}"
