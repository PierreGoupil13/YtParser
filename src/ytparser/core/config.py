"""Pure rules for user settings: validation of the config values and option priority."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ytparser.core.download import OutputFormat
from ytparser.core.profiles import DEFAULT_MP3_BITRATE, is_valid_bitrate

DEFAULT_FORMAT = OutputFormat.M4A
KNOWN_KEYS = ("format", "mp3_bitrate")


class ConfigError(ValueError):
    """The user configuration contains an invalid or unknown setting."""


@dataclass(frozen=True)
class Config:
    format: OutputFormat | None = None  # None = not set in the file
    mp3_bitrate: str = DEFAULT_MP3_BITRATE


def parse_config(data: Mapping[str, Any]) -> Config:
    """Validate the content of the config file (already parsed from YAML)."""
    unknown = sorted(set(data) - set(KNOWN_KEYS))
    if unknown:
        raise ConfigError(
            f"Unknown setting(s): {', '.join(unknown)}. Known: {', '.join(KNOWN_KEYS)}."
        )
    audio_format = None
    if "format" in data:
        try:
            audio_format = OutputFormat(data["format"])
        except ValueError:
            choices = ", ".join(fmt.value for fmt in OutputFormat)
            raise ConfigError(
                f"Invalid format {data['format']!r}; expected one of: {choices}."
            ) from None
    bitrate = data.get("mp3_bitrate", DEFAULT_MP3_BITRATE)
    if not isinstance(bitrate, str) or not is_valid_bitrate(bitrate):
        raise ConfigError(f"Invalid mp3_bitrate {bitrate!r}; expected a string such as '192k'.")
    return Config(format=audio_format, mp3_bitrate=bitrate)


def resolve_format(cli_value: OutputFormat | None, config: Config) -> OutputFormat:
    """Priority: command-line option, then config file, then the default (m4a)."""
    if cli_value is not None:
        return cli_value
    if config.format is not None:
        return config.format
    return DEFAULT_FORMAT
