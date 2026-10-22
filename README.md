# OrangeRipper

OrangeRipper is a high-performance, cross-platform desktop CD ripping and audio encoding utility built with PyQt6. Designed with a modular, non-blocking asynchronous architecture, it decouples intensive hardware I/O and network operations from the main UI thread to maintain a seamless user experience.

Written for Orange Records by Kyle T Strand.

---

## Technical Architecture & Core Mechanisms

### 1. Low-Level Windows Audio Extraction (SPTI)
On Windows platforms, standard high-level filesystem APIs cannot read raw audio sectors (`.cda` tracks contain no actual filesystem data). OrangeRipper bypasses this limitation by implementing native **SCSI Pass-Through Direct (SPTI)** via Python's `ctypes` foreign function interface:
* **Direct Hardware Interaction:** Communicates directly with optical drive handles opened via Windows `CreateFileW` with `GENERIC_READ | GENERIC_WRITE` permissions.
* **SCSI Commands (`IOCTL_SCSI_PASS_THROUGH_DIRECT`):** Constructs low-level 16-byte Command Descriptor Blocks (CDBs), specifically the SCSI `READ (10)` command (`0xBE`), to stream raw 2352-byte audio sectors straight from the physical disc buffer.
* **Memory Management:** Utilizes packed `ctypes.Structure` definitions (`SCSI_PASS_THROUGH_DIRECT`) and managed byte buffers to perform zero-copy sector transfers into temporary WAV files.

### 2. Asynchronous Multi-Threaded Processing (`QThread`)
To ensure the PyQt6 graphical interface never hangs or stutters during long-running tasks, OrangeRipper relies on dedicated background worker threads:
* **`MetadataWorker`:** Asynchronously reads the physical disc's Table of Contents (TOC), calculates the unique MusicBrainz DiscID, and executes multi-database queries without blocking event loops.
* **`RipWorker`:** Handles the track-by-track extraction, external encoder piping, and metadata tagging lifecycle in a sequential background thread, emitting progress signals (`pyqtSignal`) live to update the UI progress bar and status console.

### 3. Multi-Database Metadata Waterfall Resolution
OrangeRipper utilizes a robust fallback strategy to identify physical releases accurately:
1. **MusicBrainz:** Queries direct disc TOC signatures using `discid` to locate exact physical pressings.
2. **AcoustID & Discogs:** Fallback acoustic fingerprinting and release-matching pipelines to handle lesser-known or variant pressings.
3. **Studio Filtering:** Implements heuristic release filtering to ignore digital compilation spam and target definitive studio pressings.

### 4. Process Isolation & Window Suppression
When piping audio through external native binaries (`flac.exe`, `lame.exe`), Windows by default spawns a visible host command prompt for each execution. OrangeRipper eliminates terminal flashing entirely by injecting the **`CREATE_NO_WINDOW` (`0x08000000`)** creation flag into all `subprocess.Popen` and `subprocess.run` invocations across worker loops and encoding services.

---

## Features

* **Native Optical Drive Handling:** Direct SPTI sector extraction on Windows (`E:`, etc.) and `cdparanoia` integration on Linux (`/dev/sr0`).
* **High-Fidelity Audio Encoding:** Seamless post-extraction encoding to **FLAC** (configurable compression levels) or **MP3** (via bundled LAME binary at 320/192/128 kbps).
* **Automated & Manual Tagging:** Embeds ID3v2/FLAC metadata tags and high-resolution cover art fetched directly from release art archives using `mutagen`.
* **Manual Text Parser:** Instantaneous parsing engine for raw liner notes or digital tracklists when physical media lacks online database entries.
* **Zero-Dependency Portable Packaging:** Fully bundled via PyInstaller for standalone Windows deployment (`--onedir`, `--windowed`), including dynamic binary injection (`lame.exe`, `flac.exe`, `discid.dll`).

---

## Installation

OrangeRipper features automated setup utilities to verify Python environments, install missing dependencies, and generate platform-specific launch configurations.

### Linux / macOS
1. Open your terminal in the project root directory.
2. Run the automated installation wrapper:
   ```bash
   ./INSTALL
   ```
   *(If permission is denied, grant execution access first via `chmod +x INSTALL`)*. This automatically generates your `run.sh` launch script.

### Windows
1. Open Command Prompt or PowerShell in the project directory.
2. Run the setup utility:
   ```cmd
   python install.py
   ```
   This installs required Python libraries (`PyQt6`, `discid`, `mutagen`, `requests`, `Pillow`) and prepares launch scripts.

---

## Packaging for Distribution (Windows)

To build a standalone, portable Windows distribution container containing all binary dependencies, assets (`app.ico`), and compiled modules:
```cmd
package.bat
```
This script cleans old caches, provisions the virtual environment, executes PyInstaller with custom asset injection flags (`--icon`, `--add-data`), and packages the executable into `dist\OrangeRipper\`.

---

## Usage

1. **Launching the Application**
   * **Linux / macOS:** `./run.sh`
   * **Windows:** Double-click `run.bat` or launch `dist\OrangeRipper\OrangeRipper.exe`.

2. **Ripping a CD**
   * Insert an audio CD into your computer optical drive.
   * Click **Scan CD Drive** in the top control panel. The status bar will walk you through reading the drive TOC, calculating the DiscID, and querying remote metadata.
   * Review the populated Artist, Album, Year, cover art thumbnail, and track table. Use checkboxes to select specific tracks.
   * Click **Start Ripping** to begin raw SPTI extraction and background encoding.

3. **Manual Tracklist Parsing**
   * Click **Paste Tracklist (Manual)**.
   * Paste your track data into the parser dialog and apply it to load the table instantly.

---

## Author & Support

OrangeRipper is developed and maintained by Kyle T Strand.

* **Email:** [kyletstrand@gmail.com](mailto:kyletstrand@gmail.com)
* **Organization:** Orange Records

If OrangeRipper has streamlined your archiving or listening workflow, consider fueling future updates or buying a coffee!

☕ **Ko-fi Support:** [https://ko-fi.com/kyletstrand](https://ko-fi.com/kyletstrand)
