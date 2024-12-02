# https://stackoverflow.com/a/44552191/11697614
from dataclasses import dataclass
import datetime
from pathlib import Path
import re
import urllib



def build_url(base_url, path, query_dict={}):
    # Returns a list in the structure of urlparse.ParseResult
    url_parts = list(urllib.parse.urlparse(base_url))
    url_parts[2] = path
    url_parts[4] = urllib.parse.urlencode(query_dict)
    return urllib.parse.urlunparse(url_parts)


def build_formdata(form_data={}):
    return {key: (None, value) for key, value in form_data.items()}


BASE_API = "https://etrain.info/"
API_VERSION = "3.4.11"
BASE_URL = "https://etrain.info"

CACHE_FOLDER = Path(".etrain-cache")
CACHE_FOLDER.mkdir(exist_ok=True)

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Host": "etrain.info",
    "Origin": "https://etrain.info",
}


@dataclass
class ETrainArrivalDepartureConfig:
    exclude_memu: bool = True
    exclude_local: bool = True
    exclude_fast_emu: bool = True
    exclude_parcel_services: bool = True
    limit: int = 7

@dataclass
class ETrainAllTrainsConfig:
    limit: int = 7
    weekday: int = datetime.datetime.now().weekday()

def decode_hash(encoded_hash, key):
    result_str = ""
    digits = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._"

    # Remove whitespaces
    encoded_hash = encoded_hash.replace(" ", "")

    # Check if enconded hash is valid
    if (
        not re.match(r"^[a-zA-Z0-9\._\s]+\={0,2}$", encoded_hash, re.IGNORECASE)
        or len(encoded_hash) % 4 > 0
    ):
        return "Invalid"

    # Remove tilde characters
    encoded_hash = encoded_hash.replace("~", "")

    result = []
    i = 0
    prev = 0

    while i < len(encoded_hash):
        cur = digits.index(encoded_hash[i])
        digitNum = i % 4

        if digitNum == 1:
            result.append(chr((prev << 2) | (cur >> 4)))
        elif digitNum == 2:
            result.append(chr(((prev & 0x0F) << 4) | (cur >> 2)))
        elif digitNum == 3:
            result.append(chr(((prev & 3) << 6) | cur))

        prev = cur
        i += 1

    encoded_hash = "".join(result)

    key = str(key)
    for i in range(len(encoded_hash)):
        char = encoded_hash[i]
        key_char = key[(i % len(key)) - 1]
        char = chr(ord(char) - ord(key_char))
        result_str += char

    return result_str


AUTH_CACHE = Path(CACHE_FOLDER / "auth.cache")


class ETrainAPIError(Exception):
    pass
