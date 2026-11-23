import pytest

from ytparser.adapters import ytdlpadapter
from ytparser.adapters.ytdlpadapter import (
    VideoFetchError,
    fetch_video_info,
    video_info_from_ytdlp,
)
from ytparser.core.video import Chapter, Comment


def test_full_ytdlp_info_is_converted() -> None:
    info = {
        "title": "Mix",
        "duration": 3600,
        "description": "0:00 A",
        "chapters": [{"start_time": 0.0, "end_time": 10.0, "title": "A"}, {"start_time": 10}],
        "comments": [{"text": "1:00 B", "like_count": 3}, {"text": "", "like_count": 9}],
    }

    video = video_info_from_ytdlp(info)

    assert video.title == "Mix"
    assert video.duration == 3600.0
    assert video.description == "0:00 A"
    assert video.chapters == (Chapter(0.0, "A"), Chapter(10.0, ""))
    assert video.comments == (Comment("1:00 B", 3),)


def test_missing_optional_fields_become_empty() -> None:
    info = {"title": "Mix", "duration": 60, "chapters": None, "comments": None, "description": None}

    video = video_info_from_ytdlp(info)

    assert (video.description, video.chapters, video.comments) == ("", (), ())


@pytest.mark.parametrize("info", [None, {"title": "Live"}, {"title": "x", "duration": None}])
def test_missing_duration_or_info_raises(info) -> None:
    with pytest.raises(VideoFetchError):
        video_info_from_ytdlp(info)


def test_fetch_never_downloads_and_wraps_yt_dlp_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict = {}

    class FakeYoutubeDL:
        def __init__(self, options: dict) -> None:
            seen["options"] = options

        def __enter__(self) -> "FakeYoutubeDL":
            return self

        def __exit__(self, *exc_info) -> None:
            return None

        def extract_info(self, url: str, download: bool) -> dict:
            seen["download"] = download
            if "bad" in url:
                raise ytdlpadapter.DownloadError("Video unavailable")
            return {"title": "Mix", "duration": 60}

    monkeypatch.setattr(ytdlpadapter, "YoutubeDL", FakeYoutubeDL)

    assert fetch_video_info("https://youtu.be/ok").title == "Mix"
    assert seen["download"] is False
    assert seen["options"]["skip_download"] is True
    assert seen["options"]["getcomments"] is True

    with pytest.raises(VideoFetchError, match="Video unavailable"):
        fetch_video_info("https://youtu.be/bad")
