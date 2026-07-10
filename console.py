import asyncio
import datetime
import heapq
import json

import climage
from aioconsole import aprint, ainput
import simpleaudio as sa
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio as play
from tqdm import tqdm
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

REPEAT_MAP = {
    TYPES["arrival_on"]: 3,
    TYPES["arrival_on_middle"]: 3,
    TYPES["departure_ready"]: 3,
    TYPES["on_platform"]: 3,
    TYPES["arrival_shortly"]: 2,
    TYPES["arrival_shortly_middle"]: 2,
    TYPES["arrival"]: 2,
    TYPES["arrival_middle"]: 2,
    TYPES["departure"]: 2,
}

COOLDOWN_MAP = {
    TYPES["arrival_on"]: 70,  # 1 minute 10 seconds
    TYPES["arrival_on_middle"]: 70,  # 1 minute 10 seconds
    TYPES["departure_ready"]: 70,  # 1 minute 10 seconds
    TYPES["on_platform"]: 90,  # 1 minute 30 seconds
    TYPES["arrival_shortly"]: 180,  # 3 minutes
    TYPES["arrival_shortly_middle"]: 180,  # 3 minutes
    TYPES["arrival"]: 300,  # 5 minutes
    TYPES["arrival_middle"]: 300,  # 5 minutes
    TYPES["departure"]: 300,  # 5 minutes
}

COOLDOWN_BURST_MAP = {
    TYPES["arrival_on"]: 5,  # 5 seconds
    TYPES["arrival_on_middle"]: 10,  # 10 seconds
    TYPES["departure_ready"]: 0,  # 0 seconds
    TYPES["on_platform"]: 10,  # 10 seconds
    TYPES["arrival_shortly"]: 30,  # 30 seconds
    TYPES["arrival_shortly_middle"]: 30,  # 30 seconds
    TYPES["arrival"]: 60,  # 1 minute
    TYPES["arrival_middle"]: 60,  # 1 minute
    TYPES["departure"]: 90,  # 1 minute 30 seconds
}


def fetch_station_name(station_code: str) -> str:
    station_code = station_code.upper()
    stations = json.load(open(STATIONS_FILE))
    return stations.get(station_code, {"name": None})["name"]


ANNOUNCEMENTS = []

last_played = {}  # {ann_file: (last_played_time, ann_type, times_played, last_played_burst_time)}

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
            last_played_time, last_ann_type, times_played, last_played_burst_time = (
                last_played.get(train_no, (None, None, 0, None))
            )
            if last_ann_type is not None and last_played_time is not None:
                priority = wait_time_priority(priority, current_time, last_played_time)
            for _ in range(REPEAT_MAP.get(ann_type, 2)):  # default repeat is 2
                heapq.heappush(
                    ANNOUNCEMENTS,
                    (
                        priority,
                        dept_time,
                        ann_file,
                        ann_type,
                        train_no,
                    ),
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
            await aprint(f"Announcement Queue Length: {len(ANNOUNCEMENTS)}")

            current_time = datetime.datetime.now()
            if dept_time is None:
                dept_time = current_time

            if (
                dept_time - current_time
            ).total_seconds() < -60:  # announcement is more than 1 min late
                print(
                    f"Announcement time is in the past, skipping. {dept_time} < {current_time} - {(dept_time - current_time).seconds:.2f} seconds; {ann_file}"
                )
                continue

            # Ignore the announcement if it's already played for the specific train in the last 5 mins but only for the same type of announcement. For example, if an arrival announcement is played, then ignore any subsequent arrival announcements for the same train for the next 5 mins, but allow departure announcements for the same train.
            last_played_time, last_ann_type, times_played, last_played_burst_time = (
                last_played.get(train_no, (None, None, 0, None))
            )
            max_play_times = REPEAT_MAP.get(ann_type, 2)  # default max play times is 2
            cooldown_time = COOLDOWN_MAP.get(
                ann_type, 300
            )  # default cooldown is 5 mins
            burst_cooldown_time = COOLDOWN_BURST_MAP.get(
                ann_type, 60
            )  # default burst cooldown is 1 min
            if times_played >= max_play_times:
                if (
                    last_played_time is not None
                    and (current_time - last_played_time).total_seconds()
                    < cooldown_time
                    and (last_ann_type == ann_type)
                ):
                    print(
                        f"Skipping announcement {ann_file} as it has already been played {times_played} times (max allowed: {max_play_times}) [Type: {ann_type}] and is on cooldown. Last played {(current_time - last_played_time).total_seconds()} seconds ago. Train No: {train_no} | Last Announcement Type: {last_ann_type} | Cooldown: {cooldown_time} seconds | Burst Cooldown: {burst_cooldown_time} seconds"
                    )
                    continue
                last_played[train_no] = (
                    current_time,
                    ann_type,
                    0,
                    current_time,
                )  # reset times played for this train and announcement type
                print(
                    f"Reset times played for this train and announcement type [Type: {ann_type}] [Train No: {train_no}] | [Last Announcement Type: {last_ann_type}] | Last played {(current_time - last_played_time).total_seconds()} seconds ago. | Cooldown: {cooldown_time} seconds | Burst Cooldown: {burst_cooldown_time} seconds"
                )
            elapsed = (
                (current_time - last_played_burst_time).total_seconds()
                if last_played_burst_time is not None
                else None
            )
            if (
                elapsed is not None
                and elapsed < burst_cooldown_time
                and last_ann_type == ann_type
            ):
                print(
                    f"Skipping announcement {ann_file} as it is on burst cooldown. Last played {(current_time - last_played_burst_time).total_seconds()} seconds ago. Train No: {train_no} | Last Announcement Type: {last_ann_type}"
                )
                continue
            # if (
            #     last_ann_type is not None
            #     and last_played_time is not None
            #     and (last_ann_type in [5] or ann_type in [5])
            #     and (times_played >= max_play_times)
            # ):
            #     if (
            #         current_time - last_played_time
            #     ).total_seconds() < 60:  # 5 minutes = 300 seconds
            #         print(
            #             f"Skipping announcement {ann_file} as it was played recently (critical announcement - {(current_time - last_played_time).total_seconds()} seconds < 60)"
            #         )
            #         continue
            # if last_ann_type in [2, 3, 5] or ann_type in [2, 3, 5]:
            #     if (
            #         last_ann_type is not None
            #         and last_played_time is not None
            #         and (current_time - last_played_time).total_seconds() < 150
            #         and (times_played >= max_play_times)
            #     ):  # 2.5 minutes = 150 seconds
            #         print(
            #             f"Skipping announcement {ann_file} as it was played recently (critical announcement - {(current_time - last_played_time).total_seconds()} seconds < 150)"
            #         )
            #         continue

            # if (
            #     last_played_time
            #     and (current_time - last_played_time).total_seconds() < 240
            #     and (times_played >= max_play_times)
            # ):  # 4 minutes = 4*60 seconds
            #     if last_ann_type == ann_type:
            #         print(
            #             f"Skipping announcement {ann_file} as it was played recently - {(current_time - last_played_time).total_seconds()} seconds < 240"
            #         )
            #         continue
            #     # but if the announcement type is (arriving on, on platform, departure ready), do not ignore those announcements but set it to every 2-3 mins instead of 5 mins, as those are more critical announcements.

            ann_seg: AudioSegment = AudioSegment.from_file(ann_file)
            print(
                f"Playing announcement: {ann_file} - {len(ann_seg) / 1000:.2f} seconds long"
            )
            playback = None
            try:
                tqdm_bar = tqdm(
                    total=len(ann_seg) / 1000, unit="s", desc=f"Playing {ann_file}"
                )
                playback = play(ann_seg)
                i = 0
                while playback.is_playing():
                    await asyncio.sleep(0.5)
                    i += 0.5
                    tqdm_bar.update(0.5)
                    tqdm_bar.set_postfix_str(f"Playing {ann_file} - {i:.2f}/{len(ann_seg) / 1000:.2f} seconds")
                    # if i % 2 == 0:  # Print every 1 second (0.5 * 2)
                    #     print(
                    #         f"Announcement {ann_file} is playing {i}/{len(ann_seg) / 1000:.2f}..."
                    #     )
                else:
                    print("Exited playback loop, announcement finished playing.")
                print(f"Calling wait_done() for announcement {ann_file}...")
                playback.wait_done()
                print(f"Announcement {ann_file} finished playing.")

            except KeyboardInterrupt:
                print("Playback interrupted")
                if playback:
                    playback.stop()
                break
            except Exception as e:
                print(f"Error playing announcement {ann_file}: {e}")

            current_time = datetime.datetime.now()
            last_played[train_no] = (
                current_time,
                ann_type,
                times_played + 1,
                current_time,
            )
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
