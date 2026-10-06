from yaml import safe_dump, safe_load
from decimal import Decimal

from ytparser.core.models import Tracklist, Track

def write_yaml(tracks: Tracklist) -> str:
    # On va vouloir écrire ligne par ligne ce dict de dict
    data = tracks.asdict()
    for track in data["tracks"] :
        track["start"] = convertSecToTime(track["start"])
        track["end"] = convertSecToTime(track["end"])
    # hh:mm:ss` ↔ secondes
    # Ecrire le yaml est bon en soit mais il faut gérer la conversion, car on garde tout en secondes
    return(safe_dump(data, allow_unicode=True, sort_keys=False))

# Reste a prendre en compte
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

if __name__ == "__main__":
    tracklist = Tracklist(
        tracks=(
            Track(number=1, start=0, end=3, title="Intro", artist="Artiste A"),
            Track(number=2, start=3, end=65, title="Été", artist="Artiste A"),
            Track(number=3, start=65, end=134, title="Final", artist="Artiste B"),
            Track(number=4, start=134.5, end=157, title="Final", artist="Artiste B"),
            Track(number=5, start=157.56, end=3723.486, title="Final", artist="Artiste B"),
        )
    )
    print(write_yaml(tracklist))