# IRAS-New

This project is the successor to the [Indian\_Railways\_Announcement\_System](https://github.com/sairam4123/Indian_Railways_Announcement_System) built 5 years ago. It builds upon a personal project developed a few years earlier and has been significantly enhanced.

## Features

- Two modes of operation:
  - **Discord Bot**: Plays railway-style announcements in Discord servers.
  - **Console App**: A standalone application for announcements.


## History

This project originated as a Discord Bot designed to replicate Indian Railways announcements. Over time, after studying the detailed documentation provided by RDSO (Research Design and Standards Organization), it was expanded into a console-based application for broader use.

## Dependencies
1. FFMpeg (Download from https://www.ffmpeg.org/)
2. eSpeak-NG
   - This dependency is only needed if you're going to run Discord App. (Not recommended)
3. Discord Bot Token:
   - This dependency is only needed if you're going to run Discord App. (Not recommended)

## Running the Project

1. **Install Dependencies**:

   - Use [Poetry](https://python-poetry.org/) to manage dependencies:
     ```bash
     poetry install
     ```
     If Poetry is not installed, it can be added via pip:
     ```bash
     pip install poetry
     ```

2. **Activate the virtual environment**:
    - Use `poetry env activate` to activate the virtual environment. If a venv doesn't exist, then Poetry will create one for you.

3. **Start the Project**:

   - For the Console App:
     ```bash
     python console.py
     ```
   - For the Discord Bot:
     ```bash
     python main.py
     ```

---

## Architecture

- **`main.py`**: Implements a priority-based announcements player for the Discord Bot.
- **`console.py`**: Implements a priority-based announcements player for standalone use.

### Custom Libraries

Two custom libraries are included for specialized functionality:

1. **`espeak_ng`**:

   - Wraps the `espeak_ng` executable for text-to-speech functionality.
   - Requires the `espeak_ng` executable to be in the system path.

2. **`etrainlib`**:

   - Scrapes data from [etrain.info](https://etrain.info) using BeautifulSoup.
   - Provides APIs for simplified data access.


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

4. **Audio Generation**:

   - Google Text-to-Speech (GTTS) converts announcement text into audio in three languages.
   - A signature chime ("ting ting") is added to the beginning of all announcements.

5. **Audio Playback**:

   - Final audio files are queued and played:
     - Via speakers for the Console App.
     - On Discord servers for the Discord Bot.


## Future Improvements

- Support for rescheduled, diverted, and canceled trains.
- Enhanced polling mechanism for optimized API calls based on train proximity.
- Improved batching of announcements to minimize redundancy.
- Support for late arriving trains.
- Platform-based announcements playback (partially implemented).
- Operator takeover functionality to allow manual control of announcements.
- Advanced error handling for network issues or incomplete data.
- Multi-station management for more complex scenarios.

---

## Acknowledgements

- [Indian Railways](https://indianrailways.gov.in/)
- [RDSO Documentation](https://rdso.indianrailways.gov.in/)
- [etrain.info](https://etrain.info/)

