from yaml import safe_dump, safe_load
from decimal import Decimal, InvalidOperation

from ytparser.core.models import Tracklist, Track


def to_yaml(tracks: Tracklist) -> str:
    data = tracks.asdict()
    for track in data["tracks"]:
        track["start"] = convertSecToTime(track["start"])
        track["end"] = convertSecToTime(track["end"])
    return safe_dump(data, allow_unicode=True, sort_keys=False)


def from_yaml(tracks: str) -> Tracklist:
    track_data = safe_load(tracks)
    if(not isinstance(track_data, dict) ) :
        raise ValueError("Document format is invalid")
    
    if not isinstance(track_data.get("tracks"), list):
        raise ValueError("tracks is required and must be a list.")
    
    parsed_tracks = []
    for track in track_data["tracks"]:
        if not isinstance(track,dict):
            raise ValueError("Each track must be a mapping.")

        try:
            number = track["number"]
            start = track["start"]
            end = track["end"]
            title = track["title"]
            artist = track["artist"]
        except KeyError as error:
            field = error.args[0]
            raise ValueError(f"Missing track field: {field}") from error

        for field, value in (("start", start), ("end", end)):
            if not isinstance(value, str):
                raise ValueError(f"Track {field} must be a string.")

        parsed_track = Track(
            number=number,
            start=convertTimeToSec(start),
            end=convertTimeToSec(end),
            title=title,
            artist=artist,
        )
        parsed_tracks.append(parsed_track)

    return Tracklist(tracks=tuple(parsed_tracks))


def convertSecToTime(time: int) -> str:
    time = Decimal(str(time))
    minutes, secondes = divmod(time, 60)
    heures, minutes = divmod(minutes, 60)
    return f"{splitFraction(heures)}:{splitFraction(minutes)}:{splitFraction(secondes)}"


def splitFraction(number: Decimal) -> str:
    text = str(number)
    whole, separator, fraction = text.partition(".")
    if separator == "":
        return whole.zfill(2)
    elif int(fraction) == 0:
        return whole.zfill(2)
    else:
        return whole.zfill(2) + separator + fraction


def convertTimeToSec(time: str) -> float:
    heures, minutes, secondes = time.split(":")

    if any(value == "" for value in [heures, minutes, secondes]):
        raise ValueError("Time components must not be empty.")

    heures = int(heures)
    minutes = int(minutes)
    try:
        secondes = Decimal(secondes)
    except InvalidOperation as error:
        raise ValueError("Seconds must be numeric.") from error

    if minutes >= 60:
        raise ValueError("Minutes must be strictly less than 60")

    if not secondes.is_finite() or secondes >= 60:
        raise ValueError("Seconds must be finite and strictly less than 60")

    if any(value < 0 for value in [heures, minutes, secondes]):
        raise ValueError("Time components can not be of negative values.")
    total = heures * 3600 + minutes * 60 + secondes

    return float(total)
