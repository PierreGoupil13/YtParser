import pytest

from ytparser.core.yamlwriter import convertTimeToSec


@pytest.mark.parametrize(
    "time",
    [
        pytest.param("00:60:00", id="minutes-out-of-range"),
        pytest.param("00:00:60", id="seconds-out-of-range"),
        pytest.param("00:00:60.001", id="fractional-seconds-out-of-range"),
        pytest.param("-01:00:00", id="negative-hours"),
        pytest.param("00:-01:00", id="negative-minutes"),
        pytest.param("00:00:-00.5", id="negative-seconds"),
        pytest.param("abc", id="not-a-time"),
        pytest.param("", id="empty-time"),
        pytest.param("00:01", id="missing-component"),
        pytest.param("00:01:02:03", id="extra-component"),
        pytest.param("00::03", id="empty-component"),
        pytest.param("00:00:abc", id="non-numeric-seconds"),
        pytest.param("00:00:NaN", id="non-finite-nan"),
        pytest.param("00:00:Infinity", id="non-finite-infinity"),
    ],
)
def test_time_to_seconds_rejects_invalid_times(time: str) -> None:
    with pytest.raises(ValueError):
        convertTimeToSec(time)
