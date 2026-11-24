import pytest

from ytparser.core.config import Config, ConfigError, parse_config, resolve_format
from ytparser.core.download import OutputFormat


def test_empty_config_means_defaults() -> None:
    assert parse_config({}) == Config(format=None, mp3_bitrate="192k")


def test_valid_config() -> None:
    config = parse_config({"format": "opus", "mp3_bitrate": "256k"})
    assert config == Config(format=OutputFormat.OPUS, mp3_bitrate="256k")


@pytest.mark.parametrize(
    "data",
    [
        {"format": "wav"},
        {"mp3_bitrate": "fast"},
        {"mp3_bitrate": 192},
        {"formt": "mp3"},
    ],
)
def test_invalid_config_is_rejected(data: dict[str, object]) -> None:
    with pytest.raises(ConfigError):
        parse_config(data)


@pytest.mark.parametrize(
    ("cli_value", "config_format", "expected"),
    [
        (OutputFormat.MP3, OutputFormat.OPUS, OutputFormat.MP3),  # option > config
        (None, OutputFormat.OPUS, OutputFormat.OPUS),  # config > default
        (None, None, OutputFormat.M4A),  # default
        (OutputFormat.M4A, OutputFormat.OPUS, OutputFormat.M4A),  # option even if equal to default
    ],
)
def test_format_priority(
    cli_value: OutputFormat | None, config_format: OutputFormat | None, expected: OutputFormat
) -> None:
    assert resolve_format(cli_value, Config(format=config_format)) == expected
