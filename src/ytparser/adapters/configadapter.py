"""Config adapter: read the user settings from a YAML file."""

import os
from pathlib import Path

import yaml

from ytparser.core.config import Config, ConfigError, parse_config

CONFIG_NAMES = ("config.yaml", "config.yml")


def default_config_path() -> Path:
    """Return the existing config.yaml / config.yml of the user folder (config.yaml if none).

    The folder is %APPDATA%\\ytparser on Windows, ~/.config/ytparser elsewhere.
    """
    appdata = os.environ.get("APPDATA")
    folder = (Path(appdata) if appdata else Path.home() / ".config") / "ytparser"
    for name in CONFIG_NAMES:
        if (folder / name).is_file():
            return folder / name
    return folder / CONFIG_NAMES[0]


def load_config(path: Path | None = None) -> Config:
    """Read the config file; a missing or empty file means default settings."""
    path = path or default_config_path()
    if not path.is_file():
        return Config()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ConfigError(f"{path} is not valid YAML: {error}") from error
    if data is None:
        return Config()
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: expected 'name: value' settings at the top level.")
    try:
        return parse_config(data)
    except ConfigError as error:
        raise ConfigError(f"{path}: {error}") from error
