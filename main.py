import asyncio
import datetime
from pathlib import Path
from typing import Optional

import discord
import gtts
import pydub
import speech_recognition
import re
import functools
import asyncio
import time
import espeak_ng

from collections import deque

from io import BytesIO, StringIO, BufferedIOBase
from discord.ext import commands, tasks
from discord.sinks import Filters, default_filters
from vosk import Model

# import heapq

# from utils.time import FutureTime
from datetime import timedelta
import json
import re

from etrainlib._async import ETrainAPIAsync
from etrainlib.constants import ETrainAPIError
from player import main as player_main
from etrainlib import CACHE_FOLDER

class TrainBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.voice_client = None
    
    @tasks.loop(minutes=3)
    async def play_announcement(self, *args, **kwargs):
        print("Checking for announcements")
        for guild_id in announcements:
            station = announcements[guild_id]["station"]
            channel_id = announcements[guild_id]["channel"]
            author_id = announcements[guild_id]["author"]
            channel = await self.fetch_channel(channel_id)

            async def _captcha_resolver(sd: str, keys: list[str]) -> str:
                await channel.send(f"Look for the image in .etrain-cache folder with name: {sd.replace('.', '_')}: \nPossible keys are: {keys}", file=discord.File(CACHE_FOLDER / f"{sd.replace('.', '_')}.png"))
                key = await bot.wait_for("message", check=lambda m: m.author.id == author_id)
                return key.content.strip()

            
            station_code, station_name = station.split(" - ")
            async for (ann, dept_time) in player_main(station_name.title(), station_code, captcha_resolver=_captcha_resolver):
                if songs.get(guild_id):
                    songs[guild_id].extend([[str(ann), author_id, channel_id, dept_time]] * 2)
                else:
                    songs[guild_id] = deque([[str(ann), author_id, channel_id, dept_time]] * 2)
                await channel.send("Queued! " + str(ann))
                if not voice_client.is_playing():
                    await play_song(*(songs[guild_id].popleft()))

    async def on_ready(self):
        self.play_announcement.start()
        print("I'm ready!")
        print("Started tasks!")
    
    async def setup_hook(self):
        self.play_announcement.start()
        print("Started tasks!")

bot = TrainBot(command_prefix=",", intents=discord.Intents.all())

# recognizer = speech_recognition.Recognizer()
# recognizer.vosk_model = Model("models/en-IN")

STATION_FILE = Path("stations.json")
TRAIN_FILE = Path("trains.json")

speech_recognition_recordings = Path.cwd() / "recordings"
text_to_speech_recordings = Path.cwd() / "text_to_speech"
speech_recognition_converted_recordings = Path.cwd() / "speech_recognition"


text_to_speech_file_format = "{0.id}-{1}.wav"
speech_recognition_file_format = "{0}-{1}.wav"
listening = False
songs = {}

announcements = {} # voice_id: {"station": "TBM", "platform": 6}

voice_client: discord.VoiceClient = None

tts_speaker = espeak_ng.Speaker()


def asyncify(func):
    @functools.wraps(func)
    async def run(*args, loop=None, executor=None, **kwargs):
        if loop is None:
            loop = asyncio.get_event_loop()
        pfunc = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(executor, pfunc)

    return run


# @bot.event
# async def on_ready():
#     print("I'm ready!")
#     text_to_speech_recordings.mkdir(parents=True, exist_ok=True)
#     speech_recognition_recordings.mkdir(parents=True, exist_ok=True)


# @bot.slash_command(guild_ids=["744194428209463296"])
# @discord.option("wav_file", autocomplete=wav_file_autocomplete)
# async def play_file(ctx: discord.ApplicationContext, wav_file: str):
#     global voice_client

#     if not ctx.user.voice:
#         await ctx.respond("Connect to a voice channel please!")
#     await ctx.defer()

#     if not ctx.voice_client:
#         voice_client = await ctx.user.voice.channel.connect()

#     # queue
#     if ctx.voice_client.is_playing():
#         if songs.get(ctx.guild_id):
#             songs[ctx.guild_id].append([wav_file, ctx.author.id, ctx.channel_id])
#         else:
#             songs[ctx.guild_id] = deque([[wav_file, ctx.author.id, ctx.channel_id]])
#         await ctx.respond("Queued!")
#     else:
#         tts("Loading file!", ctx.author, voice_client)
#         await ctx.respond("Loading file!")
#         if not wav_file.endswith(".wav"):
#             tts("Converting to wave format!", ctx.author, voice_client)

#     abs_path = None
#     wav_path = None

#     if wav_file.endswith("mp3"):
#         abs_path = Path.cwd() / "mp3gs" / wav_file
#         wav_path = (
#             abs_path.parent.parent / "mp3s" / "waves" / wav_file.replace(".mp3", ".wav")
#         )
#     if wav_file.endswith(".ogg"):
#         abs_path = Path.cwd() / "oggs" / wav_file
#         wav_path = (
#             abs_path.parent.parent / "oggs" / "waves" / wav_file.replace(".ogg", ".wav")
#         )
#     if wav_file.endswith("wav"):
#         abs_path = Path.cwd() / "waves" / wav_file
#     if wav_file.endswith("mp3") and not wav_path.exists():
#         pydub.AudioSegment.from_mp3(abs_path).export(wav_path, format="wav")
#     if wav_file.endswith("ogg") and not wav_path.exists():
#         pydub.AudioSegment.from_ogg(abs_path).export(wav_path, format="wav")

#     if voice_client.is_playing():
#         return

#     message = await play_song(wav_file, ctx.author.id, ctx.channel_id)

#     while ctx.voice_client.is_playing():
#         await message.edit(f"Is Playing: {voice_client.is_playing()}")
#         await asyncio.sleep(5)
#     await message.edit(f"Playing: {wav_file}")
#     if not songs.get(ctx.guild_id):
#         ctx.voice_client.stop()


async def play_song(wav_file, author_id, channel_id, *args):
    # elif wav_file.endswith('wav'):
    # pydub.AudioSegment.from_wav(abs_path).export(io_base, format="wav")
    message = None
    channel = await bot.fetch_channel(channel_id)
    user = await bot.fetch_user(author_id)
    if not voice_client.is_playing():

        # if not wav_file.endswith('wav'):
        #     exten = wav_file.split(".")[-1]
        #     if wav_path.exists():
        #         await ctx.respond(f'Loading {exten} file')
        #         tts(f"Loading {exten} file", ctx.user, ctx.voice_client)
        #     # else:
        #     #     await ctx.respond(f'Converting {exten} -> wav, pls wait!')
        #     #     tts(f"Converting {exten} file, please wait", ctx.user, ctx.voice_client)
        # if wav_file.endswith('wav'):
        #     await ctx.respond('Loading wav file!')
        #     tts("Loading wav file", ctx.user, ctx.voice_client)

        message = await channel.send(
            f"Playing file: {wav_file}! Added by {user.display_name}"
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
    tts_file = text_to_speech_recordings / text_to_speech_file_format.format(tts_id, 0)
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

    async def _captcha_handler(sd: str, keys: list[str]) -> str:
        await ctx.send(f"Look for the image in .etrain-cache folder with name: {sd.replace('.', '_')}: \nPossible keys are: {keys}", file=discord.File(CACHE_FOLDER / f"{sd.replace('.', '_')}.png"))
        key = await bot.wait_for("message", check=lambda m: m.author == ctx.author)
        return key.content.strip()

    try:
        async for (ann, dept_time) in player_main(station_name.title(), station_code, captcha_resolver=_captcha_handler):
            if songs.get(ctx.guild_id):
                songs[ctx.guild_id].extend([[str(ann), ctx.author.id, ctx.channel_id, dept_time]] * 2)
            else:
                songs[ctx.guild_id] = deque([[str(ann), ctx.author.id, ctx.channel_id, dept_time]] * 2)
            await ctx.respond("Queued! " + str(ann))
            if not voice_client.is_playing():
                await play_song(*(songs[ctx.guild_id].popleft()))
    except ETrainAPIError as e:
        await ctx.send(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    


@bot.command(aliases=["tts"])
async def text_to_speech(
    ctx: commands.Context, lang: Optional[str] = "en", *, text: str
):
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()
    tts_file = text_to_speech_recordings / text_to_speech_file_format.format(
        ctx.author, 0
    )
    tts_file = tts_file.with_suffix(".mp3")
    await ctx.send("Talking..")
    gtts.gTTS(text, lang=lang).save(str(tts_file))
    pydub.AudioSegment.from_mp3(tts_file).export(
        str(tts_file.with_suffix(".wav")), format="wav"
    )
    if not ctx.voice_client.is_playing():
        ctx.voice_client.play(discord.FFmpegPCMAudio(str(tts_file.with_suffix(".wav"))))
    await asyncio.sleep(20)
    # if tts_file.exists():
    #     tts_file.unlink()
    # if tts_file.with_suffix(".wav").exists():
    #     tts_file.with_suffix(".wav").unlink()



def song_completed(error):
    if error:
        raise error
    if songs.get(voice_client.guild.id):
        print("executing queue")
        dept_time: str | datetime.datetime
        wav_file, author_id, channel_id, dept_time = songs[voice_client.guild.id].popleft()
        print("Dept Time: ", dept_time)
        if type(dept_time) == str and dept_time == "Destination":
            bot.loop.create_task(play_song(wav_file, author_id, channel_id))
            return
        cur_time = datetime.datetime.now()
        while dept_time < cur_time:
            wav_file, author_id, channel_id, dept_time = songs[voice_client.guild.id].popleft()
        bot.loop.create_task(play_song(wav_file, author_id, channel_id))

# async def callback(sink: discord.sinks.Sink, channel_id, member_id, *args):
#     print("Recognising!")
#     channel = await bot.fetch_channel(channel_id)
#     # await channel.send("Recognizing your voice, please wait!")
#     try:
#         file = sink.audio_data[member_id].file
#     except KeyError:
#         return

#     stt_file = speech_recognition_recordings / speech_recognition_file_format.format(
#         member_id, 0
#     )
#     with open(stt_file, "wb") as f:
#         f.write(file.read())
#         file.seek(0)

#     if listening:
#         voice_client.start_recording(
#             ListenerSink(filters={"filtered_users": [member_id]}),
#             callback,
#             channel_id,
#             member_id,
#         )

#     with speech_recognition.AudioFile(str(stt_file)) as source:
#         sr_audio_data = recognizer.record(source)
#     await channel.send(
#         recognizer.recognize_google(sr_audio_data, show_all=True),
#         file=discord.File(file, filename="recording.wav"),
#     )
    # print(recognizer.)
    # if voice_client.is_playing():
    # while voice_client.is_playing():
    # await asyncio.sleep(0.5)
    # voice_client.play(discord.FFmpegPCMAudio(str(stt_file)))
    # await channel.send("I think this is right, maybe, \n Here's your Speech-To-Text \n")
    # message = "Is this right? {}".format(recognizer.recognize_google(sr_audio_data, language='en-US'))

    # tts_file = text_to_speech_recordings / text_to_speech_file_format.format(ctx.author, 0)

    # gtts.gTTS(message).save(str(tts_file))
    # await ctx.send("Talking!")
    # pydub.AudioSegment.from_mp3(tts_file).export(str(tts_file.with_suffix(".wav")), format="wav")
    # if not ctx.voice_client.is_playing():
    #     ctx.voice_client.play(discord.FFmpegPCMAudio(str(tts_file.with_suffix(".wav"))))
    # await asyncio.sleep(20)
    # if tts_file.exists():
    #     tts_file.unlink()
    # if tts_file.with_suffix(".wav").exists():
    #     tts_file.with_suffix(".wav").unlink()

    # for speech_recognition_recording in speech_recognition_recordings.iterdir():
    #     speech_recognition_recording.unlink()


# @tasks.loop(minutes=15)
# async def mp3_to_wav():

# @tasks.loop(seconds=20)
# async def get_audio(member_id, channel_id):
#     voice_client.start_recording(
#         discord.sinks.WaveSink(), callback, channel_id, member_id
#     )
#     await asyncio.sleep(17)
#     voice_client.stop_recording()
# filters={"time": timedelta(seconds=7).total_seconds(), "users": [member.id]}

# @tasks.loop(seconds=5)
# async def get_audio(member_id, channel_id):
#     while voice_client.recording:
#         await asyncio.sleep(0.5)
#     if not voice_client.recording:
#         voice_client.start_recording(
#             discord.sinks.WaveSink(), callback, channel_id, member_id
#         )
#     await asyncio.sleep(4.5)
#     if voice_client.recording:
#         voice_client.stop_recording()


bot.run(open(Path.cwd() / "login.txt").read())
