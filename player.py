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
from etrainlib._sync import ETrainAPI


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


arrival = {
    "en": """
Your kind attention please! Train number: {train[no]} {train[name]} coming from {train[src]} will arrive on platform number {train[pf]}.
""",
    "hi": """
Your kind attention please! Train number: {train[no]} {train[name]} coming from {train[src]} will come on platform number {train[pf]}.
""",
    "ta": """
Passengers attention please, Train number: {train[no]} {train[name]} coming from {train[src]} will arrive on platform number {train[pf]}.
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


def choose_msg(train, cur_time: datetime.datetime) -> str:
    arr = train["exp_arr"].split(", ")[0]
    source = arr.lower().startswith("source")
    if not source:
        day = int(train["exp_arr"].split(", ")[1].split(" ")[0])
        arr = datetime.datetime.strptime(arr, "%H:%M").replace(
            cur_time.year, cur_time.month, day, second=cur_time.second
        )

    dept = train["exp_dept"].split(", ")[0]
    dest = dept.lower().startswith("dest")
    print(train["exp_arr"])
    print(train["exp_dept"])
    if not dest:
        day = int(train["exp_dept"].split(", ")[1].split(" ")[0])
        dept = datetime.datetime.strptime(dept, "%H:%M").replace(
            cur_time.year, cur_time.month, day, second=cur_time.second
        )
    msg = ""
    if source and not dest:  # Train is originating from here and not terminating here
        if dept > cur_time and (dept - cur_time).total_seconds() < 120:
            msg = departure_ready

        elif dept > cur_time and (dept - cur_time).total_seconds() < 60 * 60:
            msg = departure
        print(
            arr,
            dept,
            cur_time,
            (dept - cur_time).total_seconds(),
            "Train originates here.",
        )
    elif not source and dest:  # Coming from somewhere and not originating here.
        if arr > cur_time and (arr - cur_time).total_seconds() < 60:
            msg = arrival_on
        elif arr > cur_time and (arr - cur_time).total_seconds() < 20 * 60:
            msg = arrival_shortly
        print(
            arr,
            dept,
            cur_time,
            (arr - cur_time).total_seconds(),
            "Train terminates here.",
        )
    else:
        if arr > cur_time and (arr - cur_time).total_seconds() < 2 * 60:
            msg = arrival_on
            print("Generating arriving on message.")
        elif arr > cur_time and (arr - cur_time).total_seconds() < 10 * 60:
            msg = arrival_shortly
            print("Generating arriving shortly message.")
        elif arr > cur_time and (arr - cur_time).total_seconds() < 20 * 60:
            msg = arrival
            print("Generating arrival message")

        if dept > cur_time and (dept - cur_time).total_seconds() < 3 * 60:
            msg = departure_ready
            print("Generating departing ready")

        elif (
            dept > cur_time
            and cur_time > arr
            and (dept - cur_time).total_seconds() < 60 * 60
        ):
            msg = departure
            print("Generating scheduled for departure message.")

        if (
            arr < cur_time
            and dept > cur_time
            and (dept - cur_time).total_seconds() > 3 * 60
        ):
            msg = on_platform

        print(
            arr,
            dept,
            cur_time,
            (arr - cur_time).total_seconds(),
            (dept - cur_time).total_seconds(),
        )
    return msg


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

    with ETrainAPI(captcha_handler=default_captcha_handler) as etrain:
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
        return speedup(segment, playback_speed=1.15)


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
            msg = choose_msg(train, cur_time=time)
            dept = train["exp_dept"].split(", ")[0]
            dest = dept.lower().startswith("dest")
            if not dest:
                day = int(train["exp_dept"].split(", ")[1].split(" ")[0])
                dept = datetime.datetime.strptime(dept, "%H:%M").replace(
                    time.year, time.month, day, second=time.second
                )
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
                        "dept_time": train["exp_dept"].split(" ")[0],
                    }
                }
            )
            print("Getting train schedule...")
            schedule: list = await etrain.get_train_schedule(train["train_no"], train["train_name"].replace(" ", "-"))
            if schedule:
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
            yield [ann_file, dept]
        


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
