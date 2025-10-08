import datetime
from pathlib import Path

import bs4
import parsedatetime

from etrainlib.constants import CACHE_FOLDER, ETrainAllTrainsConfig, ETrainArrivalDepartureConfig

def parse_schedule(dt):
    day = dt.split(" ")[2].strip(")")
    if dt.lower().startswith("source"):
        return "Source", day
    elif dt.lower().startswith("dest"):
        return "Destination", day
    _time = dt.split(" ")[0]
    return _time, day


def parse_running_status_arr_dep(sta_entry_arr_dep):
    scheduled_arr, actual_arr = None, None
    scheduled_dept, actual_dept = None, None
    arr = sta_entry_arr_dep[0]
    if arr.lower().startswith("source"):
        scheduled_arr, actual_arr = parse_running_status(arr)
    elif arr.lower().startswith(("diverted", "cancel")):
        pass  # FIXME: we handle this later.
    else:
        arr = sta_entry_arr_dep[0:3]
        scheduled_arr, actual_arr = parse_running_status(*arr)
    if isinstance(scheduled_arr, str) and scheduled_arr.lower().startswith("source"):
        dept = sta_entry_arr_dep[1:4]
        scheduled_dept, actual_dept = parse_running_status(*dept)
    else:
        dept = sta_entry_arr_dep[3]
        if dept.lower().startswith("dest"):
            scheduled_dept, actual_dept = parse_running_status(dept)
        elif dept.lower().startswith(("diverted", "cancel")):
            pass  # FIXME: we handle this later,
        else:
            dept = sta_entry_arr_dep[3:6]
            scheduled_dept, actual_dept = parse_running_status(*dept)

    return scheduled_arr, actual_arr, scheduled_dept, actual_dept


def parse_running_status(dt, year=None, delay=None):
    if dt.lower().startswith("source") and year is None and delay is None:
        return "Source", "N/A"
    if dt.lower().startswith("dest") and year is None and delay is None:
        return "Destination", "N/A"
    _time = datetime.datetime.strptime(f"{dt}, {year}", "%H:%M, %d %b, %Y")
    if delay:
        if delay == "(RT)":
            return _time, _time
        else:
            return _time, parse_time_delta(delay, _time)
    return None, None


def parse_time_delta(delay, src=datetime.datetime.now()):
    cal = parsedatetime.Calendar()

    actual, _ = cal.parseDT(delay, sourceTime=src)
    return actual


class ETrainParser:
    @staticmethod
    def _parse_larrdep_data(json_resp, config: ETrainArrivalDepartureConfig):
        soup = bs4.BeautifulSoup(json_resp["data"], "html.parser")
        parsed_trains = []
        for table_row in soup.findAll("tr"):
            table_row: bs4.PageElement
            train_info = table_row.find_all_next("td")
            train_info = [x.get_text().strip() for x in train_info]
            print("DEBUG:", train_info)
            train_info = {
                "train_no": train_info[0],
                "train_name": train_info[1],
                "src": train_info[2],
                "dest": train_info[3],
                "tt_arr": train_info[4],
                "tt_dept": train_info[5],
                "tt_pf": train_info[6],
                "tt_halt": train_info[7],
                "exp_arr": train_info[8],
                "exp_arr_delay": train_info[9],
                "exp_dept": train_info[10],
                "exp_dept_delay": train_info[11],
            }
            if config.exclude_local and "LOCAL" in train_info["train_name"]:
                continue
            if config.exclude_memu and "MEMU" in train_info["train_name"]:
                continue
            if config.exclude_fast_emu and "FAST EMU" in train_info["train_name"]:
                continue
            if config.exclude_parcel_services and "JPP" in train_info["train_name"]:
                continue
            parsed_trains.append(train_info)
        return parsed_trains[: config.limit]

    @staticmethod
    def _parse_train_schedule_info(json_resp):
        train_soup = bs4.BeautifulSoup(json_resp["data"]["ldata"], "html.parser")
        table_rows = train_soup.find(id="sublowerdata").find("table").find_all("tr")

        stations = []
        for table_row in table_rows[1:]:
            table_row: bs4.PageElement
            sta_info = [
                x.strip()
                for x in table_row.get_text(" ; ").split(" ; ")
                if not str(x).isspace()
            ]
            dist = sta_info[3].split(" ")[0].strip()
            pf = sta_info[4].split(":")[1].strip()
            arr, a_day = parse_schedule(sta_info[7])
            dept, d_day = parse_schedule(sta_info[8])

            station = {
                "index": sta_info[0],
                "code": sta_info[1],
                "name": sta_info[2],
                "dist": dist,
                "pf": pf,
                "a": arr,
                "d": dept,
                "a_day": a_day,
                "d_day": d_day,
            }
            stations.append(station)
        return stations

    @staticmethod
    def _parse_coach_position(json_resp):
        train_soup = bs4.BeautifulSoup(json_resp["data"]["ldata"], "html.parser")
        table_rows = train_soup.find_all(attrs={"class": "rake"})
        positions = {}
        for table_row in table_rows[1:]:
            table_row: bs4.PageElement
            coach_pos = table_row.find_parent().get_text(" ; ").split(" ; ")
            positions[coach_pos[0]] = coach_pos[1]
        return positions
    
    @staticmethod
    def _parse_running_status_data(json_resp):
        train_soup = bs4.BeautifulSoup(json_resp["data"], "html.parser")
        table_rows = (
            train_soup.find(id="sublowerdata")
            .find("table")
            .find_next_sibling("table")
            .find_all("tr", attrs={"class": ["odd", "even"]})
        )
        stns = []
        for table_row in table_rows:
            table_row: bs4.PageElement
            running_stn_info = [
                x.strip()
                for x in table_row.get_text(" ; ").split(" ; ")
                if not (x.isspace() or x.startswith("+ "))
            ]
            pf = running_stn_info[3].split(":")[1].strip()
            scheduled_arr, actual_arr, scheduled_dept, actual_dept = (
                parse_running_status_arr_dep(running_stn_info[6:])
            )
            stn = {
                "index": running_stn_info[0],
                "name": running_stn_info[1],
                "s_dist": running_stn_info[2],
                "pf": pf,
                "tt_arr": scheduled_arr,
                "act_arr": actual_arr,
                "tt_dept": scheduled_dept,
                "act_dept": actual_dept,
            }
            stns.append(stn)
        return stns
    
    @staticmethod
    def _parse_all_trains_data(json_resp, config: ETrainAllTrainsConfig):
        soup = bs4.BeautifulSoup(json_resp["data"]["udata"], "html.parser")
        parsed_trains = []
        trows = soup.find(attrs={"class": "trainlist"}).find_all("tr")
        for table_row in trows:
            table_row: bs4.PageElement
            
            if len(parsed_trains) >= config.limit:
                break

            train_info = table_row.get_text(" ; ").split(" ; ")
            train_info = {
                "train_no": train_info[0],
                "train_name": train_info[1],
                "src": train_info[2],
                "dest": train_info[3],
                "tt_arr": train_info[4],
                "tt_dept": train_info[5],
                "tt_halt": train_info[6],
                "running_days": train_info[7:14],
                "classes": train_info[14:],
            }
            if config.weekday != -1:
                if train_info["running_days"][config.weekday] == "X":
                    continue
            
            parsed_trains.append(train_info)
        return parsed_trains