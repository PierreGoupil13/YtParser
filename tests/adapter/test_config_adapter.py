from pathlib import Path

import pytest

from ytparser.adapters.configadapter import default_config_path, load_config
from ytparser.core.config import Config, ConfigError
from ytparser.core.download import OutputFormat


def write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_missing_file_gives_default_settings(tmp_path: Path) -> None:
    assert load_config(tmp_path / "absent.yaml") == Config()


def test_empty_file_gives_default_settings(tmp_path: Path) -> None:
    assert load_config(write(tmp_path, "# rien\n")) == Config()


def test_reads_yaml_file(tmp_path: Path) -> None:
    path = write(tmp_path, "format: mp3\nmp3_bitrate: 320k\n")
    assert load_config(path) == Config(format=OutputFormat.MP3, mp3_bitrate="320k")


def test_invalid_yaml_names_the_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="config.yaml"):
        load_config(write(tmp_path, "format: [mp3\n"))


def test_non_mapping_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="top level"):
        load_config(write(tmp_path, "- mp3\n"))


def test_invalid_value_names_the_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"config\.yaml.*wav"):
        load_config(write(tmp_path, "format: wav\n"))


def test_numeric_bitrate_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="mp3_bitrate"):
        load_config(write(tmp_path, "mp3_bitrate: 192\n"))


def test_default_path_uses_appdata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert default_config_path() == tmp_path / "ytparser" / "config.yaml"


def test_default_path_accepts_the_yml_extension(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    (tmp_path / "ytparser").mkdir()
    (tmp_path / "ytparser" / "config.yml").write_text("format: opus\n", encoding="utf-8")
    assert default_config_path() == tmp_path / "ytparser" / "config.yml"
    assert load_config(default_config_path()) == Config(format=OutputFormat.OPUS)
