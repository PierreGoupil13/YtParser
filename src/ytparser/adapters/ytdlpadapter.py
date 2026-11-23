"""Fetch video metadata with yt-dlp, without downloading the video."""

from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from ytparser.core.video import Chapter, Comment, VideoInfo

MAX_COMMENTS = "200"


class VideoFetchError(Exception):
    """The video metadata could not be retrieved."""


def fetch_video_info(url: str) -> VideoInfo:
    options: dict[str, Any] = {
        "skip_download": True,
        "getcomments": True,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        # Top-level comments only, best ones first: max-comments, max-parents, replies...
        "extractor_args": {
            "youtube": {
                "comment_sort": ["top"],
                "max_comments": [MAX_COMMENTS, "all", "0", "0"],
            }
        },
    }
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except DownloadError as error:
        raise VideoFetchError(str(error)) from error
    return video_info_from_ytdlp(info)


def video_info_from_ytdlp(info: dict[str, Any] | None) -> VideoInfo:
    """Convert the dictionary returned by yt-dlp; missing optional fields become empty."""
    if not isinstance(info, dict):
        raise VideoFetchError("yt-dlp returned no information for this URL.")

    duration = info.get("duration")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0:
        raise VideoFetchError("The video has no known duration (live stream?).")

    chapters = tuple(
        Chapter(float(chapter["start_time"]), str(chapter.get("title") or ""))
        for chapter in info.get("chapters") or []
        if chapter.get("start_time") is not None
    )
    comments = tuple(
        Comment(str(comment["text"]), int(comment.get("like_count") or 0))
        for comment in info.get("comments") or []
        if comment.get("text")
    )
    return VideoInfo(
        title=str(info.get("title") or ""),
        duration=float(duration),
        description=str(info.get("description") or ""),
        chapters=chapters,
        comments=comments,
    )
