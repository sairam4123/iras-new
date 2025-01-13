# from typing import Callable
# import urllib.request
# import requests
# from bs4 import BeautifulSoup
# import bs4
# import pathlib
# import time
# import datetime
# import json
# import parsedatetime
# import random
# import urllib.parse
# import re
# from dataclasses import dataclass

# STATION_FILE = pathlib.Path("stations.json")
# TRAIN_FILE = pathlib.Path("trains.json")

# CACHE_FOLDER = pathlib.Path(".etrain-cache/")
# CACHE_FOLDER.mkdir(exist_ok=True)
# EXCLUDE_LOCAL = True
# EXCLUDE_MEMU = True
# EXCLUDE_FAST_EMU = True

# LIMIT = 7
# STATION_CODE = "TBM"




# ETRAIN_PHPCOOKIE = "g33h289msoqjaa5mm9i40dn56r"
# REQID = 0
# sess = requests.Session()
# res = sess.post(
#     "https://etrain.info/ajax.php?q=larrdep&v=3.4.10",
#     headers={
#         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
#         "Host": "etrain.info",
#         "Origin": "https://etrain.info",
#         "Referer": "https://etrain.info/station/Chennai-Egmore-MS/live",
#     },
#     files={
#         "stn": (None, STATION_CODE),
#         "reqID": (None, REQID),
#         "reqCount": (None, 1),
#     },
#     cookies={"PHPSESSID": ETRAIN_PHPCOOKIE},
# )
# REQID += 1
# if "captcha" in res.json().get("sscript", ""):
#     print("handle captcha")
#     code = res.json().get("sscript")
#     captcha_soup = BeautifulSoup(res.json().get("sscript"), "html.parser")
#     image = captcha_soup.find("img", attrs={"class": "captchaimage"})
#     print(image)
#     captcha_btns = captcha_soup.find_all("a", attrs={"class": "capblock"})
#     for captcha_btn in captcha_btns:
#         captcha_btn: bs4.PageElement
#         print(captcha_btn.get_text())
#     res = sess.get("https://etrain.info" + image.attrs["src"])
#     import re

#     match = re.search(r"sD\s*=\s*'([^']+)'", code)
#     if match:
#         sD_value = match.group(1)
#         print("sD:", sD_value)
#         pathlib.Path(CACHE_FOLDER / sD_value.replace(".", "_")).with_suffix(
#             ".png"
#         ).write_bytes(res.content)
#     else:
#         print("sD not found")
#     # captchaImage = res.json().get('sscript')[inx:]
#     # print(captchaImage)
#     exit()
# print("Fetching station arrivals and departures for TBM.")
# data = []
# tr_idx = 0
# soup = BeautifulSoup(res.json()["data"], "html.parser")
# for tr in soup.findAll("tr"):
#     if tr_idx >= LIMIT:
#         break
#     tr: bs4.PageElement
#     datum = tr.get_text(" ; ").split(" ; ")
#     datum = {
#         "train_no": datum[0],
#         "train_name": datum[1],
#         "src": datum[2],
#         "dest": datum[3],
#         "tt_arr": datum[4],
#         "tt_dept": datum[5],
#         "tt_pf": datum[6],
#         "tt_halt": datum[7],
#         "exp_arr": datum[8],
#         "exp_arr_delay": datum[9],
#         "exp_dept": datum[10],
#         "exp_dept_delay": datum[11],
#     }
#     if EXCLUDE_LOCAL and "EMU" in datum["train_name"]:
#         continue
#     res = sess.post(
#         "https://etrain.info/ajax.php?q=runningstatus&v=3.4.10",
#         headers={
#             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
#             "Host": "etrain.info",
#             "Origin": "https://etrain.info",
#             "Referer": f"https://etrain.info/train/{datum['train_name']}-{datum['train_no']}/schedule",
#         },
#         files={
#             # "page": (None, f"train/{datum['train_name']}-{datum['train_no']}/schedule"),
#             "final": (None, "1"),
#             "atstn": (None, datum["src"]),
#             "train": (None, datum["train_no"]),
#             "date": (None, "16-07-2024"),
#             "reqID": (None, REQID),
#             "reqCount": (None, 1),
#         },
#         cookies={"PHPSESSID": ETRAIN_PHPCOOKIE},
#     )
#     # print(res.content)
#     REQID += 1
#     resp = res.json()
#     # print(resp)

#     if "error" in resp:
#         continue
#     train_soup = BeautifulSoup(res.json()["data"], "html.parser")
#     table_rows = (
#         train_soup.find(id="sublowerdata")
#         .find("table")
#         .find_next_sibling("table")
#         .find_all("tr", attrs={"class": ["odd", "even"]})
#     )
#     # print(table_rows)
#     # # pathlib.Path("out.html").write_bytes(train_soup.prettify(encoding='utf-16'))
#     # table_rows = train_soup.find_all(attrs={"class": "rake"})
#     # # table_rows = train_soup.find(id="sublowerdata").find("table").find_all("tr")
#     # print(table_rows)
#     stns = []
#     for table_row in table_rows:
#         table_row: bs4.PageElement
#         running_stn_info = [
#             x.strip()
#             for x in table_row.get_text(" ; ").split(" ; ")
#             if not (x.isspace() or x.startswith("+ "))
#         ]
#         pf = running_stn_info[3].split(":")[1].strip()
#         scheduled_arr, actual_arr, scheduled_dept, actual_dept = (
#             parse_running_status_arr_dep(running_stn_info[6:])
#         )
#         stn = {
#             "index": running_stn_info[0],
#             "name": running_stn_info[1],
#             "s_dist": running_stn_info[2],
#             "pf": running_stn_info[3],
#             "tt_arr": scheduled_arr,
#             "act_arr": actual_arr,
#             "tt_dept": scheduled_dept,
#             "act_dept": actual_dept,
#         }
#         stns.append(stn)
#     break
#     # sta_info = [
#     #     x.strip()
#     #     for x in table_row.get_text(" ; ").split(" ; ")
#     #     if not str(x).isspace()
#     # ]
#     # dist = sta_info[3].split(" ")[0].strip()
#     # pf = sta_info[4].split(": ")[1].strip()
#     # arr, a_day = parse_schedule(sta_info[7])
#     # dept, d_day = parse_schedule(sta_info[8])

#     # station = {
#     #     "index": sta_info[0],
#     #     "code": sta_info[1],
#     #     "name": sta_info[2],
#     #     "dist": dist,
#     #     "pf": pf,
#     #     "a": arr,
#     #     "d": dept,
#     #     "a_day": a_day,
#     #     "d_day": d_day,
#     #     "day": d_day,  # FIXME: Remove: Prevent breaking changes..
#     # }

#     sleep_time = random.uniform(-0.5, 1.5)
#     print(f"Sleeping for {1+ sleep_time:.2f} secs")
#     time.sleep(1 + sleep_time)
#     # datum["route"] = staData
#     # data.append(datum)
#     tr_idx += 1

#     # tinfo = [
#     #     x
#     #     for x in train_soup.find(id="sublowerdata")
#     #     .get_text(" ; ")
#     #     .replace("\n", "")
#     #     .split(" ; ")
#     #     if x and x != "\xa0"
#     # ]
#     # staIndex = 1
#     # staData = []
#     # stationData = {}
#     # foundData = False
#     # s_members = ["code", "name", "dist", "pf", "a", "d"]
#     # s_member_index = 0
#     # print(f"Fetching train details for {datum['train_name']} {datum['train_no']}")
#     # for current_index, info in enumerate(tinfo):
#     #     try:
#     #         testIndex = int(info)
#     #     except ValueError:
#     #         if not foundData:
#     #             continue
#     #         testIndex = -1
#     #     if info == "Legends:":
#     #         break
#     #     if testIndex == staIndex:
#     #         foundData = True
#     #         stationData["index"] = testIndex
#     #         continue
#     #     if foundData:
#     #         if info == "A" or info == "D":
#     #             continue
#     #         match s_members[s_member_index]:
#     #             case "dist":
#     #                 info = info.split(" ")[0].strip()
#     #             case "pf":
#     #                 info = info.split(": ")[1].strip()
#     #             case "a":
#     #                 if info.lower().startswith("source"):
#     #                     info = "Source"
#     #                 else:
#     #                     stationData["day"] = info.split(" ")[2].strip(")")
#     #                     info = info.split(" ")[
#     #                         0
#     #                     ]  # datetime.datetime.strptime(info.split(" ")[0], "%H:%M")
#     #             case "d":
#     #                 if info.lower().startswith("dest"):
#     #                     info = "Destination"
#     #                 else:
#     #                     stationData["day"] = info.split(" ")[2].strip(")")
#     #                     info = info.split(" ")[
#     #                         0
#     #                     ]  # datetime.datetime.strptime(info.split(" ")[0], "%H:%M")

#     #         stationData[s_members[s_member_index]] = info
#     #         s_member_index += 1
#     #         if s_member_index > len(s_members) - 1:
#     #             s_member_index = 0
#     #             staIndex += 1

#     #             staData.append(stationData.copy())
#     #         continue
# # cur_stations = {}
# # cur_trains = {}

# # if STATION_FILE.exists():
# #     cur_stations = json.loads(STATION_FILE.read_text())
# # else:
# #     STATION_FILE.write_text(json.dumps(cur_stations))
# # if TRAIN_FILE.exists():
# #     cur_trains = json.loads(TRAIN_FILE.read_text())
# # else:
# #     TRAIN_FILE.write_text(json.dumps(cur_trains))

# # for datum in data:
# #     for station in datum["route"]:
# #         cur_stations[station["code"]] = {
# #             "name": station["name"],
# #             "code": station["code"],
# #         }
# #     cur_trains[datum["train_no"]] = {
# #         "train_no": datum["train_no"],
# #         "train_name": datum["train_name"],
# #         "src": datum["src"],
# #         "dest": datum["dest"],
# #         "route": datum["route"],
# #     }

# # STATION_FILE.write_text(json.dumps(cur_stations, indent=4))
# # TRAIN_FILE.write_text(json.dumps(cur_trains, indent=4))

# # pathlib.Path("data.json").write_text(json.dumps(data, indent=4))

# # res = sess.post(
# #     "https://enquiry.indianrail.gov.in/mntes/q?opt=LiveStation&subOpt=show",
# #     files={
# #         "lan": (None, "en"),
# #         "jFromStationInput": (None, "CHENNAI EGMORE - MS"),
# #         "jToStationInput": (None, ""),
# #         "nHr": (None, 2),
# #         "appLang": (None, "en"),
# #         "jStnName": (None, ""),
# #         "jStation": (None, ""),
# #     },

# # )

# # # print(requests.post("https://enquiry.indianrail.gov.in/TSPD/?type=17").content)


# # # print(res.content)
# # # IDE	AHWqTUlF0r04si-iXvJdSqJiJ31z8VhYs1FHg_JiSEgZ2ejgG3Bj-BrKUdtv3iIgSGA	.doubleclick.net	/	2025-07-21T08:57:29.246Z	70	✓	✓	None		Medium
# # # JSESSIONID	"nJIsSTn_eRg4oZWxNZIEPkVZOXTucSybajF7UndD.ntes_host1:host1_server1"	enquiry.indianrail.gov.in	/mntes	Session	77	✓	✓			Medium
# # # SERVERID	cch7fw87sfs2	enquiry.indianrail.gov.in	/	Session	20					Medium
# # # TS00000000076	0801361661ab28000243364127087fbe8ca67c2e965c582787de285e415dfa6d9aea56e40d7c38ef41e2d3c9cb29539608506543ea09d000952135bb9ead79aefb1074656b7c5a15f9a3b6a4d610e7ef918b70277d161d3991c10125400c6ab5d1d59c2f04aa77ccb37e3e0b6a92cf15984937c712a5f5e386338223784aff9f1ce0823fd52c161efd08e9690f2be0d0a523b35db9b782b4896846e19a968d8cadc5cf25fc7a79b033ccb410f5693a17fd7321329a56ba2924b0b98b74964348ab2fbbdfac138444c45bd1562c95747e5d870e384490e4a296de9418be92272c545d251b79b5afe8ad54ea66c7ae26fecc2df6dfcc7b9ee0b46f3e4aff35f4b7dab33533cbe2c34d	enquiry.indianrail.gov.in	/	Session	541					Medium
# # # TS0109848f	01ea7166bcffe8fd5671da2c945d19c011df84d1303c9d7efc1837a47b7af537aecf6fa649b49c9444368298d471e3d7aa1ca23157	.enquiry.indianrail.gov.in	/	Session	116					Medium
# # # TS0147a324	01ea7166bc156224b6cbf8ec7692822cb3ef20d215564106528040d4332d95f51340ab6d44f5a7c0ade83f2e43a9ddf5b2d0d9fd92	enquiry.indianrail.gov.in	/mntes	Session	116					Medium
# # # TS78efcf45077	0801361661ab2800a35aca21d0a3d7a5ec5561195ecbbd41b21a6055d4b7062e8844057bab0b96faeb952154339a6db208823b087a17200082a5b71cf290ce35eefe42336597c47c7a5ec2e7a37945421e2b2708f82a3927	enquiry.indianrail.gov.in	/	Session	189					Medium
# # # TSPD_101	0801361661ab2800297668192d845ac74315f187095098b7838b4751f6fa636b0d52e1dd4e5f687fdf1c801edf2078dc0876c668630518009fce254a7ddb7f4f48f184f632510b9f9a655ddb7b1a8054	enquiry.indianrail.gov.in	/	Session	168					Medium
# # # TSPD_101_DID	0801361661ab28000243364127087fbe8ca67c2e965c582787de285e415dfa6d9aea56e40d7c38ef41e2d3c9cb29539608506543ea0638009b8944d09a90f63d220e98d225f48e5e5f5e4dbd1158e41d283fa753b01fc8cd5886a9dfedf05296d81a9a5e1cf9a82bdd52d62e0f9bc157	enquiry.indianrail.gov.in	/	Session	236					Medium
# # # TSe2af6b11027	0801361661ab200082f44e521515b7a9aa56551705eee97f38aefb3238c6a11e7c872001af8524f6082980d3d01130004c73574f7f8bae337516b7b2ed3b2f375b8f735debce0ba96696e95628ab36f96355e77d784269fee53831adc0647b7a	enquiry.indianrail.gov.in	/	Session	205					Medium
# # # __stripe_mid	faf37191-127c-4e9a-8ec4-71af5c56e116149b6b	.fontawesome.com	/	2025-05-09T13:40:23.000Z	54		✓	Strict		Medium
# # # ph_phc_vqJhC8Gur3e5hySKKsNdlhHsHeDna2K1fxalCezayql_posthog	%7B%22distinct_id%22%3A%22018dd4cf-3019-7f46-8551-f48246fce75c%22%2C%22%24device_id%22%3A%22018dd4cf-3019-7f46-8551-f48246fce75c%22%2C%22%24user_state%22%3A%22anonymous%22%2C%22%24session_recording_enabled_server_side%22%3Afalse%2C%22%24autocapture_disabled_server_side%22%3Atrue%2C%22%24active_feature_flags%22%3A%5B%22plans-page-showing-pro-lite%22%2C%22skip-pro-modal-go-to-plans-pro%22%2C%22direct-to-pro-plan%22%2C%22plans-cta-above-fold%22%2C%22icon-details-layout-and-checkout%22%2C%22icon-details-layout-test%22%5D%2C%22%24enabled_feature_flags%22%3A%7B%22plans-page-showing-pro-lite%22%3A%22pro-lite%22%2C%22skip-pro-modal-go-to-plans-pro%22%3A%22skip-modal%22%2C%22direct-to-pro-plan%22%3A%22control%22%2C%22plans-cta-above-fold%22%3A%22control%22%2C%22icon-details-layout-and-checkout%22%3A%22new-icons-details-layout-ckout%22%2C%22icon-details-layout-test%22%3A%22new-icons-details-layout%22%7D%2C%22%24feature_flag_payloads%22%3A%7B%7D%2C%22%24sesid%22%3A%5B1715262018675%2C%22018f5d95-…	.fontawesome.com	/	2025-05-09T13:40:19.000Z	1328		✓	Lax		Medium
# # from selenium import webdriver
# # from selenium.webdriver.common.by import By
# # from selenium.webdriver.edge.service import Service as EdgeService
# # from selenium.webdriver.edge.options import Options
# # # from webdriver_manager.microsoft import EdgeChromiumDriverManager

# # options = Options()
# # options.add_argument("--headless")
# # options.add_argument("--disable-gpu")

# # # service = EdgeService(EdgeChromiumDriverManager().install())
# # # driver = webdriver.Edge(service=service, options=options)
# # driver = webdriver.Edge(options=options)

# # url = "https://enquiry.indianrail.gov.in/mntes/"

# # driver.get(url)

# # driver.implicitly_wait(10)  # Wait for 10 seconds

# # page_content = driver.page_source

# # driver.quit()

# # print(page_content)

import datetime
from etrainlib import ETrainAPISync, ETrainArrivalDepartureConfig, default_captcha_handler, async_default_captcha_resolver
from etrainlib._async import ETrainAPIAsync
import asyncio

from etrainlib.constants import ETrainAllTrainsConfig

async def run():
    async with ETrainAPIAsync(captcha_resolver=async_default_captcha_resolver) as e:
        print(await e.get_live_station("TBM", 'Tambaram'))
        # trains = await e.get_all_trains("PDKT", "Pudukkottai", ETrainAllTrainsConfig(limit=100, weekday=(datetime.datetime.now().weekday() + 1) % 7 ))
        # for train in trains:
        #     print(train)

    # print(e.get_coach_positions("12605", "Pallavan Exp"))
    # print(e.get_train_schedule("12605", "Pallavan Exp"))
    # print(e.get_running_status("12605", "Pallavan Exp", datetime.date.today(), "MS"))


asyncio.run(run())