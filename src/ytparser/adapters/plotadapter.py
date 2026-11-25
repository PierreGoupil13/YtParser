"""Plot a waveform and its loudness curve to an image (exploration tool).

Usage:
    uv run python -m ytparser.adapters.plotadapter SOURCE OUTPUT.png
        [WINDOW_SECONDS [TRACKLIST.yaml]]
"""

import sys
from pathlib import Path

import matplotlib

# Backend sans fenêtre : on écrit un fichier image, aucune interface graphique requise
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from ytparser.adapters.signaladapter import load_signal  # noqa: E402
from ytparser.adapters.yamladapter import load_tracklist  # noqa: E402
from ytparser.core.loudness import LoudnessCurve, rms_dbfs  # noqa: E402
from ytparser.core.signal import AudioSignal  # noqa: E402

# Nombre maximal de paquets affichés pour la forme d'onde, pour garder le tracé lisible
_MAX_WAVEFORM_POINTS = 20_000


def plot_loudness(
    signal: AudioSignal,
    curve: LoudnessCurve,
    destination: Path,
    boundaries: list[float] | None = None,
) -> None:
    """Write a PNG with the waveform (top) and the RMS curve in dBFS (bottom).

    boundaries (seconds) are drawn as vertical lines on both plots.
    """
    figure, (top, bottom) = plt.subplots(2, 1, sharex=True, figsize=(16, 7))
    # Forme d'onde : on garde le pic de chaque paquet pour ne pas effacer les transitoires
    bins = min(_MAX_WAVEFORM_POINTS, len(signal.samples))
    size = len(signal.samples) // bins
    peaks = np.abs(signal.samples[: bins * size].reshape(bins, size)).max(axis=1)
    peak_times = (np.arange(bins) + 0.5) * size / signal.sample_rate
    top.fill_between(peak_times, -peaks, peaks, linewidth=0, color="tab:blue")
    top.set_ylabel("Amplitude")
    top.set_ylim(-1, 1)
    bottom.plot(curve.times, curve.dbfs, linewidth=0.6, color="tab:red")
    bottom.set_ylabel("RMS (dBFS)")
    bottom.set_xlabel("Temps (s)")
    bottom.set_ylim(-90, 0)
    bottom.grid(alpha=0.3)
    for axis in (top, bottom):
        for moment in boundaries or []:
            axis.axvline(moment, color="green", linewidth=0.7, alpha=0.7)
    figure.tight_layout()
    figure.savefig(destination, dpi=110)
    plt.close(figure)


def main(argv: list[str]) -> None:
    if len(argv) not in (2, 3, 4):
        raise SystemExit(__doc__)
    window = float(argv[2]) if len(argv) == 3 else 0.05
    signal = load_signal(Path(argv[0]))
    boundaries = None
    if len(argv) == 4:
        # Début de chaque piste, sauf le 0 initial : ce sont les frontières à retrouver
        boundaries = [track.start for track in load_tracklist(Path(argv[3])).tracks[1:]]
    plot_loudness(signal, rms_dbfs(signal, window), Path(argv[1]), boundaries)


if __name__ == "__main__":
    main(sys.argv[1:])
