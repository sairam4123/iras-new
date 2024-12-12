import datetime
from pathlib import Path

import discord
import gtts
import pydub
import re
import time
import espeak_ng

from collections import defaultdict

from discord.ext import commands, tasks

import heapq

# from utils.time import FutureTime
from datetime import timedelta
import json
import re

from etrainlib._async import ETrainAPIAsync
from etrainlib.constants import ETrainAPIError
from player import main as player_main
from etrainlib import CACHE_FOLDER

STATION_FILE = Path("stations.json")

TTS_FILE_FORMAT = "{0.id}-{1}.wav"
TTS_FOLDER = Path.cwd() / ".tts"


songs = defaultdict(list)

announcements = {} # voice_id: {"station": "TBM", "platform": 6}

voice_client: discord.VoiceClient = None

tts_speaker = espeak_ng.Speaker()

class CaptchaButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str):
        self.view: CaptchaView
        super().__init__(style=discord.ButtonStyle.secondary, label=label, custom_id=custom_id)
    
    async def callback(self, interaction: discord.Interaction):
        print("Selected: ", interaction.custom_id)
        await interaction.response.send_message(f"Selected: {interaction.custom_id}", ephemeral=True)
        self.view.selected = self.custom_id
        self.style = discord.ButtonStyle.success
        await interaction.edit_original_response(content="Thank you for resolving the captcha!")
        self.view.disable_all_items()
        await self.view.message.edit(view=self.view)
        self.view.stop()

class CaptchaView(discord.ui.View):
    def __init__(self, sd: str, keys: list[str], author_id: str):
        super().__init__()
        self.sd = sd
        self.keys = keys
        self.selected = None
        self.author_id = author_id  
        self.btns = [
            CaptchaButton(key, key)
            for key in keys
        ]
        for btn in self.btns:
            self.add_item(btn)
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id
    
    

class TrainBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.voice_client = None
    
    @tasks.loop(minutes=1, seconds=30)
    async def play_announcement(self, *args, **kwargs):
        print("Checking for announcements")
        for guild_id in announcements:
            station = announcements[guild_id]["station"]
            channel_id = announcements[guild_id]["channel"]
            author_id = announcements[guild_id]["author"]
            channel = await self.fetch_channel(channel_id)

            async def _captcha_resolver(sd: str, keys: list[str], error: str) -> str:
                view = CaptchaView(sd, keys, author_id)
                await channel.send(f"Look at the below image and select the key: {error}", file=discord.File(CACHE_FOLDER / f"{sd.replace('.', '_')}.png"), view=view, delete_after=180)

                await view.wait()
                key = view.selected
                if view.selected is None:
                    raise ETrainAPIError("No key selected")
                return str(key).strip()

            
            station_code, station_name = station.split(" - ")
            async for (ann, dept_time, priority) in player_main(station_name.title(), station_code, captcha_resolver=_captcha_resolver):
                # if songs.get(guild_id):
                #     songs[guild_id].extend([[str(ann), author_id, channel_id, dept_time]] * 2)
                # else:
                #     songs[guild_id] = deque([[str(ann), author_id, channel_id, dept_time]] * 2)
                heapq.heappush(songs[guild_id], [priority, [str(ann), author_id, channel_id, dept_time]])
                await channel.send("Queued! " + str(ann))
                if not voice_client.is_playing():
                    priority, song_info = heapq.heappop(songs[guild_id])
                    try: 
                        await play_song(*song_info)
                    except (IndexError, discord.ClientException):
                        print("Tried to play song, but voice client is already playing audio. Adding to queue.")
                        heapq.heappush(songs[guild_id], [priority, song_info])

    async def on_ready(self):
        self.play_announcement.start()
        print("I'm ready!")
        print("Started tasks!")
        TTS_FOLDER.mkdir(exist_ok=True)
    
    async def setup_hook(self):
        self.play_announcement.start()
        print("Started tasks!")

bot = TrainBot(command_prefix=",", intents=discord.Intents.all())

# recognizer = speech_recognition.Recognizer()
# recognizer.vosk_model = Model("models/en-IN")



# def asyncify(func):
#     @functools.wraps(func)
#     async def run(*args, loop=None, executor=None, **kwargs):
#         if loop is None:
#             loop = asyncio.get_event_loop()
#         pfunc = functools.partial(func, *args, **kwargs)
#         return await loop.run_in_executor(executor, pfunc)

#     return run



async def play_song(wav_file, author_id, channel_id, *args):
    message = None
    channel = await bot.fetch_channel(channel_id)
    user = await bot.fetch_user(author_id)
    if not voice_client.is_playing():

        message = await channel.send(
            f"Playing file: {wav_file}!"
        )
        # tts(
        #     f"Playing file {wav_file}! Added by {user.display_name}", user, voice_client
        # )
        if wav_file.endswith("mp3"):
            voice_client.play(
                discord.FFmpegPCMAudio(
                    f'mp3s/waves/{wav_file.replace(".mp3", ".wav")}'
                ),
                after=song_completed,
            )
        elif wav_file.endswith("ogg"):
            voice_client.play(
                discord.FFmpegPCMAudio(
                    f'oggs/waves/{wav_file.replace(".ogg", ".wav")}'
                ),
                after=song_completed,
            )
        elif wav_file.endswith("wav"):
            voice_client.play(
                discord.FFmpegPCMAudio(f"{wav_file}"), after=song_completed
            )
        return message


def tts(tts_message, tts_id, tts_vc: discord.VoiceClient):
    tts_file = get_tts(tts_id, tts_message)
    tts_vc.play(discord.FFmpegPCMAudio(str(tts_file)))
    while tts_vc.is_playing():
        time.sleep(0.01)
    tts_vc.stop()


def get_tts(tts_id, tts_message):
    tts_file = TTS_FOLDER / TTS_FILE_FORMAT.format(tts_id, 0)
    google = False
    if google:
        tts_file = tts_file.with_suffix(".mp3")
        gtts.gTTS(tts_message, lang="en").save(str(tts_file))
        pydub.AudioSegment.from_mp3(tts_file).export(
            str(tts_file.with_suffix(".wav")), format="wav"
        )
    else:
        tts_speaker.speak(tts_message).save_wav(str(tts_file))
    return tts_file.with_suffix(".wav")


async def station_autocomplete(ctx: discord.AutocompleteContext):
    stations = [
        sta + " - " + sta_name["name"]
        for sta, sta_name in json.loads(STATION_FILE.read_text()).items()
    ]
    filtered = list(
        filter(lambda std_code: bool(re.search(ctx.value.upper(), std_code)), stations)
    )
    return filtered[:25]



@bot.slash_command(guild_ids=["744194428209463296"])
@discord.option("station", autocomplete=station_autocomplete)
async def start_announcement(
    ctx: discord.ApplicationContext, station: str
):
    global voice_client

    station_code, station_name = station.split(" - ")

    if not ctx.user.voice:
        await ctx.respond("Connect to a voice channel please!")

    await ctx.respond(f"Starting announcement for: {station}")
    if not ctx.voice_client:
        voice_client = await ctx.user.voice.channel.connect()
    tts(
        f"Starting announcement system for {station}",
        ctx.author,
        voice_client,
    )

    announcements[ctx.voice_client.guild.id] = {"station": station, "author": ctx.author.id, "channel": ctx.channel_id}

    async def _captcha_handler(sd: str, keys: list[str], error: str) -> str:
        view = CaptchaView(sd, keys, ctx.author.id)
        await ctx.send(f"Look at the below image and select the key: {error}", file=discord.File(CACHE_FOLDER / f"{sd.replace('.', '_')}.png"), view=view, delete_after=180)

        await view.wait()
        key = view.selected
        if view.selected is None:
            raise ETrainAPIError("No key selected")
        return key.strip()

    try:
        priority: int; ann: Path; dept_time: str | datetime.datetime
        async for (ann, dept_time, priority) in player_main(station_name.title(), station_code, captcha_resolver=_captcha_handler):
            heapq.heappush(songs[ctx.guild_id], [priority, [str(ann), ctx.author.id, ctx.channel_id, dept_time]])
            await ctx.respond("Queued! " + str(ann))
            if not voice_client.is_playing():
                _, song_info = heapq.heappop(songs[ctx.guild_id])
                await play_song(*song_info)
    except ETrainAPIError as e:
        await ctx.send(f"Error: {e}")
        import traceback
        traceback.print_exc()

@bot.slash_command(guild_ids=["744194428209463296"])
async def stop_announcement(ctx: discord.ApplicationContext):
    await ctx.defer()
    if ctx.voice_client:
        del announcements[ctx.voice_client.guild.id]
        await ctx.respond("Stopped announcement system!")
        await ctx.voice_client.stop()
        tts("Stopping announcement system!", ctx.author, ctx.voice_client)
        await ctx.voice_client.disconnect()
    else:
        await ctx.respond("No announcement system running!")


def song_completed(error):
    if error:
        raise error
    if songs.get(voice_client.guild.id):
        print("executing queue")
        dept_time: str | datetime.datetime
        _, [wav_file, author_id, channel_id, dept_time] = heapq.heappop(songs[voice_client.guild.id])
        print("Dept Time: ", dept_time)
        if type(dept_time) == str and dept_time == "Destination":
            bot.loop.create_task(play_song(wav_file, author_id, channel_id))
            return
        cur_time = datetime.datetime.now()
        while dept_time < cur_time:
            _, [wav_file, author_id, channel_id, dept_time] = heapq.heappop(songs[voice_client.guild.id])
        bot.loop.create_task(play_song(wav_file, author_id, channel_id))


bot.run(open(Path.cwd() / "bot.tkn").read())
