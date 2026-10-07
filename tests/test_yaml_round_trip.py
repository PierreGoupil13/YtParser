from ytparser.core.yamlwriter import to_yaml, from_yaml, convertTimeToSec, convertSecToTime
from ytparser.core.models import Track, Tracklist
import pytest

def test_yaml_round_trip_preserves_tracklist() -> None:
    original = Tracklist(
        tracks=(
            Track(1, 0, 65.123, "Été", "Artiste A"),
            Track(2, 65.123, 3723.486, "Final", "Artiste B"),
        )
    )

    text = to_yaml(original)
    restored = from_yaml(text)
    assert restored == original

@pytest.mark.parametrize(
    ("secondes", "time"),
    [
        (0, "00:00:00"),
        (3, "00:00:03"),
        (3.0, "00:00:03"),
        (3.5, "00:00:03.5"),
        (0.001, "00:00:00.001"),
        (59.999, "00:00:59.999"),
        (60, "00:01:00"),
        (65.123, "00:01:05.123"),
        (134.5, "00:02:14.5"),
        (157.56, "00:02:37.56"),
        (3599.999, "00:59:59.999"),
        (3600, "01:00:00"),
        (3723.486, "01:02:03.486"),
        (86400, "24:00:00"),
        (360000, "100:00:00"),
    ],
)
def test_conversion_time_sec(secondes: float, time: str) -> None:
    time_converted = convertSecToTime(secondes)
    assert time_converted == time
    secondes_converted = convertTimeToSec(time)
    assert secondes_converted == secondes

