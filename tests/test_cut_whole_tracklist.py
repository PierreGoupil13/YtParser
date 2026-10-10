from pathlib import Path
import json
import subprocess
from ytparser.adapters import yamladapter, ffmpegadapter
from ytparser.core.models import Tracklist 
import pytest


def test_cut_whole_tracklist_without_reencoding(tmp_path: Path) -> None:
    # Importer le yaml et en faire une tracklist
    fixtures_dir: Path = Path(__file__).resolve().parent / "fixtures"
    source: Path = fixtures_dir / "UC1.mp3"
    yaml_path: Path = fixtures_dir / "UC1.yaml"

    assert source.is_file()
    assert yaml_path.is_file()

    tracklist: Tracklist = yamladapter.load_tracklist(yaml_path)

    assert len(tracklist.tracks) == 22


    for track in tracklist.tracks:
        destination = tmp_path / f"{track.title}.mp3"
        ffmpegadapter.cut_track_without_reencoding(source, destination, track)

        # Partie qui vérifie l'exactitude de la coupe
        probe = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration:stream=codec_type,sample_rate",
                "-of", "json",
                str(destination),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        metadata = json.loads(probe.stdout)

        expected_duration = track.end - track.start
        actual_duration = float(metadata["format"]["duration"])
        difference = actual_duration - expected_duration    

        audio_stream = next(
            stream for stream in metadata["streams"]
            if stream["codec_type"] == "audio"
        )
        sample_rate = int(audio_stream["sample_rate"])
        duration_tolerance = 3 * 1152 / sample_rate

        print(
            f"{track.number:02d} — {track.title} : "
            f"attendue={expected_duration:.3f}s, "
            f"mesurée={actual_duration:.3f}s, "
            f"écart={difference:+.3f}s"
        )

        assert actual_duration == pytest.approx(
            expected_duration, abs=duration_tolerance
        ), f"Durée incorrecte pour {track.title} : écart de {difference:+.3f}s"

    print(f"Sorties audio : {tmp_path}")
    print(tracklist)

def test_cut_whole_tracklist_with_reencoding(tmp_path: Path) -> None:
    # Importer le yaml et en faire une tracklist
    fixtures_dir: Path = Path(__file__).resolve().parent / "fixtures"
    source: Path = fixtures_dir / "UC1.mp3"
    yaml_path: Path = fixtures_dir / "UC1.yaml"

    assert source.is_file()
    assert yaml_path.is_file()

    tracklist: Tracklist = yamladapter.load_tracklist(yaml_path)

    assert len(tracklist.tracks) == 22


    for track in tracklist.tracks:
        destination = tmp_path / f"{track.title}.mp3"
        ffmpegadapter.cut_track_with_reencoding(source, destination, track)

        # Partie qui vérifie l'exactitude de la coupe
        probe = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration:stream=codec_type,sample_rate",
                "-of", "json",
                str(destination),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        metadata = json.loads(probe.stdout)

        expected_duration = track.end - track.start
        actual_duration = float(metadata["format"]["duration"])
        difference = actual_duration - expected_duration    

        audio_stream = next(
            stream for stream in metadata["streams"]
            if stream["codec_type"] == "audio"
        )
        sample_rate = int(audio_stream["sample_rate"])
        duration_tolerance = 3 * 1152 / sample_rate

        print(
            f"{track.number:02d} — {track.title} : "
            f"attendue={expected_duration:.3f}s, "
            f"mesurée={actual_duration:.3f}s, "
            f"écart={difference:+.3f}s"
        )

        assert actual_duration == pytest.approx(
            expected_duration, abs=duration_tolerance
        ), f"Durée incorrecte pour {track.title} : écart de {difference:+.3f}s"

    print(f"Sorties audio : {tmp_path}")
    print(tracklist)