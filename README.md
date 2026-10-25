# IRAS-New

This project is the successor to the [Indian\_Railways\_Announcement\_System](https://github.com/sairam4123/Indian_Railways_Announcement_System) built 5 years ago. It builds upon a personal project developed a few years earlier and has been significantly enhanced.

## Features

- **Console App**: A standalone application that plays railway-style, multi-language train announcements through local speakers.
- **Station Autocomplete**: Pick the station to announce for at startup by typing its name or code, with fuzzy-matched inline suggestions.


## History

This project originated as a Discord Bot designed to replicate Indian Railways announcements. Over time, after studying the detailed documentation provided by RDSO (Research Design and Standards Organization), it was expanded into a console-based application for broader use.

## Dependencies
1. FFMpeg (Download from https://www.ffmpeg.org/)
2. A Google Cloud Text-to-Speech service account
   - Announcement audio is synthesized with Google Cloud TTS (see `speaker.py`). Place your service account key at `gen-lang-client.json` in the project root, or provide it base64-encoded via the `GEN_LANG_JSON_KEY` environment variable.

## Running the Project

1. **Install Dependencies**:

   - This project uses [uv](https://docs.astral.sh/uv/) to manage dependencies:
     ```bash
     uv sync
     ```
     If uv is not installed, see the [installation guide](https://docs.astral.sh/uv/getting-started/installation/).

2. **Start the Project**:

   ```bash
   uv run console.py
   ```

3. **Select a Station**:

   - At the `Select station:>` prompt, start typing a station name (e.g. `TAMBARAM`) or code (e.g. `TBM`). The best fuzzy match is shown as a faint inline hint.
   - **Up/Down** cycles through suggestions, **Tab/Right** accepts the current suggestion and keeps editing, **Enter** selects it, and **Esc** cancels.
   - Stations are loaded from `stations.json`.

---

## Architecture

- **`console.py`**: Standalone entry point; polls live train data on a loop and plays announcements through local speakers, applying per-announcement-type priority, repeat, cooldown, and burst-cooldown rules.
- **`player.py`**: Shared core logic — fetches live train arrivals/departures via `etrainlib`, classifies them into announcement `TYPES` (arrival, arrival shortly, on platform, departure, etc.), builds announcement text from `templates.py`, and hands it off to `vox.py` for audio generation.
- **`vox.py`**: Builds and caches announcement audio. Synthesizes and caches individual phrases per language via `speaker.py`, assembles full announcements from `templates.py`, and prefixes them with a station chime.
- **`templates.py`**: Per-language (English, Tamil, Hindi) phrase templates used to compose each announcement type.
- **`autocomplete.py`**: Fuzzy-matching terminal prompt used for station selection (works on macOS, Linux, and Windows).
- **`stations.json`**: Station code → name lookup used for station selection and name resolution.
- **`speaker.py`**: Wraps the Google Cloud Text-to-Speech API to synthesize announcement phrases.
- **`dataset_parser.py`**: One-off utility that extracts NSG station-classification tables from RDSO PDFs (`dataset/station/`) into JSON.

### Custom Libraries

- **`etrainlib`**:

   - Scrapes data from [etrain.info](https://etrain.info) using BeautifulSoup.
   - Provides both sync (`_sync.py`) and async (`_async.py`) APIs for simplified data access.


## How It Works

This section describes the pipeline from live train data to a played announcement.

### Execution Model

`console.py` runs two concurrent asyncio tasks:

- **Producer** (`fetch_announcements`): every 70 seconds, fetches the live arrivals/departures board for the selected station, generates an announcement for each relevant train, and pushes it onto a shared priority heap.
- **Consumer** (`play_announcements`): pops the highest-priority announcement from the heap, applies the playback rules described under [Scheduling](#scheduling), and plays it, displaying progress with `tqdm`.

Audio generation runs in worker threads, so the producer and consumer operate independently: generating new announcements does not delay playback, and playback does not delay the next poll.

### Data Acquisition

Live station data is fetched from [etrain.info](https://etrain.info) over HTTP. BeautifulSoup parses the HTML embedded in the JSON responses into structured fields: train number, name, source, destination, timings, and platform. If etrain.info requests a captcha, it is displayed in the terminal for the user to solve.

### Announcement Classification

Trains without an assigned platform, and local, MEMU, fast EMU, and parcel services, are excluded by `etrainlib`. For each remaining train, `choose_msg` in `player.py` compares the expected arrival and departure times with the current time and selects an announcement type:

| Train at this station | Time until event | Announcement |
| --- | --- | --- |
| **Originating** (departure only) | < 3 min to departure | Ready for departure |
| | < 60 min to departure | Scheduled to depart |
| **Terminating** (arrival only) | < 3 min to arrival | Arriving on platform |
| | < 10 min | Will arrive shortly |
| | < 30 min | Expected to arrive |
| **Passing through** (arrival and departure) | < 2 min to arrival | Arriving on platform |
| | < 10 / < 30 min to arrival | Arriving shortly / Expected |
| | Arrived, > 2 min to departure | Is on platform |
| | < 3 min to departure | Ready for departure |

Passing-through trains use the `*_middle` templates, which state both the origin and the destination of the train. Records with inconsistent timings (arrival after departure, or both times in the past) are discarded.

### Via Station Selection

Announcements name only a few significant intermediate stations rather than every stop. `build_via_stations` retrieves the train's schedule, takes the stops between the current station and the destination, and:

1. Ranks them by **NSG category** from the RDSO station classification (`dataset/station/nsg_data.json`, extracted from the RDSO PDFs by `dataset_parser.py`). NSG (non-suburban) stations rank above SG (suburban) and HG (halt) stations, with distance used as a tie-breaker.
2. Selects the top five.
3. Re-orders the selection by distance, so stations are announced in travel order.

Each retrieved schedule is also merged into `stations.json`, so the station list (and therefore the selection options) expands with use.

### Text Normalisation

Names returned by etrain.info contain abbreviations that would otherwise be spelled out letter by letter by the TTS engine. `player.py` expands train-name abbreviations (`SF` → Superfast, `EXP` → Express, `JS` → Jan Shatabdi, `VB EXP` → Vande Bharat Express, …) and station-name abbreviations (`CNTL` → Central, `CANTT` → Cantonment, `RD` → Road, …), and replaces station codes in train names with full station names.

The suffix ` JN` is removed from spoken station names. Most major stations are junctions, so retaining it would produce announcements such as "via Madurai Junction, Dindigul Junction, Virudhunagar Junction, Tirunelveli Junction, Nagercoil Junction", where the repeated suffix obscures the station names and reduces intelligibility.

### Announcement Templates

Each announcement in `templates.py` is defined as an ordered list of tokens for each language:

```python
"en": ["{cache[attention]}", "{cache[train_number]}", "{train[no]}", "{train[name]}",
       "{cache[coming_from]}", "{train[src]}", "{cache[arriving_on]}",
       "{cache[platform_label]}", "{train[pf]}"],
```

- `{cache[key]}` refers to a fixed phrase (e.g. "Your kind attention please!", "platform number"), defined per language in `vox.py`.
- `{train[key]}` is substituted with live train data. The train number is expanded into individual digits, each mapped to a cached phrase (`{cache[one]}`, `{cache[two]}`, …), so that `12635` is announced as "one two six three five", in line with standard railway practice.

Token order is defined independently for each language rather than translated from English. Tamil and Hindi are verb-final (e.g. "…platform number 4 *-இல் வந்து கொண்டிருக்கிறது*"), and their templates follow that word order.

### Phrase-Level Audio Caching

`vox.py` synthesizes **each token individually** rather than whole announcements, and caches the results under `anns/cache/<lang>/`:

- Fixed phrases are cached by key (e.g. `attention.mp3`).
- Dynamic text (train names, station names, platform numbers) is cached under the first 10 hexadecimal characters of its SHA-512 hash.
- Leading and trailing silence is trimmed from each phrase before caching. Phrases are joined with 50 ms gaps so that the result is heard as a continuous sentence.
- Fixed phrases are preloaded into memory at startup using a thread pool.

Once the cache is populated, most announcements require no TTS requests. A previously unseen train typically requires only a few new phrases, such as its name or a new via station. Timings (hours and minutes) are synthesized on first use like other dynamic text, and may therefore trigger TTS requests. As the set of possible values is small (24 hours and 60 minutes per language), the cache can be pre-filled with every timing value ahead of time, eliminating these requests.

### Announcement Assembly

For each train, the three language versions are generated in parallel (`asyncio.to_thread`) and sped up by a factor of 1.1 to match the pace of station announcements. They are concatenated in the order **Tamil → Hindi → English**, separated by 500 ms of silence, and prefixed with the signature station chime ("ting ting"). The result is exported to `anns/trains/<train_no>_<train_name>.mp3`; each language version is also saved to `anns/final/`.

Speech is synthesized with a Google Cloud **WaveNet** female voice for each language (`en-IN`, `hi-IN`, `ta-IN`), selected in `speaker.py`.

### Scheduling

Queue entries are tuples of `(priority, event_time, file, type, train_no)`. The heap therefore orders announcements by priority, then by the earliest event time:

| Priority | Announcement | Repeats | Burst interval | Cooldown |
| --- | --- | --- | --- | --- |
| 1 | Arriving on platform | 3 | 5–10 s | 70 s |
| 2 | Ready for departure | 3 | 0 s | 70 s |
| 3 | Is on platform | 3 | 10 s | 90 s |
| 4 | Arriving shortly | 2 | 30 s | 3 min |
| 5 | Expected to arrive | 2 | 1 min | 5 min |
| 6 | Scheduled to depart | 2 | 90 s | 5 min |

For each train, the consumer records the time of the last announcement, its type, and its play count. Before playback, the following rules are applied:

- **Expiry:** announcements for events more than 60 s in the past are discarded.
- **Burst interval:** an announcement of the same type for the same train is not replayed until its burst interval has elapsed, so repeats are spaced apart.
- **Cooldown:** once an announcement type has reached its repeat limit, it is suppressed for the cooldown period, after which the play count is reset.
- **Status changes:** these rules apply only to announcements of the same type. When a train's status changes (e.g. from "arriving shortly" to "arriving on platform"), the new announcement is played without delay.
- **Priority ageing:** announcements that have not played recently are promoted by one priority level: after 5 min for priorities 1–2, and after 10 min for priorities 4–6. This prevents starvation of lower-priority announcements.

For "expected to arrive" and "scheduled to depart" announcements, the producer additionally retrieves the train's **coach positions** and queues a separate announcement giving the position of each coach from the engine.

## Future Improvements

- Support for rescheduled, diverted, and canceled trains.
- Enhanced polling mechanism for optimized API calls based on train proximity.
- Improved batching of announcements to minimize redundancy.
- Support for late arriving trains.
- Operator takeover functionality to allow manual control of announcements.
- Advanced error handling for network issues or incomplete data.
- Multi-station management for more complex scenarios.

---

## Acknowledgements

- [Indian Railways](https://indianrailways.gov.in/)
- [RDSO Documentation](https://rdso.indianrailways.gov.in/)
- [etrain.info](https://etrain.info/)

