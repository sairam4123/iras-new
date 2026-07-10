# IRAS-New

This project is the successor to the [Indian\_Railways\_Announcement\_System](https://github.com/sairam4123/Indian_Railways_Announcement_System) built 5 years ago. It builds upon a personal project developed a few years earlier and has been significantly enhanced.

## Features

- **Console App**: A standalone application that plays railway-style, multi-language train announcements through local speakers.


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

---

## Architecture

- **`console.py`**: Standalone entry point; polls live train data on a loop and plays announcements through local speakers, applying per-announcement-type priority, repeat, cooldown, and burst-cooldown rules.
- **`player.py`**: Shared core logic — fetches live train arrivals/departures via `etrainlib`, classifies them into announcement `TYPES` (arrival, arrival shortly, on platform, departure, etc.), builds announcement text from `templates.py`, and hands it off to `vox.py` for audio generation.
- **`vox.py`**: Builds and caches announcement audio. Synthesizes and caches individual phrases per language via `speaker.py`, assembles full announcements from `templates.py`, and prefixes them with a station chime.
- **`templates.py`**: Per-language (English, Tamil, Hindi) phrase templates used to compose each announcement type.
- **`speaker.py`**: Wraps the Google Cloud Text-to-Speech API to synthesize announcement phrases.
- **`dataset_parser.py`**: One-off utility that extracts NSG station-classification tables from RDSO PDFs (`dataset/station/`) into JSON.

### Custom Libraries

- **`etrainlib`**:

   - Scrapes data from [etrain.info](https://etrain.info) using BeautifulSoup.
   - Provides both sync (`_sync.py`) and async (`_async.py`) APIs for simplified data access.


## Implementation

### Data Source

- Live station data is fetched from the `etrain.info` API via HTTP POST requests.

### Key Processes

1. **Data Scraping**:

   - **BeautifulSoup** is used to parse HTML data embedded in JSON responses.
   - A custom request function ensures the payload mimics browser behavior to avoid blocking.
   - Captcha handling is managed separately (details omitted).

2. **Parsing Logic**:

   - Extracts tabular data into structured fields like train number, name, source, destination, timings, platform, etc.
   - Data is cleaned and processed for clarity:
     - Abbreviations (e.g., TPJ -> Tiruchirappalli Junction) are expanded.
     - Common terms (e.g., JN -> Junction) are replaced with full forms.

3. **Priority Queues**:

   - Announcements are managed using a priority queue.
   - High-priority events (e.g., "Train is arriving" or "Train is on platform") are announced before lower-priority events (e.g., "Scheduled to depart").
   - Each announcement type has a cooldown and burst-cooldown, preventing the same event from being repeated too frequently while still allowing rapid updates when a train's status changes.

4. **Audio Generation**:

   - Google Cloud Text-to-Speech converts announcement phrases into audio in three languages (English, Tamil, Hindi); synthesized phrases are cached on disk and reused across announcements.
   - A signature chime ("ting ting") is added to the beginning of all announcements.

5. **Audio Playback**:

   - Final audio files are queued and played through local speakers.


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

