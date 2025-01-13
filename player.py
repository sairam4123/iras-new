import json
from pathlib import Path
import io
from gtts import gTTS
from py_trans import PyTranslator
import pydub
from pydub.effects import speedup
import datetime
import asyncio

from etrainlib import async_default_captcha_resolver, default_captcha_handler
from etrainlib._async import ETrainAPIAsync
from etrainlib._sync import ETrainAPISync


STATION_FILE = Path("stations.json")
TRAIN_FILE = Path("trains.json")
DATA_FILE = Path("data.json")
LANGUAGES = ["ta", "hi", "en"]
INTROS: list[pydub.AudioSegment] = [(pydub.AudioSegment.from_file(path) ) for path in (Path("announcers") / "sounds").iterdir()] 
TPJ_ANN = INTROS[2] + INTROS[2]
INTROS.insert(0, TPJ_ANN)
ANNOUNCEMENTS_PATH = Path("announcements")
ANNOUNCEMENTS_PATH.mkdir(exist_ok=True)

abbvs = {
    " VB EXP ": " VANDE BHARAT EXPRESS ",
    " SEMI FAST ": " SEMI FAST local train ",
    " FAST ": " FAST local train ",
    " SMPRK KRNTI ": "SAMPRAK KRANTI",
    " EXP ": " Express ",
    " EX ": " Express ",
    " SF ": " Superfast ",
    " SPL ": " Special ",
    " LOCAL ": " LOCAL ",
    " J ": " JUNCTION ",
    " JN ": " JUNCTION ",
    " CNTL ": " CENTRAL ",
    "Cant": "CANTONMENT",
}

arrival_shortly = {
    "ta": """
Passengers attention please, Train number: {train[no]} {train[name]} coming from {train[src]} will arrive shortly on platform number {train[pf]}.
""",
    "en": """
Your kind attention please! Train number: {train[no]} {train[name]} coming from {train[src]} will arrive shortly on platform number {train[pf]}.
""",
    "hi": """
Your kind attention please! Train number: {train[no]} {train[name]} coming from {train[src]} will come shortly on platform number {train[pf]}.
"""
}

arrival_shortly_middle = {
    "ta": """
Passengers attention please, Train number: {train[no]} {train[name]} bound for {train[dest]} coming from {train[src]} will arrive shortly on platform number {train[pf]}.
""",
    "en": """
Your kind attention please! Train number: {train[no]} {train[name]} bound for {train[dest]} coming from {train[src]} will arrive shortly on platform number {train[pf]}.
""",
    "hi": """
Your kind attention please! Train number: {train[no]} {train[name]} bound for {train[dest]} coming from {train[src]} will come shortly on platform number {train[pf]}.
"""
}

arrival_on = {
    "en": """
Your kind attention please! Train number: {train[no]} {train[name]} coming from {train[src]} is arriving on platform number {train[pf]}.
""",
    "hi": """
Your kind attention please! Train number: {train[no]} {train[name]} coming from {train[src]} is coming on platform number {train[pf]}.
""",
    "ta": """
Passengers attention please, Train number: {train[no]} {train[name]} coming from {train[src]} is arriving on platform number {train[pf]}.
"""
}

arrival_on_middle = {
    "en": """
Your kind attention please! Train number: {train[no]} {train[name]} bound for {train[dest]} coming from {train[src]} is arriving on platform number {train[pf]}.
""",
    "hi": """
Your kind attention please! Train number: {train[no]} {train[name]} bound for {train[dest]} coming from {train[src]} is coming on platform number {train[pf]}.
""",
    "ta": """
Passengers attention please, Train number: {train[no]} {train[name]} bound for {train[dest]} coming from {train[src]} is arriving on platform number {train[pf]}.
"""
}

arrival = {
    "en": """
Your kind attention please! Train number: {train[no]} {train[name]} coming from {train[src]} is expected to arrive at {train[arr_time]} on platform number {train[pf]}.
""",
    "hi": """
Your kind attention please! Train number: {train[no]} {train[name]} coming from {train[src]}, there is a possiblity to come at {train[arr_time]} on platform number {train[pf]}.
""",
    "ta": """
Passengers attention please, Train number: {train[no]} {train[name]} coming from {train[src]} is expected to arrive at {train[arr_time]} on platform number {train[pf]}.
"""
}

arrival_middle = {
    "en": """
Your kind attention please! Train number: {train[no]} {train[name]} bound for {train[dest]} coming from {train[src]} is expected to arrive at {train[arr_time]} on platform number {train[pf]}.
""",
    "hi": """
Your kind attention please! Train number: {train[no]} {train[name]} bound for {train[dest]} coming from {train[src]} there is a possiblity to come at {train[arr_time]} on platform number {train[pf]}.
""",
    "ta": """
Passengers attention please, Train number: {train[no]} {train[name]} bound for {train[dest]} coming from {train[src]} is expected to arrive at {train[arr_time]} on platform number {train[pf]}.
"""
}

departure = {
    "en": """
Your kind attention please! Train number: {train[no]} {train[name]} bound for {train[dest]} from {train[src]} is scheduled to depart from platform number {train[pf]} at {train[dept_time]}.
""",
    "hi": """
Your kind attention please! Train number: {train[no]} {train[name]} bound for {train[dest]} from {train[src]} is scheduled to leave from platform number {train[pf]} at {train[dept_time]}.
""",
    "ta": """
    Passengers attention please, Train number: {train[no]} {train[name]} bound for {train[dest]} from {train[src]} is scheduled to depart from platform number {train[pf]} at {train[dept_time]}.
"""
}

departure_ready = {
    "en": """
Your kind attention please! Train number: {train[no]} {train[name]} bound for {train[dest]} from {train[src]} is ready for departure from platform number {train[pf]} at {train[dept_time]}.
""",
    "hi": """
Your kind attention please! Train number: {train[no]} {train[name]} bound for {train[dest]} from {train[src]} is ready to leave from platform number {train[pf]} at {train[dept_time]}.
""",
    "ta": """
Passengers attention please, Train number: {train[no]} {train[name]} bound for {train[dest]} from {train[src]} is ready to depart from platform number {train[pf]} at {train[dept_time]}.
"""

}
on_platform = {
    "en": """
Your kind attention please! Train number: {train[no]} {train[name]} bound for {train[dest]} from {train[src]} is on platform number {train[pf]}.
""",
    "hi": """
Your kind attention please! Train number: {train[no]} {train[name]} bound for {train[dest]} from {train[src]} is on platform number {train[pf]}.
""",
    "ta": """
Passengers attention please, Train number: {train[no]} {train[name]} bound for {train[dest]} from {train[src]} is on platform number {train[pf]}.
"""
}

welcome = """
{station[name]} welcomes you!
"""

goodbye = """
{station[name]} wishes you a happy journey!
"""

diverted = """
Your kind attention please! Train number: {train[no]} {train[name]} bound or {train[dest]} from {train[src]} has been diverted to travel via {train[diversion]}. We deeply regret the inconvinence caused to you.
"""

rescheduled = """
Your kind attention please! Train number: {train[no]} {train[name]} bound for {train[dest]} from {train[src]} scheduled to depart at {train[tt_dept]} has been rescheduled. The new departure time is {train[dept_time]}. We deeply regret the inconvinence caused
"""

def parse_arrdep_time(train, cur_time) -> tuple[datetime.datetime | None, datetime.datetime | None]:
    arr_time = str(train["exp_arr"])
    source = arr_time.lower().startswith("source")
    if not source:
        arr_time, arr_day = str(train["exp_arr"]).split(", ")
        arr_day = int(arr_day.split(" ")[0])
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
        dept = datetime.datetime.strptime(dept_time, "%H:%M").replace(
            cur_time.year, cur_time.month, dept_day, second=cur_time.second
        )
    else:
        dept = None
    return arr, dept

def choose_msg(train, cur_time: datetime.datetime) -> str:
    arr_time, dep_time = parse_arrdep_time(train, cur_time)
    is_originating, is_terminating = arr_time is None, dep_time is None
    msg_priority = "", 100
    if is_originating and not is_terminating:  # Train is originating from here and going somewhere.
        if dep_time > cur_time and (dep_time - cur_time).total_seconds() < 2 * 60:
            msg_priority = departure_ready, 2
        elif dep_time > cur_time and (dep_time - cur_time).total_seconds() < 60 * 60:
            msg_priority = departure, 6
        print(
            arr_time,
            dep_time,
            cur_time,
            (dep_time - cur_time).total_seconds(),
            "Train originates here.",
        )
    elif not is_originating and is_terminating:  # Coming from somewhere and not originating here.
        if arr_time > cur_time and (arr_time - cur_time).total_seconds() < 2 * 60:
            msg_priority = arrival_on, 1
        elif arr_time > cur_time and (arr_time - cur_time).total_seconds() < 10 * 60:
            msg_priority = arrival_shortly, 4
        elif arr_time > cur_time and (arr_time - cur_time).total_seconds() < 20 * 60:
            msg_priority = arrival, 5
        print(
            arr_time,
            dep_time,
            cur_time,
            (arr_time - cur_time).total_seconds(),
            "Train terminates here.",
        )
    else: # Train is coming from somewhere going somewhere, dunno where :)
        if arr_time > cur_time and (arr_time - cur_time).total_seconds() < 2 * 60:
            msg_priority = arrival_on_middle, 1
            print("Generating arriving on message.")
        elif arr_time > cur_time and (arr_time - cur_time).total_seconds() < 10 * 60:
            msg_priority = arrival_shortly_middle, 4
            print("Generating arriving shortly message.")
        elif arr_time > cur_time and (arr_time - cur_time).total_seconds() < 20 * 60:
            msg_priority = arrival_middle, 5
            print("Generating arrival message")

        if dep_time > cur_time and (dep_time - cur_time).total_seconds() < 3 * 60:
            msg_priority = departure_ready, 2
            print("Generating departing ready")

        elif (
            dep_time > cur_time
            and cur_time > arr_time
            and (dep_time - cur_time).total_seconds() < 60 * 60
        ):
            msg_priority = departure, 6
            print("Generating scheduled for departure message.")

        if (
            arr_time < cur_time
            and dep_time > cur_time
            and (dep_time - cur_time).total_seconds() > 2 * 60
        ):
            msg_priority = on_platform, 3

        print(
            arr_time,
            dep_time,
            cur_time,
            (arr_time - cur_time).total_seconds(),
            (dep_time - cur_time).total_seconds(),
        )
    return msg_priority


def replace_stn_names(_str: str) -> str:
    str_list = _str.split(" ")
    for index, str_ in enumerate(str_list):
        if str_ in station_map:
            str_list[index] = station_map[str_].lower()
    return " ".join(str_list)


def replace_abbvs(_str: str) -> str:
    res = _str
    for abbv in abbvs:
        res = res.replace(abbv.lower(), abbvs[abbv].lower())
        res = res.replace(abbv.upper(), abbvs[abbv].lower())
    return res


station_map = json.loads(STATION_FILE.read_text())
station_map = {std_c: replace_abbvs(sta["name"]) for std_c, sta in station_map.items()}


coach_pos_abbv = {
    "PWR": "P W R",
    "GN": "General Compartment",
    "SLRD": "S L R D,",
    "PC": "Pantry Car",
    "GRD": "S L R D,",
}

coach_pos_ann = """
Your kind attention please! Train number: {train[no]} {train[name]}. Coach position from engine:
{train[coach_pos]}.
"""


def coach_pos_main(train_no: str, train_name: str):
    train_correct_number = " ; ".join(train_no[:]) + " ;"

    with ETrainAPISync(captcha_handler=default_captcha_handler) as etrain:
        coach_pos = etrain.get_coach_positions(train_no, train_name)

    coach_pos_str = ";".join(
        f"{coach_pos_abbv.get(c_name, c_name)} {coach_p}"
        for coach_p, c_name in coach_pos.items()
    )

    print(coach_pos_str)
    msg = coach_pos_ann.format_map(
        {
            "train": {
                "no": train_correct_number,
                "name": replace_abbvs(train_name),
                "coach_pos": coach_pos_str,
            }
        }
    )
    print(msg)
    intro = INTROS[1]  # Decrease volume by 3 dB
    with io.BytesIO() as f:
        gTTS(text=msg, lang="en-IN", tld="co.in", slow=False).write_to_fp(f)
        # f.seek(0, 2)
        # pydub.AudioSegment.silent(1000).export(f, format="mp3")
        f.seek(0)
        silent = pydub.AudioSegment.silent(duration=500)
        announcement = pydub.AudioSegment.from_file(f)
        ann_file = ANNOUNCEMENTS_PATH / f"{train_name.replace(' ', '_')}.wav"
        (intro + silent + announcement).export(str(ann_file), format="wav")


def announce(text_msg, format_map=None, languages=LANGUAGES, delta=500):
    format_map = format_map or {}
    pytrans = PyTranslator()
    with io.BytesIO() as f:
        for lang in languages:
            msg = text_msg[lang].replace("\n", " ").format_map(format_map)
            translated = pytrans.translate_dict(msg, dest=lang)["translation"]
            print(translated)
            print(f"Generating for language: {lang}")
            gTTS(text=translated, lang=lang, tld="co.in").write_to_fp(f)
            f.seek(0, 2)
            pydub.AudioSegment.silent(delta).export(f, format="mp3")
            f.seek(0, 2)
        f.seek(0)
        segment: pydub.AudioSegment = pydub.AudioSegment.from_file(f)
        return speedup(segment, playback_speed=1.30)


def format_train_name(train_name: str):
    src, *dest, name = train_name.strip().split(" ")
    print(src, dest, name)
    if "-" in src:
        src, dest = src.split("-")  # handles SRC-DEST
    elif len(dest) == 0:
        dest = ""
    elif len(dest) == 1:
        dest = dest[0]
    
    elif len(dest) >= 2:
        dest = " ".join(dest)
    return replace_abbvs(
        replace_stn_names(
            replace_abbvs(
            f"{src} {dest} {name} "
        )
        )
    ).strip()


async def main(station_name: str, std_code: str, time: datetime.datetime = None, captcha_resolver = None):
    global station_map
    
    time = time or datetime.datetime.now()
    async with ETrainAPIAsync(captcha_resolver=captcha_resolver or async_default_captcha_resolver) as etrain:
        trains = await etrain.get_live_station(std_code, station_name)
        announcements = []
        for train in trains:
            if not train["tt_pf"] or train["tt_pf"].startswith("-"):
                print(train["tt_pf"])
                continue
            train_correct_number = " ; ".join(list(train["train_no"])) + " ;"
            msg, priority = choose_msg(train, cur_time=time)
            arr_time, dep_time = parse_arrdep_time(train, time)
            if not msg:
                continue
            train_info = (
                {
                    "train": {
                        "no": train_correct_number,
                        "name": format_train_name(train["train_name"] + " "),
                        "src": replace_abbvs(replace_stn_names(train["src"] + " ")).strip(),
                        "dest": replace_abbvs(replace_stn_names(train["dest"] + " ")).strip(),
                        "pf": train["tt_pf"],
                        "arr_time": (arr_time or time).strftime("%H:%M"),
                        "dept_time": (dep_time or time).strftime("%H:%M"),
                    }
                }
            )
            print("Getting train schedule...")
            schedule: list = await etrain.get_train_schedule(train["train_no"], train["train_name"].replace(" ", "-"))
            if schedule:
                print("Updating station map...")
                station_map = json.loads(STATION_FILE.read_text())
                station_map.update({sta["code"]: {"code": sta["code"], "name": sta["name"]} for sta in schedule})
                STATION_FILE.write_text(json.dumps(station_map))
                station_map = json.loads(STATION_FILE.read_text())
                station_map = {std_c: replace_abbvs(sta["name"]) for std_c, sta in station_map.items()}

            print("Generating announcement...")
            print(msg)
            intro = INTROS[0]

            announcement = await asyncio.get_event_loop().run_in_executor(None, announce, msg, train_info)
            silent = pydub.AudioSegment.silent(duration=500)
            ann_file = (
                ANNOUNCEMENTS_PATH / f"{train['train_name'].replace(' ', '_')}.wav"
            )
            (intro + silent + (announcement + 3)).export(str(ann_file), format="wav")
            announcements.append(ann_file)
            # if dep_time is not available, then send the arrival time
            yield [ann_file, dep_time or arr_time, priority]
        


def welcome_f(stn_name: str):
    g_msg = goodbye.format_map(
        {
            "station": {
                "name": stn_name,
            }
        }
    )
    msg = welcome.format_map(
        {
            "station": {
                "name": stn_name,
            }
        }
    )
    print(msg)
    intro = INTROS[0]  # Decrease volume by 3 dB

    silent = pydub.AudioSegment.silent(duration=500)
    announcement = announce(msg)
    w_ann = intro + silent + announcement
    announcement = announce(g_msg)
    g_ann = intro + silent + announcement

    silent = pydub.AudioSegment.silent(duration=2000)
    ann_file = ANNOUNCEMENTS_PATH / f"{stn_name.replace(' ', '_')}.mp3"
    (w_ann + silent + g_ann).export(str(ann_file))


if __name__ == "__main__":
    # coach_pos_main("12605", "PALLAVAN EXP")
    print(asyncio.run(main("Tiruchirapalli Junction", "TPJ")))
