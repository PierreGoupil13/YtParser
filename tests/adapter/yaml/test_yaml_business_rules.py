import pytest
from yaml import safe_dump

from ytparser.core.yamlwriter import from_yaml


def track_data(number: int, start: str = "00:00:00", end: str = "00:00:10") -> dict[str, object]:
    return {
        "number": number,
        "start": start,
        "end": end,
        "title": "Title",
        "artist": "Artist",
    }


def test_from_yaml_rejects_empty_tracklist() -> None:
    with pytest.raises(ValueError, match=r"(?i)at least one track"):
        from_yaml("tracks: []")


@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param("00:00:10", "00:00:10", id="equal-boundaries"),
        pytest.param("00:00:11", "00:00:10", id="reversed-boundaries"),
    ],
)
def test_from_yaml_rejects_invalid_track_interval(start: str, end: str) -> None:
    text = safe_dump({"tracks": [track_data(1, start, end)]})

    with pytest.raises(ValueError, match=r"(?i)start.*end"):
        from_yaml(text)


@pytest.mark.parametrize(
    "tracks",
    [
        pytest.param(
            [track_data(1, end="00:00:12"), track_data(2, "00:00:10", "00:00:20")],
            id="overlapping-tracks",
        ),
        pytest.param(
            [track_data(1, "00:00:10", "00:00:20"), track_data(2)],
            id="out-of-order-tracks",
        ),
    ],
)
def test_from_yaml_rejects_overlap_or_wrong_order(tracks: list[dict[str, object]]) -> None:
    text = safe_dump({"tracks": tracks})

    with pytest.raises(ValueError, match=r"(?i)overlap"):
        from_yaml(text)


@pytest.mark.parametrize(
    "tracks",
    [
        pytest.param([track_data(2)], id="numbering-starts-at-two"),
        pytest.param(
            [track_data(1), track_data(3, "00:00:10", "00:00:20")],
            id="missing-number",
        ),
        pytest.param(
            [track_data(1), track_data(1, "00:00:10", "00:00:20")],
            id="duplicate-number",
        ),
    ],
)
def test_from_yaml_rejects_inconsistent_numbers(tracks: list[dict[str, object]]) -> None:
    text = safe_dump({"tracks": tracks})

    with pytest.raises(ValueError, match=r"(?i)numbers"):
        from_yaml(text)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        pytest.param("number", "1", "number", id="string-number"),
        pytest.param("number", True, "number", id="boolean-number"),
        pytest.param("number", 1.5, "number", id="fractional-number"),
        pytest.param("number", 0, "number", id="zero-number"),
        pytest.param("title", None, "title", id="null-title"),
        pytest.param("artist", None, "artist", id="null-artist"),
    ],
)
def test_from_yaml_rejects_invalid_business_field(field: str, value: object, message: str) -> None:
    track = track_data(1)
    track[field] = value
    text = safe_dump({"tracks": [track]})

    with pytest.raises(ValueError, match=message):
        from_yaml(text)


def test_from_yaml_accepts_gap_between_tracks() -> None:
    text = safe_dump({"tracks": [track_data(1), track_data(2, "00:00:12", "00:00:20")]})

    restored = from_yaml(text)

    assert len(restored.tracks) == 2
    assert restored.tracks[0].end == 10
    assert restored.tracks[1].start == 12
