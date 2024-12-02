import json
from pathlib import Path

STATION_FILE = Path("stations.json")
station_map = json.loads(STATION_FILE.read_text())
for s_code in station_map:
    if type(station_map[s_code]) == dict:
        continue
    station = station_map[s_code]
    station_map[s_code] = {"name": station, "code": s_code}

STATION_FILE.write_text(json.dumps(station_map, indent=4))