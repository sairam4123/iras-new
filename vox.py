import hashlib
from typing import Any, cast
from pydub.silence import detect_leading_silence

import pydub

import pathlib

import re

try:
    from .speaker import t2s
except ImportError:
    from speaker import t2s

ANN_HINT_REGEX = re.compile(r"\{cache\[(\w+)\]\}")
TRAIN_HINT_REGEX = re.compile(r"\{train\[(\w+)\]\}")

CACHE_FOLDER = pathlib.Path("anns/cache")

CACHE_FOLDER.mkdir(parents=True, exist_ok=True)
LANGS = ["en", "hi", "ta"]
CACHE_FPS = {lang: CACHE_FOLDER / lang for lang in LANGS}

for lang, cache_fp in CACHE_FPS.items():
    cache_fp.mkdir(parents=True, exist_ok=True)

CACHE: dict[str, dict[str, pydub.AudioSegment]] = {lang: {} for lang in LANGS}

texts = {
    "en": {
        "attention": "Your kind attention please!",
        "train_number": "Train number",
        "coming_from": "coming from",
        "coming_from_train": "coming from",
        "bound_for": "bound for",
        "train": "train",
        "via": "via",
        "platform_label": "platform number",
        "arriving_shortly": "will arrive shortly on",
        "expected_departure": "is scheduled to depart from",
        "ready_departure": "is ready for departure from",
        "arriving_on": "is arriving on",
        "expected_arrival": "is expected to arrive on",
        "standing_on": "is on",
        "time_at": "at",
        "hour_marker": "hours",
        "minute_marker": "minutes",
        "deep_regret": "We deeply regret the inconvinence caused.",
        "pls_contact_authorities": "Please contact the authorities.",
        "no_information": "has no information available at this time.",
    },
    "ta": {
        "attention": "பயணிகளின் கனிவான கவனத்திற்கு!",
        "train_number": "வண்டி எண்",
        "coming_from": "இலிருந்து",
        "coming_from_train": "இலிருந்து வரும் இரயில்",
        "bound_for": "வரை செல்லும்",
        "via": "வழியாக",
        "train": "இரயில்",
        "ordinal_suffix": "-ஆவது",
        "platform_on": "பிளாட்பாரத்தில்",
        "platform_to": "பிளாட்பாரத்திற்கு",
        "platform_from": "பிளாட்பாரத்திலிருந்து",
        "hour_marker": "மணி",
        "minute_marker": "நிமிடத்திற்கு",
        "arriving_shortly": "இன்னும் சிறிது நேரத்தில் வந்து சேரும்.", # replace these with "-il innum"
        "expected_departure": "புறப்படும்.", # replace these with "-ilirundhu"
        "ready_departure": "புறப்பட தயாராக உள்ளது.",
        "arriving_on": "வந்து கொண்டிருக்கிறது.",
        "expected_arrival": "வந்து சேரும் என எதிர்பார்க்கப்படுகிறது.",
        "standing_on": "உள்ளது.",
        "deep_regret": "உங்களக்கு ஏற்பட்ட சிரமத்திற்கு நாங்கள் வருந்துகிறோம்.",
        "pls_contact_authorities": "தயவுசெய்து அதிகாரிகளுடன் தொடர்பு கொள்ளவும்.",
        "no_information": "பற்றிய தகவல்கள் இந்த நேரத்தில் கிடைக்கவில்லை.",
    },
    "hi": {
        "attention": "यात्रिगण कृपया ध्यान दें!",
        "train_number": "गाड़ी संख्या",
        "coming_from": "से आने वाली",
        "coming_from_train": "से आने वाली गाड़ी",
        "bound_for": "तक जाने वाली",
        "via": "से होकर",
        "train": "गाड़ी",
        "platform_label": "प्लेटफॉर्म नंबर",
        "hour_marker": "बजकर",
        "minute_marker": "मिनट पर",
        "arriving_shortly": "पर थोड़ी देर में आएगी।",
        "expected_departure": "से रवाना होगी।",
        "ready_departure": "से रवाना होने के लिए तैयार है।",
        "arriving_on": "पर आ रही है।",
        "expected_arrival": "पर आने की संभावना है।",
        "standing_on": "पर खड़ी है।",
        "deep_regret": "आपको हुई असुविधा के लिए हमें खेद है।",
        "pls_contact_authorities": "कृपया अधिकारियों से संपर्क करें।",
        "no_information": "पर तकनीकी खराबी के कारण इस समय कोई जानकारी उपलब्ध नहीं है।",
    },
}

lang_map = {
    "en": "en-IN",
    "hi": "hi-IN",
    "ta": "ta-IN",
}

number_map = {
    "zero": {
        "en": "Zero",
        "hi": "शून्य",
        "ta": "பூஜ்ஜியம்",
        "te": "సున్నా",
    },
    "one": {
        "en": "One",
        "hi": "एक",
        "ta": "ஒன்று",
        "te": "ఒకటి",
    },
    "two": {
        "en": "Two",
        "hi": "दो",
        "ta": "இரண்டு",
        "te": "రెండు",
    },
    "three": {
        "en": "Three",
        "hi": "तीन",
        "ta": "மூன்று",
        "te": "మూడు",
    },
    "four": {
        "en": "Four",
        "hi": "चार",
        "ta": "நான்கு",
        "te": "నాలుగు",
    },
    "five": {
        "en": "Five",
        "hi": "पांच",
        "ta": "ஐந்து",
        "te": "ఐదు",
    },
    "six": {
        "en": "Six",
        "hi": "छह",
        "ta": "ஆறு",
        "te": "ఆరు",
    },
    "seven": {
        "en": "Seven",
        "hi": "सात",
        "ta": "ஏழு",
        "te": "ఏడు",
    },
    "eight": {
        "en": "Eight",
        "hi": "आठ",
        "ta": "எட்டு",
        "te": "ఎనిమిది",
    },
    "nine": {
        "en": "Nine",
        "hi": "नौ",
        "ta": "ஒன்பது",
        "te": "తొమ్మిది",
    },
}

num_map_digits = {
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}


def load_cached_ann(lang: str):
    cache_fp = CACHE_FPS.get(lang)
    if not cache_fp:
        raise ValueError(f"Invalid language: {lang}")
    for ann_fp in cache_fp.glob("*.mp3"):
        key = ann_fp.stem
        CACHE[lang][key] = pydub.AudioSegment.from_file(ann_fp, format="mp3")


def generate_audio_for_hint(ann_hint: str, key: str, lang: str) -> pydub.AudioSegment:
    with open(CACHE_FPS[lang] / f"{key}.mp3", "w+b") as f:
        t2s(ann_hint, f, lang=lang_map.get(lang, "en-IN"))
        f.seek(0)
        segment = pydub.AudioSegment.from_file(f, format="mp3")
        dead_silence_duration = detect_leading_silence(segment)
        if dead_silence_duration > 0:
            print(
                f"Trimming {dead_silence_duration}ms of leading silence from cached audio for key: {key} in cache: {lang}"
            )
            segment = segment[dead_silence_duration:]
        death_silence_duration = detect_leading_silence(segment.reverse())
        if death_silence_duration > 0:
            print(
                f"Trimming {death_silence_duration}ms of trailing silence from cached audio for key: {key} in cache: {lang}"
            )
            segment = segment[:-death_silence_duration]
        segment.export(CACHE_FPS[lang] / f"{key}.mp3", format="mp3")
        return segment


async def stitch_announcement(
    ann_hints: list[str], lang: str
) -> pydub.AudioSegment | None:
    announcement: pydub.AudioSegment = pydub.AudioSegment.empty()
    for ann_hint in ann_hints:
        segment = pydub.AudioSegment.empty()
        if ann_hint.startswith("{cache"):
            match = ANN_HINT_REGEX.match(ann_hint)
            if not match:
                raise ValueError(f"Invalid announcement hint: {ann_hint}")
            key, *_ = match.groups()
            cache_name = lang
            if cache_name not in CACHE:
                raise ValueError(f"Invalid cache name: {cache_name}")
            if key not in CACHE[cache_name]:
                # generate the audio and cache it
                print(f"Generating audio for {key}...")
                text = texts[cache_name].get(key)
                if not text:
                    text = number_map.get(key, {}).get(cache_name)
                    print(
                        f"Fetched text from number_map: {text} for key: {key}, cache_name: {cache_name}"
                    )
                if not text:
                    raise ValueError(f"Invalid key: {key} for cache: {cache_name}")
                segment = generate_audio_for_hint(text, key, cache_name)
                CACHE[cache_name][key] = segment

            else:
                print(f"Fetching cached audio for {key}, in {cache_name}...")
                segment = CACHE[cache_name][key]
        else:
            # cache the audio through sha512 hash of the text
            print(f"Finding cached audio for {ann_hint}...")
            key = hashlib.sha512(ann_hint.encode()).hexdigest()[:10]

            if key not in CACHE[lang]:
                print(f"Generating audio for {ann_hint} with key: {key}...")
                segment = generate_audio_for_hint(ann_hint, key, lang)
                CACHE[lang][key] = segment
            else:
                print(f"Fetching cached audio for {ann_hint} with key: {key}...")
                segment = CACHE[lang][key]
        announcement += segment + pydub.AudioSegment.silent(
            duration=50
        )  # add 50ms of silence between segments

    # stitch the announcement together
    # for ann_hint in ann_hints:
    #     if ann_hint.startswith("{cache"):
    #         match = ANN_HINT_REGEX.match(ann_hint)
    #         if not match:
    #             raise ValueError(f"Invalid announcement hint: {ann_hint}")
    #         key, *_ = match.groups()
    #         cache_name = lang
    #         cached_audio: pydub.AudioSegment | None = CACHE[cache_name].get(key)
    #         if not cached_audio:
    #             raise ValueError(
    #                 f"Cached audio not found for key: {key} in cache: {cache_name}"
    #             )

    #         announcement += cached_audio + pydub.AudioSegment.silent(
    #             duration=50
    #         )  # add 100ms of silence between segments
    #     else:
    #         key = hashlib.sha512(ann_hint.encode()).hexdigest()[:10]
    #         cached_audio: pydub.AudioSegment | None = CACHE[lang].get(key)
    #         if not cached_audio:
    #             raise ValueError(
    #                 f"Cached audio not found for key: {key} in cache: {cache_name}"
    #             )
    #         dead_silence_duration = detect_leading_silence(cached_audio)
    #         if dead_silence_duration > 0:
    #             print(
    #                 f"Trimming {dead_silence_duration}ms of leading silence from cached audio for key: {key} in cache: {cache_name}"
    #             )
    #             cached_audio: pydub.AudioSegment = cached_audio[dead_silence_duration:]
    #         death_silence_duration = detect_leading_silence(cached_audio.reverse())
    #         if death_silence_duration > 0:
    #             print(
    #                 f"Trimming {death_silence_duration}ms of trailing silence from cached audio for key: {key} in cache: {cache_name}"
    #             )
    #             cached_audio: pydub.AudioSegment = cached_audio[
    #                 :-death_silence_duration
    #             ]

    #         announcement += cached_audio + pydub.AudioSegment.silent(
    #             duration=50
    #         )  # add 100ms of silence between segments
    pathlib.Path("anns/final").mkdir(parents=True, exist_ok=True)
    announcement.export(
        pathlib.Path("anns/final")
        / f"{hashlib.sha512(str(ann_hints).encode()).hexdigest()[:10]}_{lang}.mp3",
        format="mp3",
    )
    return announcement


def fill_train_details(ann_hints: list[str], train: dict[str, Any]) -> list[str]:
    final_hints = []
    for ann_hint in ann_hints:
        if ann_hint.startswith("{train"):
            match = TRAIN_HINT_REGEX.match(ann_hint)
            if not match:
                raise ValueError(f"Invalid train hint: {ann_hint}")
            key, *_ = match.groups()
            if key not in train:
                raise ValueError(f"Invalid key: {key} for train details")
            if key == "no":  # handle this special case
                final_hints.extend(
                    [
                        f"{{cache[{num_map_digits.get(str(train_single_digit), str(train_single_digit))}]}}"
                        for train_single_digit in train["no"]
                    ]
                )
            elif key == "via":  # handle this special case
                final_hints.extend([via_station for via_station in train["via"]])
            elif key == "name":  # handle this special case
                final_hints.append(
                    train["name"].lower()
                )  # convert to lowercase for better TTS pronunciation
            else:
                final_hints.append(str(train[key]))
        else:
            final_hints.append(ann_hint)
    return final_hints


async def create_announcement_sound(
    ann_hints: list[str], train: dict[str, Any], lang: str
) -> pydub.AudioSegment | None:
    ann_hints = fill_train_details(ann_hints, train)
    load_cached_ann(lang)
    announcement = await stitch_announcement(ann_hints, lang)
    return announcement


# async def main():
#     train = {
#         "no": "12601",
#         "src": "Chennai Egmore",
#         "via": [
#             "Chengalpattu Junction",
#             "Villupuram Junction",
#             "Virudhachalam Junction",
#         ],
#         "dest": "Tiruchirappalli Junction",
#         "pf": "11",
#         "name": "Pallavan Express",
#         "arr_hr": "10",
#         "arr_min": "40",
#         "dep_hr": "10",
#         "dep_min": "45",
#     }

#     ann = {
#         "en": [
#             "{cache[attention]}",
#             "{cache[train_number]}",
#             "{train[no]}",
#             "{train[name]}",
#             "{cache[bound_for]}",
#             "{train[dest]}",
#             "{cache[coming_from]}",
#             "{train[src]}",
#             "{cache[via]}",
#             "{train[via]}",
#             "{cache[expected_arrival]}",
#             "{cache[platform_label]}",
#             "{train[pf]}",
#             "{cache[time_at]}",
#             "{train[arr_hr]}",
#             "{cache[hour_marker]}",
#             "{train[arr_min]}",
#             "{cache[minute_marker]}",
#         ],
#         "ta": [
#             "{cache[attention]}",
#             "{cache[train_number]}",
#             "{train[no]}",
#             "{train[name]}",
#             "{train[src]}",
#             "{cache[coming_from]}",
#             "{train[via]}",
#             "{cache[via]}",
#             "{train[dest]}",
#             "{cache[bound_for]}",
#             "{cache[train]}",
#             "{train[arr_hr]}",
#             "{cache[hour_marker]}",
#             "{train[arr_min]}",
#             "{cache[minute_marker]}",
#             "{train[pf]}",
#             "{cache[ordinal_suffix]}",
#             "{cache[platform_to]}",
#             "{cache[expected_arrival]}",
#         ],
#         "hi": [
#             "{cache[attention]}",
#             "{cache[train_number]}",
#             "{train[no]}",
#             "{train[name]}",
#             "{train[src]}",
#             "{cache[coming_from]}",
#             "{train[via]}",
#             "{cache[via]}",
#             "{train[dest]}",
#             "{cache[bound_for]}",
#             "{cache[train]}",
#             "{train[arr_hr]}",
#             "{cache[hour_marker]}",
#             "{train[arr_min]}",
#             "{cache[minute_marker]}",
#             "{cache[platform_label]}",
#             "{train[pf]}",
#             "{cache[expected_arrival]}",
#         ],
#     }

#     ann_hints = ann["en"]
#     ann_hints = fill_train_details(ann_hints, train)
#     load_cached_ann("en")
#     await stitch_announcement(ann_hints, "en")


# if __name__ == "__main__":
# import asyncio

# asyncio.run(main())
# asyncio.run(
#     stitch_announcement(
#         [
#             "{cache[attn_seeker]}",
#             "{cache[train_num]}",
#             "{cache[one]}",
#             "{cache[two]}",
#             "{cache[three]}",
#             "{cache[five]}",
#             "{cache[one]}",
#             "Pallavan Express",
#             "Chennai Egmore",
#             "{cache[coming_from]}",
#             "Chengalpattu Junction",
#             "Villupuram Junction",
#             "Virudhachalam Junction",
#             "Tiruchirappalli Junction",
#             "{cache[via]}",
#             "Karaikudi Junction",
#             "{cache[bound_for]}",
#             "{cache[platform_number]}",
#             "{cache[two]}",
#             "11",
#             "{cache[hour_marker]}",
#             "0",
#             "{cache[minute_marker]}",
#             "{cache[expected_arrival]}",
#         ],
#         "ta",
#     )
# )
