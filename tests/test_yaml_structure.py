import pytest
from yaml import YAMLError, safe_dump

from ytparser.core.models import Track, Tracklist
from ytparser.core.yamlwriter import from_yaml


def valid_track_data() -> dict[str, int | str]:
    return {
        "number": 1,
        "start": "00:00:00",
        "end": "00:01:05.123",
        "title": "Été",
        "artist": "Artiste A",
    }


def test_from_yaml_accepts_valid_document() -> None:
    text = """
tracks:
  - number: 1
    start: "00:00:00"
    end: "00:01:05.123"
    title: "Été"
    artist: "Artiste A"
"""

    restored = from_yaml(text)

    assert restored == Tracklist((Track(1, 0, 65.123, "Été", "Artiste A"),))


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("", id="empty-document"),
        pytest.param("# Only a comment\n", id="comment-only-document"),
        pytest.param("null", id="null-document"),
        pytest.param("42", id="numeric-document"),
        pytest.param("a title", id="string-document"),
        pytest.param("[]", id="list-document"),
    ],
)
def test_from_yaml_rejects_non_mapping_document(text: str) -> None:
    with pytest.raises(ValueError, match=r"(?i)document"):
        from_yaml(text)


def test_from_yaml_rejects_missing_tracks() -> None:
    with pytest.raises(ValueError, match=r"(?i)tracks"):
        from_yaml("album: Compilation")


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(None, id="null-tracks"),
        pytest.param(42, id="numeric-tracks"),
        pytest.param("a title", id="string-tracks"),
        pytest.param({}, id="mapping-tracks"),
    ],
)
def test_from_yaml_rejects_non_list_tracks(value: object) -> None:
    text = safe_dump({"tracks": value})

    with pytest.raises(ValueError, match=r"(?i)tracks"):
        from_yaml(text)


@pytest.mark.parametrize(
    "entry",
    [
        pytest.param(None, id="null-entry"),
        pytest.param(42, id="numeric-entry"),
        pytest.param("a title", id="string-entry"),
        pytest.param([], id="list-entry"),
    ],
)
def test_from_yaml_rejects_non_mapping_track(entry: object) -> None:
    text = safe_dump({"tracks": [entry]})

    with pytest.raises(ValueError, match=r"(?i)track"):
        from_yaml(text)


@pytest.mark.parametrize("field", ["number", "start", "end", "title", "artist"])
def test_from_yaml_rejects_missing_track_field(field: str) -> None:
    track = valid_track_data()
    del track[field]
    text = safe_dump({"tracks": [track]})

    with pytest.raises(ValueError, match=field):
        from_yaml(text)


@pytest.mark.parametrize("field", ["start", "end"])
@pytest.mark.parametrize(
    "value",
    [
        pytest.param(None, id="null-time"),
        pytest.param(3, id="integer-time"),
        pytest.param(3.5, id="float-time"),
        pytest.param(True, id="boolean-time"),
    ],
)
def test_from_yaml_rejects_non_string_time(field: str, value: object) -> None:
    track: dict[str, object] = dict(valid_track_data())
    track[field] = value
    text = safe_dump({"tracks": [track]})

    with pytest.raises(ValueError, match=field):
        from_yaml(text)


def test_from_yaml_rejects_invalid_yaml_syntax() -> None:
    with pytest.raises(YAMLError):
        from_yaml("tracks: [")
