from pathlib import Path

from ytparser.core.models import Tracklist
from ytparser.core.yamlwriter import from_yaml, to_yaml


def load_tracklist(path: Path) -> Tracklist:
    return from_yaml(path.read_text(encoding="utf-8"))


def save_tracklist(path: Path, tracksYaml: Tracklist) -> None:
    path.write_text(to_yaml(tracksYaml), encoding="utf-8")
