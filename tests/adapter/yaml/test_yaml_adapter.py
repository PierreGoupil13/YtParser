from ytparser.adapters.yamladapter import load_tracklist, save_tracklist
from ytparser.core.models import Track, Tracklist


def test_tracklist_file_round_trip(tmp_path) -> None:
    original = Tracklist(
        tracks=(
            Track(1, 0, 65.123, "Été", "Artiste A"),
            Track(2, 65.123, 3723.486, "Final", "Artiste B"),
        )
    )
    path = tmp_path / "tracklist.yaml"

    save_tracklist(path, original)

    assert path.is_file()
    assert load_tracklist(path) == original
