"""FFmpeg adapter: cut tracks out of a local audio file."""

import json
import shutil
import subprocess
from pathlib import Path

from ytparser.core.cutplan import check_tracklist_fits, track_filenames
from ytparser.core.models import Track, Tracklist

REQUIRED_TOOLS = ("ffmpeg", "ffprobe")


class ToolNotFoundError(FileNotFoundError):
    """FFmpeg or ffprobe cannot be found on the PATH."""


def probe_duration(source: Path) -> float:
    """Return the duration of an audio file in seconds, as reported by ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", _arg(source)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    duration = json.loads(result.stdout).get("format", {}).get("duration")
    if duration is None:
        raise ValueError(f"ffprobe could not read the duration of {source}.")
    return float(duration)


def cut_tracklist(source: Path, tracklist: Tracklist, output_dir: Path) -> list[Path]:
    """Cut every track by stream copy into output_dir and return the created files in order."""
    missing = [tool for tool in REQUIRED_TOOLS if shutil.which(tool) is None]
    if missing:
        raise ToolNotFoundError(
            f"{' and '.join(missing)} not found. Install FFmpeg and add it to the PATH."
        )
    check_tracklist_fits(tracklist, probe_duration(source))
    destinations = [output_dir / name for name in track_filenames(tracklist, source.suffix)]
    # Tout vérifier avant la première découpe, pour ne pas laisser un dossier à moitié rempli
    existing = [path for path in destinations if path.exists()]
    if existing:
        raise FileExistsError(
            f"{existing[0]} already exists ({len(existing)} conflicting file(s)). "
            "Choose another output folder or remove these files."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    for track, destination in zip(tracklist.tracks, destinations, strict=True):
        cut_track_without_reencoding(source, destination, track)
    return destinations


def cut_track_without_reencoding(source: Path, destination: Path, track: Track) -> None:
    # Copie du flux sans réencodage : rapide, sans nouvelle perte, coupe alignée sur les trames
    _run_cut(source, destination, track, ["-c:a", "copy"])


def cut_track_with_reencoding(source: Path, destination: Path, track: Track) -> None:
    # Réencodage MP3 à 192 kbit/s : coupe à l'échantillon près, mais nouvelle compression
    _run_cut(source, destination, track, ["-c:a", "libmp3lame", "-b:a", "192k"])


def _run_cut(source: Path, destination: Path, track: Track, codec_args: list[str]) -> None:
    subprocess.run(
        [
            # Pas de saisie attendue, pas d'écrasement, seulement les erreurs dans le terminal
            "ffmpeg",
            "-nostdin",
            "-n",
            "-v",
            "error",
            # -ss avant -i : recherche dans la source ; -t : durée de la piste, pas l'instant de fin
            "-ss",
            _seconds(track.start),
            "-i",
            _arg(source),
            "-t",
            _seconds(track.end - track.start),
            # Premier fichier d'entrée, seulement l'audio, et seulement le premier flux audio
            "-map",
            "0:a:0",
            *codec_args,
            _arg(destination),
        ],
        # Un code de sortie non nul de FFmpeg lève CalledProcessError
        check=True,
    )


def _seconds(value: float) -> str:
    # Virgule fixe : FFmpeg refuse la notation 5e-05 que str() produit pour les petites valeurs
    return f"{value:.6f}"


def _arg(path: Path) -> str:
    # Chemin absolu : un nom relatif commençant par « - » serait lu comme une option
    return str(path.absolute())
