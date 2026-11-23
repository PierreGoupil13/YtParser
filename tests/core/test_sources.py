import pytest

from ytparser.core.sources import rank_comment_candidates, select_source
from ytparser.core.timestamps import TimestampEntry
from ytparser.core.video import Chapter, Comment, VideoInfo

CHAPTERS = (Chapter(0, "Chapter A"), Chapter(100, "Chapter B"))
DESCRIPTION = "Tracklist\n0:00 Desc A\n2:00 Desc B\n"
COMMENT_2 = Comment("0:00 One\n1:00 Two", like_count=5)
COMMENT_3 = Comment("0:00 One\n1:00 Two\n2:00 Three", like_count=1)
COMMENT_3_POPULAR = Comment("0:00 X\n1:00 Y\n2:00 Z", like_count=50)


def make_info(**overrides) -> VideoInfo:
    return VideoInfo(title="Mix", duration=300, **overrides)


def test_chapters_win_over_description_and_comments() -> None:
    info = make_info(chapters=CHAPTERS, description=DESCRIPTION, comments=(COMMENT_2,))

    selection = select_source(info)

    assert selection.source == "chapters"
    assert selection.entries == (TimestampEntry(0, "Chapter A"), TimestampEntry(100, "Chapter B"))


def test_description_is_used_without_chapters() -> None:
    info = make_info(description=DESCRIPTION, comments=(COMMENT_2,))

    selection = select_source(info)

    assert selection.source == "description"
    assert selection.entries == (TimestampEntry(0, "Desc A"), TimestampEntry(120, "Desc B"))


def test_comments_are_used_last() -> None:
    selection = select_source(make_info(description="No timestamps", comments=(COMMENT_2,)))

    assert selection.source == "comment"
    assert selection.entries == (TimestampEntry(0, "One"), TimestampEntry(60, "Two"))


def test_single_chapter_or_timestamp_is_not_a_tracklist() -> None:
    info = make_info(
        chapters=(Chapter(0, "Whole video"),),
        description="Best part at 3:45",
        comments=(COMMENT_2,),
    )

    assert select_source(info).source == "comment"


def test_nothing_usable_raises() -> None:
    info = make_info(description="Hello", comments=(Comment("nice 1:00"),))

    with pytest.raises(ValueError, match="No usable timestamps"):
        select_source(info)


def test_candidates_are_ranked_by_timestamp_count_then_likes() -> None:
    comments = (COMMENT_2, COMMENT_3, COMMENT_3_POPULAR, Comment("only 1:00"))

    ranked = rank_comment_candidates(comments)

    assert [c.comment for c in ranked] == [COMMENT_3_POPULAR, COMMENT_3, COMMENT_2]


def test_manual_choice_picks_another_candidate_and_forces_comments() -> None:
    info = make_info(chapters=CHAPTERS, comments=(COMMENT_3, COMMENT_3_POPULAR, COMMENT_2))

    selection = select_source(info, comment_choice=2)

    assert selection.source == "comment"
    assert selection.chosen == 2
    assert selection.entries == (TimestampEntry(0, "One"), TimestampEntry(60, "Two"))
    assert len(selection.candidates) == 3


@pytest.mark.parametrize("choice", [-1, 1])
def test_manual_choice_out_of_range_raises(choice: int) -> None:
    with pytest.raises(ValueError, match="between 1 and 1"):
        select_source(make_info(comments=(COMMENT_2,)), comment_choice=choice)
