"""Library adapter: cut, tag, then file tracks as Artist/Album/NN - Title.ext."""

import shutil
import tempfile
from pathlib import Path

from ytparser.adapters.ffmpegadapter import cut_tracklist
from ytparser.adapters.tagadapter import write_tags
from ytparser.core.models import Tracklist
from ytparser.core.naming import library_path, tags_for
from ytparser.core.profiles import DEFAULT_PROFILE, OutputProfile


def export_library(
    source: Path,
    tracklist: Tracklist,
    album: str,
    output_dir: Path,
    profile: OutputProfile = DEFAULT_PROFILE,
) -> list[Path]:
    """Cut with the output profile, tag each file, then move it into the library layout.

    Tagging happens before moving, and nothing reaches output_dir if cutting or tagging
    fails. Existing files are never overwritten.
    """
    with tempfile.TemporaryDirectory(prefix="ytparser-") as temp:
        cut_files = cut_tracklist(source, tracklist, Path(temp), profile)
        plan = []
        for track, cut_file in zip(tracklist.tracks, cut_files, strict=True):
            tags = tags_for(track, tracklist, album)
            write_tags(cut_file, tags, profile)
            plan.append((cut_file, output_dir / library_path(tags, profile.extension)))

        targets = [target for _, target in plan]
        if len(set(targets)) != len(targets):
            raise ValueError("Two tracks would get the same file name.")
        existing = [target for target in targets if target.exists()]
        if existing:
            raise FileExistsError(
                f"{existing[0]} already exists ({len(existing)} conflicting file(s)). "
                "Choose another output folder or remove these files."
            )
        for cut_file, target in plan:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(cut_file, target)
    return targets
