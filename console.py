import asyncio
import datetime
import heapq

import climage
from aioconsole import aprint, ainput

from player import main as player_main
from etrainlib import async_default_captcha_resolver

from pydub import AudioSegment
from pydub.playback import play

station_name = 'Tambaram'
station_code = 'TBM'

ANNOUNCEMENTS = []

TIME_BETWEEN_ANN_SEC = 30  # 1 minute 30 seconds or 90 seconds

async def async_console_captcha_resolver(sd: str, keys: list[str], error: str) -> str:
    image = climage.convert('.etrain-cache/' + sd.replace('.', '_') + '.png', width=80, is_unicode=True, is_truecolor=True, is_256color=False)
    await aprint(image)
    key = await ainput(
        f"{error}\nPossible keys are: {keys}\n> "
    )
    return key.strip()

async def fetch_announcements():
    while True:
        print('Fetching announcements')
        async for (ann_file, dept_time, priority) in player_main(station_name, station_code, captcha_resolver=async_console_captcha_resolver):
            await aprint(f'Priority: {priority}, Dept Time: {dept_time}, Announcement: {ann_file}')
            heapq.heappush(ANNOUNCEMENTS, (priority, dept_time, ann_file))
        await asyncio.sleep(TIME_BETWEEN_ANN_SEC)

async def play_announcements():
    while True:
        if len(ANNOUNCEMENTS) > 0:
            priority, dept_time, ann_file = heapq.heappop(ANNOUNCEMENTS)
            await aprint(f'Priority: {priority}, Dept Time: {dept_time}, Announcement: {ann_file}')
            current_time = datetime.datetime.now()
            if dept_time < current_time:
                continue
            ann_seg: AudioSegment = AudioSegment.from_file(ann_file)
            asyncio.get_event_loop().run_in_executor(None, play, ann_seg)
            await asyncio.sleep(ann_seg.duration_seconds)
        else:
            await asyncio.sleep(1)

async def main():
    fetch = asyncio.create_task(fetch_announcements())
    play_ann = asyncio.create_task(play_announcements())

    await asyncio.gather(fetch, play_ann)

if __name__ == '__main__':
    asyncio.run(main())