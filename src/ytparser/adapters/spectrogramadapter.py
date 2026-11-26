"""Plot the spectrogram of an excerpt, optionally with the tracklist boundaries (exploration tool).

Usage:
    uv run python -m ytparser.adapters.spectrogramadapter SOURCE OUTPUT.png START END
        [TRACKLIST.yaml]

START and END are in seconds. The tracklist boundaries inside the excerpt are drawn in green.
Spectral flux, spectral change and the candidate cuts (orange) are computed on the whole file
and shown for the excerpt.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from ytparser.adapters.signaladapter import load_signal  # noqa: E402
from ytparser.adapters.yamladapter import load_tracklist  # noqa: E402
from ytparser.core.loudness import rms_dbfs  # noqa: E402
from ytparser.core.signal import AudioSignal  # noqa: E402
from ytparser.core.spectralchange import (  # noqa: E402
    ChangeCurve,
    find_candidates,
    spectral_change,
    spectral_flux,
)
from ytparser.core.spectrum import stft  # noqa: E402


def excerpt(signal: AudioSignal, start: float, end: float) -> AudioSignal:
    """Return the part of signal between start and end seconds."""
    if not 0 <= start < end:
        raise ValueError("START must be non-negative and before END.")
    first = round(start * signal.sample_rate)
    last = min(round(end * signal.sample_rate), len(signal.samples))
    return AudioSignal(signal.samples[first:last], signal.sample_rate)


def _within(curve: ChangeCurve, start: float, end: float) -> ChangeCurve:
    keep = (curve.times >= start) & (curve.times <= end)
    return ChangeCurve(curve.times[keep], curve.values[keep])


def plot_spectrogram(
    part: AudioSignal,
    offset: float,
    destination: Path,
    boundaries: list[float] | None = None,
    flux: ChangeCurve | None = None,
    change: ChangeCurve | None = None,
    candidates: list[float] | None = None,
) -> None:
    """Write a PNG with the spectrogram, the loudness and the spectral change of an excerpt.

    offset is the time of the excerpt in the source, so the axis shows source seconds.
    flux, change and candidates are in source seconds; those outside the excerpt are ignored.
    """
    spectrogram = stft(part)
    curve = rms_dbfs(part)
    end = offset + part.duration
    figure, (top, bottom, third) = plt.subplots(
        3, 1, sharex=True, figsize=(16, 10), gridspec_kw={"height_ratios": [3, 1, 1]}
    )
    extent = (
        offset + spectrogram.times[0],
        offset + spectrogram.times[-1],
        spectrogram.frequencies[0],
        spectrogram.frequencies[-1],
    )
    # Transposé : fréquences en vertical, temps en horizontal, graves en bas
    image = top.imshow(
        spectrogram.db.T, origin="lower", aspect="auto", extent=extent, vmin=-80, vmax=0
    )
    # La barre de couleurs prend la place des deux panneaux, pour que leurs axes restent alignés
    figure.colorbar(image, ax=[top, bottom, third], label="dB (relatif au maximum)", pad=0.01)
    top.set_ylabel("Fréquence (Hz)")
    bottom.plot(offset + curve.times, curve.dbfs, linewidth=0.8, color="tab:red")
    bottom.set_ylabel("RMS (dBFS)")
    bottom.set_ylim(-90, 0)
    bottom.grid(alpha=0.3)
    if flux is not None:
        part_flux = _within(flux, offset, end)
        third.plot(part_flux.times, part_flux.values, linewidth=0.5, color="gray", label="flux")
    if change is not None:
        part_change = _within(change, offset, end)
        third.plot(
            part_change.times,
            part_change.values,
            linewidth=1.4,
            color="tab:blue",
            label="changement (3 s)",
        )
    for moment in candidates or []:
        if offset <= moment <= end:
            third.axvline(moment, color="orange", linewidth=2, linestyle="--")
    third.set_ylabel("Changement (dB)")
    third.set_xlabel("Temps (s)")
    third.grid(alpha=0.3)
    third.legend(loc="upper right")
    for axis in (top, bottom, third):
        for moment in boundaries or []:
            axis.axvline(moment, color="lime", linewidth=1.2)
    top.set_xlim(offset, end)
    figure.savefig(destination, dpi=110)
    plt.close(figure)


def main(argv: list[str]) -> None:
    if len(argv) not in (4, 5):
        raise SystemExit(__doc__)
    start, end = float(argv[2]), float(argv[3])
    signal = load_signal(Path(argv[0]))
    part = excerpt(signal, start, end)
    # Calculé sur tout le fichier : les fenêtres de 3 s ne subissent pas d'effet de bord
    spectrogram = stft(signal, hop=512)
    flux = spectral_flux(spectrogram)
    change = spectral_change(spectrogram)
    candidates = find_candidates(change)
    boundaries = None
    if len(argv) == 5:
        starts = [track.start for track in load_tracklist(Path(argv[4])).tracks[1:]]
        boundaries = [moment for moment in starts if start <= moment <= end]
    plot_spectrogram(part, start, Path(argv[1]), boundaries, flux, change, candidates)
    print(f"{np.round(end - start, 1)} s tracés dans {argv[1]}")


if __name__ == "__main__":
    main(sys.argv[1:])
