import pytest

from ytparser.core.download import OutputFormat, source_plan
from ytparser.core.profiles import (
    DEFAULT_PROFILE,
    M4A_PROFILE,
    OPUS_PROFILE,
    get_profile,
    mp3_profile,
)


def test_m4a_profile_copies_the_aac_stream() -> None:
    assert M4A_PROFILE.extension == ".m4a"
    assert M4A_PROFILE.source == source_plan(OutputFormat.M4A)
    assert M4A_PROFILE.codec_args == ("-c:a", "copy")
    assert M4A_PROFILE.preroll == 0
    assert DEFAULT_PROFILE is M4A_PROFILE


def test_opus_profile_remuxes_the_opus_stream() -> None:
    assert OPUS_PROFILE.extension == ".opus"
    assert OPUS_PROFILE.source.preferred_codec == "opus"
    assert OPUS_PROFILE.codec_args == ("-c:a", "copy")


def test_mp3_profile_reencodes_with_the_requested_bitrate() -> None:
    profile = mp3_profile("256k")
    assert profile.extension == ".mp3"
    assert profile.codec_args == ("-c:a", "libmp3lame", "-b:a", "256k")
    assert profile.preroll > 0


@pytest.mark.parametrize("bitrate", ["", "192", "k", "fast", "0k", "1000k"])
def test_mp3_profile_rejects_invalid_bitrate(bitrate: str) -> None:
    with pytest.raises(ValueError, match="bitrate"):
        mp3_profile(bitrate)


@pytest.mark.parametrize("target", list(OutputFormat))
def test_get_profile_returns_the_profile_of_each_format(target: OutputFormat) -> None:
    assert get_profile(target).format == target
    assert get_profile(target).source == source_plan(target)


def test_get_profile_passes_the_mp3_bitrate() -> None:
    assert get_profile(OutputFormat.MP3, "128k").codec_args[-1] == "128k"
