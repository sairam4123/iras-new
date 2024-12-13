import re
import datetime
from typing import Callable

import requests
from bs4 import BeautifulSoup
from etrainlib.constants import (
    BASE_API,
    BASE_URL,
    AUTH_CACHE,
    CAPTCHA_FOLDER,
    COMMON_HEADERS,
    API_VERSION,
    CACHE_FOLDER,
    ETrainAPIError,
    ETrainArrivalDepartureConfig,
    build_formdata,
    build_url,
    decode_hash,
)
from etrainlib.parser import ETrainParser

__all__ = ["ETrainAPI", "ETrainAPIError", "ETrainArrivalDepartureConfig", "CACHE_FOLDER"]




class ETrainAPI:
    def __init__(self, phpcookie=None, captcha_handler: Callable[[str, list[str], str, str], str] = None):
        self.req_id = 0
        self.req_count = {}
        if AUTH_CACHE.exists():
            self._phpcookie = phpcookie or AUTH_CACHE.read_text()
        else:
            self._phpcookie = phpcookie
        self.session = requests.session()
        self.session.headers = COMMON_HEADERS
        self.session.cookies.set("PHPSESSID", self._phpcookie)
        self.captcha_handler = captcha_handler
        self.parser = ETrainParser()

    def _request(self, path: str, query={}, form_data={}):
        res = self.session.post(
            build_url(BASE_API, path="ajax.php", query_dict=query | {"v": API_VERSION}),
            files=build_formdata(form_data | self._get_request_info(query)),
            headers={"Referer": build_url(BASE_URL, path=path)},
        )
        self._increment_request_info(query)
        try:
            json = res.json()
        except (ValueError, Exception) as e:
            print("Unexpected error:", e)
            return None
        else:
            if "captcha" in json.get("sscript", {}):
                curr_cookie = res.cookies.get("PHPSESSID")
                if curr_cookie != self._phpcookie:
                    self._phpcookie = curr_cookie
                    self.session.cookies.set("PHPSESSID", self._phpcookie)
                print("DEBUG: Setting new session token.")
                if self.request_new_token(json):
                    return self._request(path, query, form_data)
            if "error" in json:
                raise ETrainAPIError(json["error"])
        return json

    @property
    def session_cookie(self):
        return self._phpcookie

    def _get_request_info(self, query):
        if query["q"] not in self.req_count:
            self.req_count[query["q"]] = 1
        return {"reqID": self.req_id, "reqCount": self.req_count[query["q"]]}

    def _increment_request_info(self, query):
        self.req_id += 1
        self.req_count[query["q"]] += 1

    def request_new_token(self, json_resp):
        code = json_resp.get("sscript")

        captcha_soup = BeautifulSoup(code, "html.parser")
        image = captcha_soup.find("img", attrs={"class": "captchaimage"})
        error = captcha_soup.find("span", attrs={"id": "captchaformerrormsg"}).get_text()

        res = self.session.get(BASE_URL + image.attrs["src"])

        match = re.search(r"sD\s*=\s*'([^']+)'", code)
        if not match:
            raise ETrainAPIError("invalid captcha")

        encoded_hash = match.group(1)
        cache_file = f"{encoded_hash.replace('.', '_')}.png"
        (CAPTCHA_FOLDER / cache_file).write_bytes(res.content)
        captcha_btns = captcha_soup.find_all("a", attrs={"class": "capblock"})
        keys = [captcha.get_text() for captcha in captcha_btns]
        key = self.captcha_handler(encoded_hash, keys, error, str(CAPTCHA_FOLDER / cache_file))
        index = keys.index(key)
        decoded_hash = decode_hash(encoded_hash, index)

        new_json_resp = self._request(
            "",
            {"q": "captcha"},
            form_data={"ctext": "", "captcha-code": key, "captcha-text": decoded_hash},
        )

        return new_json_resp["data"] == "1"

    def get_live_station(
        self,
        stn_code: str,
        stn_name: str,
        config: ETrainArrivalDepartureConfig = ETrainArrivalDepartureConfig(),
    ):
        json_resp = self._request(
            f"/station/{stn_name.replace(' ', '-')}-{stn_code.upper()}/live",
            query={"q": "larrdep"},
            form_data={"stn": stn_code.upper()},
        )
        return self.parser._parse_larrdep_data(json_resp, config)

    def get_train_schedule(self, train_no: str, train_name: str):
        page = f"/train/{train_name}-{train_no}/schedule"
        json_resp = self._request(
            page, query={"q": "page"}, form_data={"page": page}
        )  # Request page
        return self.parser._parse_train_schedule_info(json_resp)

    def get_coach_positions(self, train_no: str, train_name: str):
        page = f"/train/{train_name}-{train_no}/schedule"
        json_resp = self._request(
            page, query={"q": "page"}, form_data={"page": page}
        )  # Request page
        return self.parser._parse_coach_position(json_resp)


    def get_running_status(
        self, train_no: str, train_name: str, date: datetime.date, src_stn_code: str
    ):
        page = f"/train/{train_name}-{train_no}/live"
        json_resp = self._request(
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

    def close(self):
        self.session.close()

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        AUTH_CACHE.write_text(self.session_cookie)
        self.close()
        return
