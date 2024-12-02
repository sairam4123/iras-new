import datetime
import re
from typing import Callable
import aiohttp
from aiohttp import ClientResponse as Response
import bs4
from .constants import API_VERSION, BASE_API, BASE_URL, CACHE_FOLDER, COMMON_HEADERS, AUTH_CACHE, ETrainAPIError, ETrainAllTrainsConfig, ETrainArrivalDepartureConfig, build_formdata, build_url, decode_hash
from .parser import ETrainParser
import json

class ETrainAPIAsync:
    def __init__(self, phpcookie=None, captcha_resolver: Callable[[str, list[str]], str] = None):
        self.req_id = 0
        self.req_count = {}
        if AUTH_CACHE.exists():
            self._phpcookie = phpcookie or AUTH_CACHE.read_text()
        else:
            self._phpcookie = phpcookie
        self.session = aiohttp.ClientSession()
        self.session.headers.update(COMMON_HEADERS)
        self.session.cookie_jar.update_cookies({"PHPSESSID": self._phpcookie})
        self.captcha_handler = captcha_resolver
        self.parser = ETrainParser()
    
    def _get_request_info(self, query):
        # if query["q"] not in self.req_count:
        #     self.req_count[query["q"]] = 1
        return {"reqID": self.req_id, "reqCount": 1}

    def _increment_request_info(self, query):
        self.req_id += 1
        # self.req_count[query["q"]] += 1
    
    async def _request(self, path: str = None, query: dict=None, form_data: dict=None):
        query = query or {}
        form_data = form_data or {}
        print("DEBUG: Requesting", path)
        async with self.session.post(
            url=build_url(BASE_API, path="ajax.php", query_dict=query | {"v": API_VERSION}),
            data=build_formdata(form_data | self._get_request_info(query)),
            headers={"Referer": build_url(BASE_URL, path=path)},
        ) as res:
            res: Response
            print("DEBUG: Response", res.status, res.url)
            self._increment_request_info(query)
            try:
                json: dict = await res.json(content_type="text/html")
            except (ValueError, Exception) as e:
                raise e
            else:
                if "captcha" in json.get("sscript", {}):
                    curr_cookie = res.cookies.get("PHPSESSID")
                    if curr_cookie != self._phpcookie:
                        self._phpcookie = curr_cookie.coded_value
                        self.session.cookie_jar.update_cookies({"PHPSESSID": self._phpcookie})
                    print("DEBUG: Setting new session token")
                    if await self.request_new_token(json):
                        return await self._request(path, query, form_data)
                if "error" in json:
                    raise ETrainAPIError(json["error"])
            return json
    
    async def request_new_token(self, json_resp):
        code = json_resp.get("sscript")

        captcha_soup = bs4.BeautifulSoup(code, "html.parser")
        image = captcha_soup.find("img", attrs={"class": "captchaimage"})

        async with self.session.get(BASE_URL + image.attrs["src"]) as res:
            res: Response
            if res.status != 200:
                raise ETrainAPIError("failed to fetch captcha image")
            
            match = re.search(r"sD\s*=\s*'([^']+)'", code)
            if not match:
                raise ETrainAPIError("invalid captcha")

            encoded_hash = match.group(1)
            cache_file = f"{encoded_hash.replace('.', '_')}.png"
            (CACHE_FOLDER / cache_file).write_bytes(await res.read())

        captcha_btns = captcha_soup.find_all("a", attrs={"class": "capblock"})
        keys = [captcha.get_text() for captcha in captcha_btns]

        key = await self.captcha_handler(encoded_hash, keys)
        index = keys.index(key)

        decoded_hash = decode_hash(encoded_hash, index)

        new_json_resp = await self._request(
            "",
            {"q": "captcha"},
            form_data={"ctext": "", "captcha-code": key, "captcha-text": decoded_hash},
        )

        return new_json_resp["data"] == "1"

    async def get_live_station(
        self,
        stn_code: str,
        stn_name: str,
        config: ETrainArrivalDepartureConfig = ETrainArrivalDepartureConfig(),
    ):
        json_resp = await self._request(
            f"/station/{stn_name.replace(' ', '-')}-{stn_code.upper()}/live",
            query={"q": "larrdep"},
            form_data={"stn": stn_code.upper()},
        )
        return self.parser._parse_larrdep_data(json_resp, config)

    async def get_train_schedule(self, train_no: str, train_name: str):
        page = f"/train/{train_name}-{train_no}/schedule"
        json_resp = await self._request(
            page, query={"q": "page"}, form_data={"page": page}
        )  # Request page
        return self.parser._parse_train_schedule_info(json_resp)

    async def get_coach_positions(self, train_no: str, train_name: str):
        page = f"/train/{train_name}-{train_no}/schedule"
        json_resp = await self._request(
            page, query={"q": "page"}, form_data={"page": page}
        )  # Request page
        return self.parser._parse_coach_position(json_resp)
    
    async def get_all_trains(self, stn_code: str, stn_name: str, config: ETrainAllTrainsConfig = ETrainAllTrainsConfig()):
        json_resp = await self._request(
            f"/station/{stn_name.replace(' ', '-')}-{stn_code.upper()}/all",
            query={"q": "page"},
            form_data={"page": f"/station/{stn_name.replace(' ', '-')}-{stn_code.upper()}/all"},
        )
        return self.parser._parse_all_trains_data(json_resp, config)


    async def get_running_status(
        self, train_no: str, train_name: str, date: datetime.date, src_stn_code: str
    ):
        page = f"/train/{train_name}-{train_no}/live"
        json_resp = await self._request(
            page,
            query={"q": "runningstatus"},
            form_data={
                "train": train_no,
                "final": 1,
                "atstn": src_stn_code,
                "date": date.strftime("%d-%m-%Y"),
            },
        )
        return self.parser._parse_running_status_data(json_resp)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        AUTH_CACHE.write_text(self._phpcookie)
        await self.session.close()

