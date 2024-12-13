from ._sync import ETrainAPI, ETrainAPIError, ETrainArrivalDepartureConfig, CACHE_FOLDER
import asyncio


def default_captcha_handler(sd: str, keys: list[str], error: str, file: str) -> str:
    key = input(
        f"{error} Look for the image in .etrain-cache folder with name: {sd.replace('.', '_')}: \nPossible keys are: {keys}\n> "
    )
    return key.strip()

async def async_default_captcha_resolver(sd: str, keys: list[str], error: str, file: str) -> str:
    return await asyncio.get_event_loop().run_in_executor(None, default_captcha_handler, sd, keys, error, file)