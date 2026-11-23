"""Pure rules for cutting a compilation: output file names and audio length checks."""

from ytparser.core.models import Tracklist

# YouTube timestamps and video durations are rounded to the second, so a tracklist
# may legitimately end slightly after the downloaded audio.
DURATION_TOLERANCE = 1.0


def track_filenames(tracklist: Tracklist, suffix: str) -> tuple[str, ...]:
    """Name each output after its track number, zero-padded so files sort in track order."""
    if len(suffix) < 2 or not suffix.startswith("."):
        raise ValueError(f"The audio file needs an extension such as '.mp3', got {suffix!r}.")
    width = max(2, len(str(len(tracklist.tracks))))
    return tuple(f"{track.number:0{width}d}{suffix}" for track in tracklist.tracks)


def check_tracklist_fits(tracklist: Tracklist, audio_duration: float) -> None:
    """Reject a tracklist that cannot describe an audio file of this duration."""
    # Tracks are ordered and do not overlap: the last one has the latest start and end.
    last = tracklist.tracks[-1]
    if last.start >= audio_duration or last.end > audio_duration + DURATION_TOLERANCE:
        raise ValueError(
            f"Track {last.number} ({last.start:.3f} s to {last.end:.3f} s) does not fit "
            f"in the audio file, which lasts {audio_duration:.3f} s."
        )
