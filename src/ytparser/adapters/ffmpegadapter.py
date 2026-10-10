import subprocess
from pathlib import Path

from ytparser.core.models import Track


def cut_track_without_reencoding(source: Path, destination: Path, track: Track) -> None:
    duration = track.end - track.start
    subprocess.run(
        [
            # Première partie qui instancie le processus sur la commande ffmpeg, n'attends pas de saisie et n'écrase pas un fichier
            "ffmpeg",
            "-nostdin",
            "-n",
            # Précise le début de la découp, la source, la durée de la découpe
            "-ss",
            str(track.start),
            "-i",
            str(source),
            "-t",
            str(duration),
            # Précise que l'on veut le premier fichier d'entrée, seulement l'audio, et seulement le premier flux audio
            "-map",
            "0:a:0",
            # Une copie de l'audio sans réencodage et la destination
            "-c:a",
            "copy",
            str(destination),
        ],
        # Permet de vérifier que le sub process ne se termine pas en erreur
        check=True,
    )

def cut_track_with_reencoding(source: Path, destination: Path, track: Track) -> None:
    duration = track.end - track.start
    subprocess.run(
        [
            # Première partie qui instancie le processus sur la commande ffmpeg, n'attends pas de saisie et n'écrase pas un fichier
            "ffmpeg",
            "-nostdin",
            "-n",
            # Précise le début de la découp, la source, la durée de la découpe
            "-ss",
            str(track.start),
            "-i",
            str(source),
            "-t",
            str(duration),
            # Précise que l'on veut le premier fichier d'entrée, seulement l'audio, et seulement le premier flux audio
            "-map",
            "0:a:0",
            # Reencodage, avec un débit de 192kbit/s
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(destination),
        ],
        # Permet de vérifier que le sub process ne se termine pas en erreur
        check=True,
    )