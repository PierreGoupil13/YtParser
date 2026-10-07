from yaml import safe_dump, safe_load
from decimal import Decimal

from ytparser.core.models import Tracklist, Track

def to_yaml(tracks: Tracklist) -> str:
    # On va vouloir écrire ligne par ligne ce dict de dict
    data = tracks.asdict()
    for track in data["tracks"] :
        track["start"] = convertSecToTime(track["start"])
        track["end"] = convertSecToTime(track["end"])
    # hh:mm:ss` ↔ secondes
    # Ecrire le yaml est bon en soit mais il faut gérer la conversion, car on garde tout en secondes
    return(safe_dump(data, allow_unicode=True, sort_keys=False))

def from_yaml(tracks: str) -> Tracklist:
    track_data = safe_load(tracks)
    parsed_tracks = []
    for track in track_data['tracks']:
        track['start'] = convertTimeToSec(track['start'])
        track['end'] = convertTimeToSec(track['end'])
        parsed_track = Track(track['number'], track['start'], track['end'],track['title'],track['artist'])
        parsed_tracks.append(parsed_track)
    return Tracklist(tracks=tuple(parsed_tracks))

def convertSecToTime(time: int) -> str:
    time = Decimal(str(time))
    minutes, secondes = divmod(time, 60);
    heures, minutes = divmod(minutes, 60);

    return f"{splitFraction(heures)}:{splitFraction(minutes)}:{splitFraction(secondes)}"

def splitFraction(number: int | float) -> str:
    text = (str(number))
    whole, separator, fraction = text.partition(".")
    if(separator == "") :
        return whole.zfill(2)
    elif(int(fraction) == 0):
        return whole.zfill(2)
    else:
        return(whole.zfill(2) + separator + fraction)

def convertTimeToSec(time: str) -> float:
    heures, minutes, secondes = time.split(':')
    total = int(heures) * 3600 + int(minutes)* 60 + Decimal(secondes)
    return float(total);


if __name__ == "__main__":
    original = Tracklist(
        tracks=(
            Track(1, 0, 65.123, "Été", "Artiste A"),
            Track(2, 65.123, 3723.486, "Final", "Artiste B"),
        )
    )

    text = to_yaml(original)
    restored = from_yaml(text)

    print(text)
    print(restored)
    assert restored == original
    print("Aller-retour réussi !")