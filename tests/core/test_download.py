import pytest

from ytparser.core.download import (
    UPDATE_HINT,
    OutputFormat,
    explain_download_error,
    source_plan,
)


@pytest.mark.parametrize(
    ("target", "first_choice"),
    [
        (OutputFormat.M4A, "bestaudio[acodec^=mp4a]"),
        (OutputFormat.OPUS, "bestaudio[acodec=opus]"),
        (OutputFormat.MP3, "bestaudio"),
    ],
)
def test_each_format_selects_its_source_stream(target: OutputFormat, first_choice: str) -> None:
    assert source_plan(target).selector.split("/")[0] == first_choice


@pytest.mark.parametrize("target", list(OutputFormat))
def test_every_selector_ends_with_a_generic_fallback(target: OutputFormat) -> None:
    assert source_plan(target).selector.split("/")[-1] == "bestaudio"


def test_preferred_codec_detection() -> None:
    assert source_plan(OutputFormat.M4A).is_preferred("aac")
    assert not source_plan(OutputFormat.M4A).is_preferred("opus")
    assert source_plan(OutputFormat.MP3).is_preferred("anything")


def test_unavailable_video_message_has_no_update_hint() -> None:
    message = explain_download_error("ERROR: [youtube] abc: Video unavailable")

    assert "unavailable" in message
    assert UPDATE_HINT not in message


def test_other_errors_suggest_updating_yt_dlp() -> None:
    message = explain_download_error("ERROR: unable to extract player response")

    assert "unable to extract player response" in message
    assert UPDATE_HINT in message
