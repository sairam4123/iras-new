import pdfplumber

import json
from tqdm import tqdm

steps = [
    "Extract tables from PDF",
    "Read and parse tables",
    "Convert to JSON",
    "Clean NSG data",
    "Convert NSG to number format",
    "Save to JSON file"
]

nsg_mapping = {
    # Non suburban stations
    "NSG1": 1,
    "NSG2": 2,
    "NSG3": 3,
    "NSG4": 4,
    "NSG5": 5,
    "NSG6": 6,
    # Suburban stations
    "SG1": 7,
    "SG2": 8,
    "SG3": 9,
    "SG4": 10,
    "SG5": 11,
    "SG6": 12,
    # HALT stations
    "HG1": 13,
    "HG2": 14,
    "HG3": 15,
    "HG4": 16,
    "HG5": 17,
    "HG6": 18,
}


def read_table(table: list[list[str | None]]) -> list[dict[str, str]]:
    data = []
    headers = ['Sr No', 'Station', 'Zone', 'Code', 'Division', 'State', 'OldCategory', 'Reserved', 'Unreserved', 'Total', 'EReserved', 'EUnreserved', 'ETotal', 'NewCategory']
    for row in (table[0:]):
        if row[0] == 'Sr. No.' or row[0] == '' or row[1] is None:
            continue
        entry = {headers[i]: row[i] for i in range(len(row))}    
        data.append(entry)
    return data

def parse_pdf(file_path: str) -> list[dict[str, str]]:
    table_data = []
    with pdfplumber.open(file_path) as pdf:
        for page in tqdm(pdf.pages):
            text = page.extract_tables()
            data = read_table(text[0])
            table_data.extend(data)
    return table_data

# Step 1: Extract tables from PDF
# pdf_data = parse_pdf("dataset/station/nsg_stations2022850.pdf")
# station_json = {}

# Step 2: Read and parse tables
# for entry in tqdm(pdf_data):
#     station_json[entry['Code']] = entry['NewCategory']

# with open('dataset/station/nsg_stations2022850.json', 'w') as f:
#     json.dump(station_json, f, indent=4)

with open("dataset/station/nsg_stations2022851.json", "r") as f:
    station_json = json.load(f)

for station in station_json:
    nsg: str = station_json[station]
    nsg = nsg.replace('-', '').replace(' ', '').replace('_', '').replace('P', '').upper()
    station_json[station] = nsg_mapping[nsg]

with open('dataset/station/nsg_stations2022851.json', 'w') as f:
    json.dump(station_json, f, indent=4)
