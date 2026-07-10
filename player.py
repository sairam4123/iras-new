import json
from pathlib import Path
import io
import traceback
from typing import Any
import pydub
import asyncio

import datetime

# from pydub.effects import speedup
import heapq

from vox import create_announcement_sound, build_cache

from etrainlib import async_default_captcha_resolver
from etrainlib._async import ETrainAPIAsync

from speaker import t2s

from templates import (
    arrival,
    arrival_shortly,
    arrival_on,
    departure,
    departure_ready,
    on_platform,
    no_info,
    arrival_middle,
    arrival_on_middle,
    arrival_shortly_middle,
)

TYPES = {
    "arrival_shortly": 1,
    "arrival_on": 2,
    "on_platform": 3,
    "arrival": 4,
    "departure_ready": 5,
    "departure": 6,
    "arrival_shortly_middle": 8,
    "arrival_on_middle": 9,
    "arrival_middle": 10,
    "no_info": 7,
    # "diverted": 11,
    # "rescheduled": 12,
    # "short_terminated": 13,
    # "cancelled": 14,
}

STATION_FILE = Path("stations.json")
TRAIN_FILE = Path("trains.json")
DATA_FILE = Path("data.json")
LANGUAGES = ["ta", "hi", "en"]
INTROS: list[pydub.AudioSegment] = [
    (pydub.AudioSegment.from_file(path))
    for path in (Path("announcers") / "sounds").iterdir()
]
TPJ_ANN = INTROS[2] + INTROS[2]
INTROS.insert(0, TPJ_ANN)
ANNOUNCEMENTS_PATH = Path("anns/trains")
ANNOUNCEMENTS_PATH.mkdir(exist_ok=True, parents=True)

NSG_DATA_PATH = Path("dataset/station/nsg_data.json")

nsg_data: dict[str, int] = json.loads(NSG_DATA_PATH.read_text())

abbvs = {
    " VANDE BHARAT ": " VANDE BHARAT EXPRESS ",
    " VB EXP ": " VANDE BHARAT EXPRESS ",
    " JS ": " JAN SHATABDI ",
    " SF ": " Superfast ",
    " EX ": " Express ",
    " SPL ": " Special ",
    " LOCAL ": " LOCAL ",
    " EXP ": " Express ",
    " SMPRK KRNTI ": " SAMPRAK KRANTI ",
    " PCET ": " PARCEL CARGO EXPRESS TRAIN ",
    " SEMI ": " SEMI FAST ",
    " FAST ": " FAST local train ",
}

station_abbvs = {
    " JN": "",  # remove it to improve stn name performance
    " CNTL": " CENTRAL",
    " Cantt": " CANTONMENT",
    " Cant": " CANTONMENT",
    " RD": " ROAD",
    " JN.": "",  # temp remove it to improve stn name performance
    " HLT": " HALT",
    " NRTH": " NORTH",
    " STH": " SOUTH",
    # " T": " TERMINUS",
}

local_train_abbvs = {
    " FAST": " FAST local train ",
    " SEMI ": "SEMI FAST ",
}

build_cache()


def parse_arrdep_time(
    train, cur_time: datetime.datetime
) -> tuple[datetime.datetime | None, datetime.datetime | None]:
    arr_time = str(train["exp_arr"])
    source = arr_time.lower().startswith("source")
    if not source:
        arr_time, arr_day = str(train["exp_arr"]).split(", ")
        arr_day = int(arr_day.split(" ")[0])
        if not arr_time:
            arr = None
        else:
            arr = datetime.datetime.strptime(arr_time, "%H:%M").replace(
                cur_time.year, cur_time.month, arr_day, second=cur_time.second
            )
    else:
        arr = None

    dept_time = str(train["exp_dept"])
    dest = dept_time.lower().startswith("dest")

    if not dest:
        dept_time, dept_day = str(train["exp_dept"]).split(", ")
        dept_day = int(dept_day.split(" ")[0])
        if not dept_time:
            dept = None
        else:
            dept = datetime.datetime.strptime(dept_time, "%H:%M").replace(
                cur_time.year, cur_time.month, dept_day, second=cur_time.second
            )
    else:
        dept = None
    return arr, dept


def split_time(time_str: str) -> tuple[str, str]:
    time_str = time_str.strip()
    if not time_str:
        return "", ""
    if ":" not in time_str:
        return time_str, ""
    hr, min_ = time_str.split(":")
    return hr, min_


def choose_msg(train, cur_time: datetime.datetime) -> int | None:
    arr_time, dep_time = parse_arrdep_time(train, cur_time)
    print(arr_time, dep_time, cur_time, "TIME CHECK")
    if arr_time is None and dep_time is None:
        return TYPES["no_info"]
    if arr_time is not None and dep_time is not None and arr_time > dep_time:
        return None  # Invalid data, arrival time cannot be greater than departure time.
    if (
        arr_time is not None
        and dep_time is not None
        and arr_time < cur_time
        and dep_time < cur_time
    ):
        return None  # Invalid data, both arrival and departure times are in the past.
    msg_type = None
    if (
        arr_time is None and dep_time is not None
    ):  # Train is originating from here and going somewhere.
        if dep_time > cur_time and (dep_time - cur_time).total_seconds() < 3 * 60:
            msg_type = TYPES["departure_ready"]
        elif dep_time > cur_time and (dep_time - cur_time).total_seconds() < 60 * 60:
            msg_type = TYPES["departure"]
        print(
            arr_time,
            dep_time,
            cur_time,
            (dep_time - cur_time).total_seconds(),
            "Train originates here.",
        )
    elif (
        arr_time is not None and dep_time is None
    ):  # Coming from somewhere and not originating here.
        if arr_time > cur_time and (arr_time - cur_time).total_seconds() < 3 * 60:
            msg_type = TYPES["arrival_on"]
        elif arr_time > cur_time and (arr_time - cur_time).total_seconds() < 10 * 60:
            msg_type = TYPES["arrival_shortly"]
        elif arr_time > cur_time and (arr_time - cur_time).total_seconds() < 20 * 60:
            msg_type = TYPES["arrival"]
        print(
            arr_time,
            dep_time,
            cur_time,
            (arr_time - cur_time).total_seconds(),
            "Train terminates here.",
        )
    elif (
        arr_time is not None and dep_time is not None
    ):  # Train is coming from somewhere going somewhere, dunno where :)
        if arr_time > cur_time and (arr_time - cur_time).total_seconds() < 2 * 60:
            msg_type = TYPES["arrival_on_middle"]
            print("Generating arriving on message.")
        elif arr_time > cur_time and (arr_time - cur_time).total_seconds() < 10 * 60:
            msg_type = TYPES["arrival_shortly_middle"]
            print("Generating arriving shortly message.")
        elif arr_time > cur_time and (arr_time - cur_time).total_seconds() < 20 * 60:
            msg_type = TYPES["arrival_middle"]
            print("Generating arrival message")

        if dep_time > cur_time and (dep_time - cur_time).total_seconds() < 3 * 60:
            msg_type = TYPES["departure_ready"]
            print("Generating departing ready")

        elif (
            dep_time > cur_time
            and cur_time > arr_time
            and (dep_time - cur_time).total_seconds() < 60 * 60
        ):
            msg_type = TYPES["departure"]
            print("Generating scheduled for departure message.")

        if (
            arr_time < cur_time
            and dep_time > cur_time
            and (dep_time - cur_time).total_seconds() > 2 * 60
        ):
            msg_type = TYPES["on_platform"]

        print(
            arr_time,
            dep_time,
            cur_time,
            (arr_time - cur_time).total_seconds(),
            (dep_time - cur_time).total_seconds(),
        )
    return msg_type


def replace_stn_names(_str: str) -> str:
    str_list = _str.split(" ")
    for index, str_ in enumerate(str_list):
        if str_ in ann_station_map:
            str_list[index] = ann_station_map[str_].lower()
    return " ".join(str_list)


def replace_abbvs(_str: str, abbvs_: dict[str, str] | None = None) -> str:
    abbvs_ = abbvs_ or abbvs
    res = _str
    for abbv in abbvs_:
        res = res.replace(abbv.lower(), abbvs_[abbv].lower())
        res = res.replace(abbv.upper(), abbvs_[abbv].lower())
    return res


station_map = json.loads(STATION_FILE.read_text())
station_map = {std_c: replace_abbvs(sta["name"]) for std_c, sta in station_map.items()}
ann_station_map = {
    std_c: replace_abbvs(sta, station_abbvs) for std_c, sta in station_map.items()
}
print(ann_station_map)

coach_pos_abbv = {
    "PWR": "P W R",
    "GN": "General Compartment",
    "SLRD": "S L R D,",
    "PC": "Pantry Car",
    "GRD": "S L R D,",
}

number_map = {
    "0": {
        "en": "Zero",
        "hi": "शून्य",
        "ta": "பூஜ்ஜியம்",
        "te": "సున్నా",
    },
    "1": {
        "en": "One",
        "hi": "एक",
        "ta": "ஒன்று",
        "te": "ఒకటి",
    },
    "2": {
        "en": "Two",
        "hi": "दो",
        "ta": "இரண்டு",
        "te": "రెండు",
    },
    "3": {
        "en": "Three",
        "hi": "तीन",
        "ta": "மூன்று",
        "te": "మూడు",
    },
    "4": {
        "en": "Four",
        "hi": "चार",
        "ta": "நான்கு",
        "te": "నాలుగు",
    },
    "5": {
        "en": "Five",
        "hi": "पांच",
        "ta": "ஐந்து",
        "te": "ఐదు",
    },
    "6": {
        "en": "Six",
        "hi": "छह",
        "ta": "ஆறு",
        "te": "ఆరు",
    },
    "7": {
        "en": "Seven",
        "hi": "सात",
        "ta": "ஏழு",
        "te": "ఏడు",
    },
    "8": {
        "en": "Eight",
        "hi": "आठ",
        "ta": "எட்டு",
        "te": "ఎనిమిది",
    },
    "9": {
        "en": "Nine",
        "hi": "नौ",
        "ta": "ஒன்பது",
        "te": "తొమ్మిది",
    },
}

coach_pos_ann = """
Your kind attention please! Train number: {train[no]} {train[name]}. Coach position from engine:
{train[coach_pos]}.
"""


def tts(msg, f, lang="en"):
    # yapper = PiperSpeaker(voice=PiperVoiceIN())
    # try:

    # except Exception as e:
    # print("Error using yapper, falling back to gTTS", e)
    # gTTS(text=msg, lang=lang, tld="co.in", slow=False).write_to_fp(f)
    t2s(msg, f, lang=lang)


async def coach_pos_main(
    train_no: str, train_name: str, captcha_resolver=async_default_captcha_resolver
):
    train_correct_number = " ; ".join(train_no[:]) + " ;"

    async with ETrainAPIAsync(captcha_resolver=captcha_resolver) as etrain:
        coach_pos = await etrain.get_coach_positions(train_no, train_name)

    coach_pos_str = ";".join(
        f"{coach_pos_abbv.get(c_name, c_name)}: {coach_p}"
        for coach_p, c_name in coach_pos.items()
    )

    print(coach_pos_str)
    msg = coach_pos_ann.format_map(
        {
            "train": {
                "no": train_correct_number,
                "name": replace_abbvs(train_name).lower(),
                "coach_pos": coach_pos_str,
            }
        }
    )
    print(msg)
    intro = INTROS[0]  # Decrease volume by 3 dB
    with io.BytesIO() as f:
        # gTTS(text=msg, lang="en-IN", tld="co.in", slow=False).write_to_fp(f)
        tts(msg, f, lang="en-IN")

        # f.seek(0, 2)
        # pydub.AudioSegment.silent(1000).export(f, format="mp3")
        f.seek(0)
        silent = pydub.AudioSegment.silent(duration=500)
        announcement = pydub.AudioSegment.from_file(f)
        # announcement = speedup(announcement, playback_speed=1.0)

        ann_file = ANNOUNCEMENTS_PATH / f"{train_name.replace(' ', '_')}_coach.wav"
        (intro + silent + announcement).export(str(ann_file), format="wav")

    return ann_file


ann_types_text = {
    TYPES["arrival"]: arrival,
    TYPES["arrival_shortly"]: arrival_shortly,
    TYPES["arrival_on"]: arrival_on,
    TYPES["departure"]: departure,
    TYPES["departure_ready"]: departure_ready,
    TYPES["on_platform"]: on_platform,
    TYPES["no_info"]: no_info,
    TYPES["arrival_middle"]: arrival_middle,
    TYPES["arrival_on_middle"]: arrival_on_middle,
    TYPES["arrival_shortly_middle"]: arrival_shortly_middle,
}


def match_type(ann_type: int, lang: str) -> list[str]:
    return ann_types_text.get(ann_type, no_info).get(lang, [])


async def create_announcement_for(
    ann_type, train: dict[str, Any], languages=LANGUAGES, delta=500
):
    segments = []
    tasks = []
    for lang in languages:
        try:
            ann_text_hints = match_type(ann_type, lang)
            if not ann_text_hints:
                print(
                    f"No announcement text found for type {ann_type} in language {lang}. Skipping."
                )
                continue
            seg = asyncio.create_task(
                create_announcement_sound(ann_text_hints, train, lang)
            )

            tasks.append(seg)

        except Exception as e:
            print(f"Error generating for language: {lang}", e)
            traceback.print_exc()
            break
        except KeyboardInterrupt:
            print("Interrupted while generating announcement.")
            break

    segments = await asyncio.gather(*tasks)
    final_segment = pydub.AudioSegment.silent(duration=0)
    for segment in segments:
        if not segment:
            print(
                f"Failed to create announcement sound for type {ann_type} in language {lang}. Skipping."
            )
            continue
        final_segment += segment + pydub.AudioSegment.silent(duration=delta)

    # segment: pydub.AudioSegment = (
    #     cast(pydub.AudioSegment, sum(segments))
    #     if segments
    #     else pydub.AudioSegment.silent(duration=0)
    # )

    intro = INTROS[0] + 5  # Increase volume by 9 dB
    final_segment = intro + pydub.AudioSegment.silent(duration=500) + final_segment
    return final_segment  # speedup(final_segment, playback_speed=1.0)


def format_train_name(train_name: str):
    src, *dest, name = train_name.strip().split(" ")
    mid = dest
    if "-" in src:
        src, dest = src.split("-")  # handles SRC-DEST
    elif len(dest) == 0:
        dest = ""
    elif len(dest) == 1 and len(mid) == 1:
        dest = dest[0]
        mid = mid[0]

    elif len(dest) >= 2 and len(mid) >= 2:
        dest = " ".join(dest)
        mid = " ".join(mid)
    if mid == dest:
        return replace_stn_names(replace_abbvs(f"{src} {dest} {name} ")).strip()
    return replace_stn_names(
        replace_abbvs(f"{src} {dest} {' '.join(mid)} {name} ")
    ).strip()


def choose_priority_time(
    train: dict, cur_time: datetime.datetime
) -> datetime.datetime | None:
    arr_time, dep_time = parse_arrdep_time(train, cur_time)

    # if train hasn't arrived yet, prioritize arrival time
    if arr_time and arr_time > cur_time:
        return arr_time
    # else, if train has arrived but hasn't departed yet, prioritize departure time
    if dep_time and dep_time > cur_time:
        return dep_time

    # else, return current time (train has already departed, or terminated here)
    return cur_time


async def main(
    station_name: str,
    stn_code: str,
    time: datetime.datetime | None = None,
    captcha_resolver=None,
):
    global station_map

    time = time or datetime.datetime.now()
    async with ETrainAPIAsync(
        captcha_resolver=captcha_resolver or async_default_captcha_resolver
    ) as etrain:
        trains = await etrain.get_live_station(stn_code, station_name)
        for train in trains:
            if not train["tt_pf"] or train["tt_pf"].startswith("-"):
                print(
                    "Ignoring train with no platform number:",
                    train["train_no"],
                    train["train_name"],
                    train["tt_pf"],
                )
                continue

            ann_type = choose_msg(train, cur_time=time)
            arr_time, dep_time = parse_arrdep_time(train, time)
            if not ann_type:
                continue

            train_info = build_train_metadata(train, arr_time, dep_time)

            print("Getting train schedule...")
            schedule: list = await etrain.get_train_schedule(
                train["train_no"], train["train_name"].replace(" ", "-")
            )
            if schedule:
                print("Updating station map...")
                update_station_map_with(schedule)

                via_stns = build_via_stations(schedule, stn_code)
                print("Via stations codes:", via_stns)
                via_stns = [
                    replace_abbvs(station_map.get(code, code), station_abbvs)
                    .strip()
                    .lower()
                    for code in via_stns
                ]
                print("Via stations:", via_stns)
                train_info["train"]["via"] = via_stns

            print("Generating announcement...")
            msg = match_type(ann_type, "en")  # for debugging

            print(msg)

            announcement = await create_announcement_for(
                ann_type, train_info["train"], languages=LANGUAGES
            )
            ann_file = (
                ANNOUNCEMENTS_PATH
                / f"{train['train_no']}_{train['train_name'].replace(' ', '_')}.mp3"
            )
            (announcement + 3).export(str(ann_file), format="mp3")
            # if dep_time is not available, then send the arrival time
            # prioritize arrivals otherwise departures

            priority_time = choose_priority_time(train, time)
            yield [ann_file, priority_time, ann_type, train_info]


def build_train_metadata(train, arr_time, dep_time):
    train_info = {
        "train": (
            {
                "no": train["train_no"],
                "name": format_train_name(train["train_name"] + " "),
                "src": replace_abbvs(replace_stn_names(train["src"] + " ")).strip(),
                "dest": replace_abbvs(replace_stn_names(train["dest"] + " ")).strip(),
                "pf": train["tt_pf"],
            }
            | (
                {
                    "arr_hr": arr_time.strftime("%H"),
                    "arr_min": arr_time.strftime("%M"),
                }
                if arr_time
                else {}
            )
            | (
                {
                    "dept_hr": dep_time.strftime("%H"),
                    "dept_min": dep_time.strftime("%M"),
                }
                if dep_time
                else {}
            )
        )
    }

    return train_info


def update_station_map_with(schedule):
    global station_map
    station_map = json.loads(STATION_FILE.read_text())
    station_map.update(
        {sta["code"]: {"code": sta["code"], "name": sta["name"]} for sta in schedule}
    )
    STATION_FILE.write_text(json.dumps(station_map))
    station_map = json.loads(STATION_FILE.read_text())
    station_map = {
        std_c: replace_abbvs(sta["name"]) for std_c, sta in station_map.items()
    }


def build_via_stations(schedule: list, curr: str, n_via=5) -> list[str]:
    schedule_codes = [sta["code"] for sta in schedule]
    schedule_distances = {sta["code"]: sta.get("dist", 0) for sta in schedule}

    curr_idx = schedule_codes.index(curr)

    forward_heap = schedule_codes[curr_idx + 1 : -1]
    forward = heapq.nsmallest(
        n_via,
        forward_heap,
        key=lambda c: (nsg_data.get(c, 99999), schedule_distances.get(c, 0)),
    )

    print(
        "Forward via before sort:",
        forward_heap,
        [nsg_data.get(c, 99999) for c in forward_heap],
    )

    forward.sort(key=lambda c: int(schedule_distances.get(c, 0)))

    return forward


# def welcome_f(stn_name: str):
#     g_msg = goodbye.format_map(
#         {
#             "station": {
#                 "name": stn_name,
#             }
#         }
#     )
#     msg = welcome.format_map(
#         {
#             "station": {
#                 "name": stn_name,
#             }
#         }
#     )
#     print(msg)
#     intro = INTROS[0]  # Decrease volume by 3 dB

#     silent = pydub.AudioSegment.silent(duration=500)
#     announcement = create_announcement_for(msg)
#     w_ann = intro + silent + announcement
#     announcement = create_announcement_for(g_msg)
#     g_ann = intro + silent + announcement

#     silent = pydub.AudioSegment.silent(duration=2000)
#     ann_file = ANNOUNCEMENTS_PATH / f"{stn_name.replace(' ', '_')}.mp3"
#     (w_ann + silent + g_ann).export(str(ann_file))


# if __name__ == "__main__":
#     # coach_pos_main("12605", "PALLAVAN EXP")
#     # print(asyncio.run(main("Tiruchirapalli Junction", "TPJ")))
#     while True:
#         name = input("Train name:> ")
#         print(format_train_name(name))
#         number = input("Train number:> ")
#         if not number or not name:
#             break

#         coach_pos_main(number, name)
