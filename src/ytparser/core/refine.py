"""Move approximate track boundaries onto the nearest real transition in the audio."""

from dataclasses import dataclass, replace

import numpy as np

from ytparser.core.loudness import LoudnessCurve
from ytparser.core.models import Track, Tracklist

# Distance maximale entre un timestamp et la transition cherchée (les timestamps YouTube
# observés sur UC1 peuvent avoir 9 s d'avance)
DEFAULT_RADIUS = 12.0
# Un creux d'énergie doit descendre au moins de tant de dB sous le niveau médian de la zone
MIN_DEPTH_DB = 12.0
# Un son plus fort que le creux de tant de dB n'est plus dans le creux
_GAP_MARGIN_DB = 6.0
_SMOOTH_SECONDS = 0.5
# Écart minimal entre deux débuts de piste après recalage
_MIN_TRACK_SECONDS = 1.0


@dataclass(frozen=True)
class Refinement:
    """What happened to one boundary: method is "silence", "spectral" or "unchanged"."""

    track: int
    original: float
    refined: float
    method: str

    @property
    def shift(self) -> float:
        return self.refined - self.original


def _smoothed(curve: LoudnessCurve) -> np.ndarray:
    size = max(1, round(_SMOOTH_SECONDS / curve.window_seconds))
    # Bords répétés : sans cela la moyenne s'effondre artificiellement aux extrémités du fichier
    padded = np.pad(curve.dbfs, size, mode="edge")
    return np.convolve(padded, np.ones(size) / size, mode="same")[size:-size]


def refine_boundary(
    curve: LoudnessCurve,
    candidates: list[float],
    moment: float,
    radius: float = DEFAULT_RADIUS,
    position: float = 1.0,
    smoothed: np.ndarray | None = None,
) -> tuple[float, str]:
    """Return the refined time of a boundary and the method that found it.

    1. Inside moment +/- radius, look for the deepest dip in loudness. If it is deep enough,
       the track change happens in that gap: it starts where the sound drops (end of the
       previous track) and ends where the sound comes back (arrival of the next one). The cut
       is placed at gap_start + position * (gap_end - gap_start): position 1 is the arrival of
       the next track (never clips the previous one), 0 is the start of the gap, 0.5 the middle.
    2. Without such a dip, take the spectral change candidate nearest to moment, if any.
    3. Otherwise keep moment.
    """
    if not 0.0 <= position <= 1.0:
        raise ValueError("position must be between 0 and 1.")
    levels = _smoothed(curve) if smoothed is None else smoothed
    first = max(0, int((moment - radius) / curve.window_seconds))
    last = min(len(levels), int((moment + radius) / curve.window_seconds) + 1)
    zone = levels[first:last]
    if len(zone) >= 3:
        valley = int(zone.argmin())
        if float(np.median(zone)) - float(zone[valley]) >= MIN_DEPTH_DB:
            ceiling = float(zone[valley]) + _GAP_MARGIN_DB
            start = end = valley
            while start > 0 and zone[start - 1] <= ceiling:
                start -= 1
            while end < len(zone) - 1 and zone[end + 1] <= ceiling:
                end += 1
            # Un creux qui touche la fin de la zone n'a pas de remontée : le son revient plus loin
            if end < len(zone) - 1:
                gap_start = float(curve.times[first + start])
                arrival = float(curve.times[first + end + 1])
                return gap_start + position * (arrival - gap_start), "silence"
    nearby = [c for c in candidates if abs(c - moment) <= radius]
    if nearby:
        return min(nearby, key=lambda c: abs(c - moment)), "spectral"
    return moment, "unchanged"


def refine_tracklist(
    tracklist: Tracklist,
    curve: LoudnessCurve,
    candidates: list[float],
    radius: float = DEFAULT_RADIUS,
    position: float = 1.0,
) -> tuple[Tracklist, list[Refinement]]:
    """Refine every boundary between two tracks; the first start and the last end stay put.

    A refined boundary that would leave a track shorter than one second (or reorder tracks)
    is ignored and the original time is kept. Gaps left by hand in the tracklist are kept.
    """
    tracks = tracklist.tracks
    smoothed = _smoothed(curve)
    starts = [track.start for track in tracks]
    refinements = []
    for index in range(1, len(tracks)):
        original = tracks[index].start
        refined, method = refine_boundary(curve, candidates, original, radius, position, smoothed)
        too_early = refined < starts[index - 1] + _MIN_TRACK_SECONDS
        too_late = refined > tracks[-1].end - _MIN_TRACK_SECONDS
        if too_early or too_late:
            refined, method = original, "unchanged"
        starts[index] = refined
        refinements.append(Refinement(tracks[index].number, original, refined, method))

    new_tracks: list[Track] = []
    for index, track in enumerate(tracks):
        contiguous = index + 1 < len(tracks) and track.end == tracks[index + 1].start
        end = starts[index + 1] if contiguous else track.end
        new_tracks.append(replace(track, start=starts[index], end=end))
    return Tracklist(tuple(new_tracks)), refinements
