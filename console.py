import asyncio
import datetime
import heapq
import json

import climage
from aioconsole import aprint, ainput
from pydub import AudioSegment
from pydub.playback import play

from player import main as player_main

station_name = 'Tambaram'
station_code = 'TBM'

STATIONS_FILE = 'stations.json'

def fetch_station_name(station_code: str) -> str:
    station_code = station_code.upper()
    stations = json.load(open(STATIONS_FILE))
    return stations.get(station_code, {'name': None})['name']

ANNOUNCEMENTS = []

TIME_BETWEEN_ANN_SEC = 70  # 1 minute 30 seconds or 90 seconds

async def async_console_captcha_resolver(sd: str, keys: list[str], error: str, file: str) -> str:
    image = climage.convert(file, width=80, is_unicode=True, is_truecolor=True, is_256color=False)
    await aprint(image)
    key = await ainput(
        f"{error}\nPossible keys are: {keys}\n> "
    )
    print(f"You selected: {key}")
    return key.strip()

# Producer function
async def fetch_announcements():
    while True:
        print('Fetching announcements')
        async for (ann_file, dept_time, priority) in player_main(station_name, station_code, captcha_resolver=async_console_captcha_resolver):
            await aprint(f'Priority: {priority}, Dept Time: {dept_time}, Announcement: {ann_file}')
            heapq.heappush(ANNOUNCEMENTS, (priority, dept_time, ann_file))
        await asyncio.sleep(TIME_BETWEEN_ANN_SEC)

# Consumer function
async def play_announcements():
    while True:
        if len(ANNOUNCEMENTS) > 0:
            priority, dept_time, ann_file = heapq.heappop(ANNOUNCEMENTS)
            await aprint(f'Priority: {priority}, Dept Time: {dept_time}, Announcement: {ann_file}')
            current_time = datetime.datetime.now()
            if dept_time is None:
                dept_time = current_time
            if dept_time < current_time:
                continue
            ann_seg: AudioSegment = AudioSegment.from_file(ann_file)
            try:
                task = asyncio.get_event_loop().run_in_executor(None, play, ann_seg)

                while True:
                    await asyncio.sleep(0.5)
                    if task.done():
                        break

            except KeyboardInterrupt:
                task.cancel()
                print("Playback interrupted")
                break

        else:
            await asyncio.sleep(1)

async def main():
    global station_name, station_code
    station_code = await ainput('Select station:> ')
    station_name = fetch_station_name(station_code)
    if station_name is None:
        await aprint("Station not found")
        return
    await aprint("Station selected: " + station_name)
    fetch = asyncio.create_task(fetch_announcements())
    play_ann = asyncio.create_task(play_announcements())

    await asyncio.gather(fetch, play_ann)

if __name__ == '__main__':
    asyncio.run(main())