import base64
from io import BytesIO
import json
import os
import random
from typing import Literal
import google.cloud.texttospeech as tts

def get_service_account_info() -> dict:
    res = base64.b64decode(os.environ["GEN_LANG_JSON_KEY"]).decode("utf-8")
    res = json.loads(res)
    return res

def get_service_account_info_path() -> dict:
    path = os.path.join(os.getcwd(), "gen-lang-client.json")
    with open(path, "r") as f:
        return json.load(f)

def get_speech_client() -> tts.TextToSpeechClient:
    tts_client: tts.TextToSpeechClient = tts.TextToSpeechClient.from_service_account_info(
        get_service_account_info_path()
    )
    return tts_client

VOICE_MODEL = 'Chirp3'

def select_voice_people(lang: str) -> dict[str, tts.Voice]:

    # speech_client = tts.TextToSpeechClient.from_service_account_json(os.environ["GEN_LANG_JSON"])
    speech_client = get_speech_client()

    voices = {}
    # used_voices = set()

    all_voices = speech_client.list_voices(tts.ListVoicesRequest(language_code=lang))
    listed_voices = [voice for voice in all_voices.voices if VOICE_MODEL in voice.name]

    gender_voices: dict[Literal["male"] | Literal["female"] | Literal["neutral"], list[tts.Voice]] = {
        "male": [],
        "female": [],
        "neutral": [],
    }

    for voice in listed_voices:
        gender = tts.SsmlVoiceGender(voice.ssml_gender).name.lower()
        if gender in gender_voices:
            gender_voices[gender] += [voice]
    
    person = {
        "id": "announcer",
        "gender": "female",
    }


    person_gender = "female"
    if (person_gender not in ["male", "female", "neutral"]):
        raise ValueError(f"Invalid {person_gender} is generated.")
    
    # contains only partial name matches so that we can avoid certain voices
    ignored_voices = ['Pulcherrima']

    available = [v for v in gender_voices.get(person_gender if person_gender in gender_voices else "neutral", [])]
    available = [v for v in available if all(ign not in v.name for ign in ignored_voices)]

    if not available:
        raise ValueError(f"No available voices left for gender: {person['gender']}")

    # voice = available[0] # always choose first one (deterministic)
    voice = random.choice(available)
    voices[person['id']] = voice
    # used_voices.add(voice.name)
    print(f"Selected voice: {voice.name} for {person['id']} ({person['gender']})")
    return voices

def t2s(text: str, out_fp: BytesIO, lang: str = "en-IN"):
    speech_client = get_speech_client()
    voices = select_voice_people(lang)
    voice = voices["announcer"]

    synthesis_input = tts.SynthesisInput(text=text)

    voice_params = tts.VoiceSelectionParams(
        language_code=lang,
        name=voice.name,
        ssml_gender=voice.ssml_gender
    )

    audio_config = tts.AudioConfig(
        audio_encoding=tts.AudioEncoding.MP3
    )

    response = speech_client.synthesize_speech(
        input=synthesis_input,
        voice=voice_params,
        audio_config=audio_config
    )

    out_fp.write(response.audio_content)