import pytest

from ytparser.core.timestamps import TimestampEntry, parse_timestamps


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("1:23 Artist - Title", (83.0, "Artist - Title")),
        ("0:00 Intro", (0.0, "Intro")),
        ("01:23:45 Long track", (5025.0, "Long track")),
        ("1:02:03 Long track", (3723.0, "Long track")),
        ("[1:23] Artist - Title", (83.0, "Artist - Title")),
        ("(1:23) Artist - Title", (83.0, "Artist - Title")),
        ("1:23 - Artist - Title", (83.0, "Artist - Title")),
        ("1:23 – Artist - Title", (83.0, "Artist - Title")),
        ("1:23 | Artist - Title", (83.0, "Artist - Title")),
        ("1:23: Artist - Title", (83.0, "Artist - Title")),
        ("  1:23   Artist - Title  ", (83.0, "Artist - Title")),
        ("1. 1:23 Artist - Title", (83.0, "Artist - Title")),
        ("05) 1:23 Artist - Title", (83.0, "Artist - Title")),
        ("- 1:23 Artist - Title", (83.0, "Artist - Title")),
        ("• 1:23 Artist - Title", (83.0, "Artist - Title")),
        ("0:00 - 3:45 Artist - Title", (0.0, "Artist - Title")),
        ("Artist - Title 3:45", (225.0, "Artist - Title")),
        ("Artist - Title - [3:45]", (225.0, "Artist - Title")),
        ("1:23", (83.0, "")),
        ("1:23 -", (83.0, "")),
        ("0:00 Song (Remix)", (0.0, "Song (Remix)")),
        ("0:00 3:45 Title", (0.0, "3:45 Title")),
    ],
)
def test_parse_timestamps_handles_real_world_formats(
    line: str, expected: tuple[float, str]
) -> None:
    assert parse_timestamps(line) == [TimestampEntry(*expected)]


@pytest.mark.parametrize(
    "line",
    [
        "",
        "Tracklist:",
        "Follow me on https://example.com:8080/page",
        "Released in 2019, 12 tracks",
        "1:75 Invalid seconds",
        "1:70:00 Invalid minutes",
        "1:234 Too many digits",
        "123:45 Three-digit minutes",
    ],
)
def test_parse_timestamps_ignores_lines_without_valid_timestamp(line: str) -> None:
    assert parse_timestamps(line) == []


def test_parse_timestamps_extracts_entries_in_order_from_multiline_text() -> None:
    text = (
        "Best of 2020 mix\n"
        "\n"
        "Tracklist:\n"
        "0:00 First - Song\n"
        "3:30 Second - Song\n"
        "1:02:03 Third - Song\n"
        "Subscribe!\n"
    )

    assert parse_timestamps(text) == [
        TimestampEntry(0.0, "First - Song"),
        TimestampEntry(210.0, "Second - Song"),
        TimestampEntry(3723.0, "Third - Song"),
    ]


def test_parse_timestamps_handles_windows_line_endings() -> None:
    assert parse_timestamps("0:00 A\r\n1:00 B\r\n") == [
        TimestampEntry(0.0, "A"),
        TimestampEntry(60.0, "B"),
    ]
