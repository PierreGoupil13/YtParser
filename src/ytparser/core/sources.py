"""Choose where the timestamps come from: chapters, then description, then comments."""

from dataclasses import dataclass

from ytparser.core.timestamps import TimestampEntry, parse_timestamps
from ytparser.core.video import Comment, VideoInfo

# A single timestamp is not a tracklist ("best part at 3:45").
MIN_TIMESTAMPS = 2


@dataclass(frozen=True, slots=True)
class CommentCandidate:
    comment: Comment
    entries: tuple[TimestampEntry, ...]


@dataclass(frozen=True, slots=True)
class SourceSelection:
    """Timestamps retained by select_source.

    source is "chapters", "description" or "comment" (the `detected_from` values of the PRD).
    For comments, candidates lists every ranked candidate and chosen is the index used.
    """

    source: str
    entries: tuple[TimestampEntry, ...]
    candidates: tuple[CommentCandidate, ...] = ()
    chosen: int = 0


def rank_comment_candidates(comments: tuple[Comment, ...]) -> tuple[CommentCandidate, ...]:
    """Keep comments holding a tracklist, most timestamps first, then most liked.

    The sort is stable, so ties keep the order given by YouTube.
    """
    candidates = []
    for comment in comments:
        entries = tuple(parse_timestamps(comment.text))
        if len(entries) >= MIN_TIMESTAMPS:
            candidates.append(CommentCandidate(comment, entries))
    return tuple(sorted(candidates, key=lambda c: (-len(c.entries), -c.comment.like_count)))


def select_source(info: VideoInfo, comment_choice: int | None = None) -> SourceSelection:
    """Pick the most reliable source of timestamps.

    comment_choice is a 0-based index in the ranked comment candidates. Giving it forces
    the comments source, even when chapters or a description are available.
    """
    if comment_choice is None:
        if len(info.chapters) >= MIN_TIMESTAMPS:
            entries = tuple(TimestampEntry(c.start, c.title) for c in info.chapters)
            return SourceSelection("chapters", entries)

        entries = tuple(parse_timestamps(info.description))
        if len(entries) >= MIN_TIMESTAMPS:
            return SourceSelection("description", entries)

    candidates = rank_comment_candidates(info.comments)
    chosen = 0 if comment_choice is None else comment_choice
    if not candidates:
        raise ValueError("No usable timestamps found in chapters, description or comments.")
    if not 0 <= chosen < len(candidates):
        raise ValueError(f"Comment choice must be between 1 and {len(candidates)}.")
    return SourceSelection("comment", candidates[chosen].entries, candidates, chosen)
