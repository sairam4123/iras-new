import asyncio
import datetime
import heapq
import json

import climage
from aioconsole import aprint, ainput
from pydub import AudioSegment
from pydub.playback import play

from player import main as player_main, coach_pos_main, TYPES

station_name = "Tambaram"
station_code = "TBM"

STATIONS_FILE = "stations.json"

PRIORITY_MAP = {
    TYPES["arrival_on"]: 1,
    TYPES["arrival_on_middle"]: 1,
    TYPES["departure_ready"]: 2,
    TYPES["on_platform"]: 3,
    TYPES["arrival_shortly"]: 4,
    TYPES["arrival_shortly_middle"]: 4,
    TYPES["arrival"]: 5,
    TYPES["arrival_middle"]: 5,
    TYPES["departure"]: 6,
}


def fetch_station_name(station_code: str) -> str:
    station_code = station_code.upper()
    stations = json.load(open(STATIONS_FILE))
    return stations.get(station_code, {"name": None})["name"]


ANNOUNCEMENTS = []

last_played = {}  # {ann_file: (last_played_time, ann_type)}

TIME_BETWEEN_ANN_SEC = 70  # 1 minute 10 seconds or 70 seconds


async def async_console_captcha_resolver(
    sd: str, keys: list[str], error: str, file: str
) -> str:
    image = climage.convert(
        file, width=80, is_unicode=True, is_truecolor=True, is_256color=False
    )
    await aprint(image)
    key = await ainput(f"{error}\nPossible keys are: {keys}\n> ")
    print(f"You selected: {key}")
    return key.strip()


# Producer function
async def fetch_announcements():
    while True:
        print("Fetching announcements")
        async for ann_file, dept_time, ann_type, train_info in player_main(
            station_name, station_code, captcha_resolver=async_console_captcha_resolver
        ):
            current_time = datetime.datetime.now()
            train_no = train_info["train"]["no"]
            await aprint(
                f"Dept Time: {dept_time}, Announcement: {ann_file}, Type: {ann_type}, Train No: {train_no}"
            )
            priority = PRIORITY_MAP.get(ann_type, 5)  # default priority is 5
            last_played_time, last_ann_type = last_played.get(train_no, (None, None))
            if last_ann_type is not None and last_played_time is not None:
                priority = wait_time_priority(priority, current_time, last_played_time)
            if (
                ann_type == TYPES["arrival_on"]
                or ann_type == TYPES["arrival_on_middle"]
                or ann_type == TYPES["departure_ready"]
            ):
                # add 3 times to the queue
                heapq.heappush(
                    ANNOUNCEMENTS, (priority, dept_time, ann_file, ann_type, train_no)
                )
                heapq.heappush(
                    ANNOUNCEMENTS, (priority, dept_time, ann_file, ann_type, train_no)
                )
                heapq.heappush(
                    ANNOUNCEMENTS, (priority, dept_time, ann_file, ann_type, train_no)
                )
            else:
                heapq.heappush(
                    ANNOUNCEMENTS, (priority, dept_time, ann_file, ann_type, train_no)
                )
            if (
                ann_type == TYPES["arrival"] or ann_type == TYPES["departure"]
            ):  # coach position announcements
                coach_pos_announcement = await coach_pos_main(
                    train_no, train_info["train"]["name"]
                )
                heapq.heappush(
                    ANNOUNCEMENTS,
                    (
                        priority,
                        dept_time,
                        coach_pos_announcement,
                        4,
                        f"{train_no}_coach_pos",
                    ),
                )

        await asyncio.sleep(TIME_BETWEEN_ANN_SEC)


def wait_time_priority(cur_priority, cur_time, last_played_time):
    # increase priority to improve chances of being played if the announcement was played more than 5 mins ago, but only for critical announcements (priority 1 and 2)
    if (
        cur_priority in [1, 2]
        and last_played_time is not None
        and (cur_time - last_played_time).total_seconds() > 300
    ):
        return (
            cur_priority - 1
        )  # increase priority by 1 level (1 becomes 0, 2 becomes 1)

    # increase priority to improve chances of being played if the announcement was played more than 10 mins, but for non-critical announcements (priority >3)
    if (
        cur_priority > 3
        and last_played_time is not None
        and (cur_time - last_played_time).total_seconds() > 600
    ):
        return cur_priority - 1  # increase priority by 1 level
    return cur_priority


# hi-IN-Chirp3-HD-Vindemiatrix
# Consumer function
async def play_announcements():
    while True:
        if len(ANNOUNCEMENTS) > 0:
            priority, dept_time, ann_file, ann_type, train_no = heapq.heappop(
                ANNOUNCEMENTS
            )
            await aprint(
                f"Now Playing: Priority: {priority}, Dept Time: {dept_time}, Announcement: {ann_file}, Type: {ann_type}, Train No: {train_no}"
            )

            current_time = datetime.datetime.now()
            if dept_time is None:
                dept_time = current_time

            # Ignore the announcement if it's already played for the specific train in the last 5 mins but only for the same type of announcement. For example, if an arrival announcement is played, then ignore any subsequent arrival announcements for the same train for the next 5 mins, but allow departure announcements for the same train.
            last_played_time, last_ann_type = last_played.get(train_no, (None, None))
            if (
                last_ann_type is not None
                and last_played_time is not None
                and (last_ann_type in [5] or ann_type in [5])
            ):
                if (
                    current_time - last_played_time
                ).total_seconds() < 60:  # 5 minutes = 300 seconds
                    print(
                        f"Skipping announcement {ann_file} as it was played recently (critical announcement - {(current_time - last_played_time).total_seconds()} seconds < 60)"
                    )
                    continue
            if last_ann_type in [2, 3, 5] or ann_type in [2, 3, 5]:
                if (
                    last_ann_type is not None
                    and last_played_time is not None
                    and (current_time - last_played_time).total_seconds() < 150
                ):  # 2.5 minutes = 150 seconds
                    print(
                        f"Skipping announcement {ann_file} as it was played recently (critical announcement - {(current_time - last_played_time).total_seconds()} seconds < 150)"
                    )
                    continue

            if (
                last_played_time
                and (current_time - last_played_time).total_seconds() < 240
            ):  # 4 minutes = 4*60 seconds
                if last_ann_type == ann_type:
                    print(
                        f"Skipping announcement {ann_file} as it was played recently - {(current_time - last_played_time).total_seconds()} seconds < 240"
                    )
                    continue
                # but if the announcement type is (arriving on, on platform, departure ready), do not ignore those announcements but set it to every 2-3 mins instead of 5 mins, as those are more critical announcements.

            last_played[train_no] = (current_time, ann_type)

            if dept_time < current_time:
                print(
                    f"Announcement time is in the past, skipping. {dept_time} < {current_time} - {(dept_time - current_time).seconds:.2f} seconds; {ann_file}"
                )
                continue
            ann_seg: AudioSegment = AudioSegment.from_file(ann_file)

            task = None
            try:
                task = asyncio.get_event_loop().run_in_executor(None, play, ann_seg)

                while True:
                    await asyncio.sleep(0.5)
                    if task.done():
                        break

            except KeyboardInterrupt:
                if task:
                    task.cancel()
                print("Playback interrupted")
                break

        else:
            await asyncio.sleep(1)


async def main():
    global station_name, station_code
    station_code = (str(await ainput("Select station:> "))).upper().strip()
    station_name = fetch_station_name(station_code)
    if station_name is None:
        await aprint("Station not found")
        return
    await aprint("Station selected: " + station_name)
    fetch = asyncio.create_task(fetch_announcements())
    play_ann = asyncio.create_task(play_announcements())

    await asyncio.gather(fetch, play_ann)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting...")
        exit(0)
