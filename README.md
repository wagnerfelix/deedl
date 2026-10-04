 Deezer Audio Downloader

Python script for processing Deezer album, track, and playlist URLs. This README describes the supplied script with the discussed `clean_filename()` and `get_song_filename()` additions, artist directories, and album release years.

## Features

- Processes the tracks included in an album page.
- Prefers FLAC; falls back to MP3 at 320 kbit/s and converts it to FLAC using SoX.
- Organizes downloads as `Artist/Year - Album Title/01 - Track Title.flac`.
- Creates artist and album directories only when they do not already exist.
- Writes title, album, artist, release year, and track number metadata.
- Uses up to four worker threads.

## Requirements

- Python 3.10 or newer, because the script uses `match`/`case`.
- Python packages: `requests`, `pycryptodome`, and `mutagen`.
- SoX with MP3 support for the MP3 fallback.
- A valid ARL session and an account whose options, as checked by the script, allow lossless audio.

## Installation

The examples below assume the script is named `deedl.py`.

Choose either system packages or a virtual environment. All commands below assume you are in the directory containing `deedl.py` and `requirements.txt`.

### Option 1: Run Directly with System Packages

No virtual environment is required for this option. Install Python dependencies through your distribution's package manager.

**Arch Linux:**

```bash
sudo pacman -Syu python python-requests python-pycryptodome python-mutagen sox
python3 --version
```

**Ubuntu (22.04 or newer):**

```bash
sudo apt update
sudo apt install python3 python3-requests python3-pycryptodome python3-mutagen sox libsox-fmt-all
python3 --version
```

Verify the crypto module namespace:

```bash
python3 -c "from Crypto.Cipher import Blowfish; import requests, mutagen; print('Dependencies OK')"
```

If this fails specifically with `No module named 'Crypto'`, check the alternative namespace:

```bash
python3 -c "from Cryptodome.Cipher import Blowfish; import requests, mutagen; print('Dependencies OK')"
```

If the alternative works, replace the original crypto import in `deedl.py` with this compatible import block:

```python
try:
    from Crypto.Cipher import Blowfish
except ModuleNotFoundError as exc:
    if exc.name != "Crypto":
        raise
    from Cryptodome.Cipher import Blowfish
```

Arch's `python-pycryptodome` provides `Crypto`; distro packaging may use `Cryptodome` instead. Check the installed package rather than installing pip packages over system packages. Reference: [Arch package file list](https://archlinux.org/packages/extra/x86_64/python-pycryptodome/files/) and [Debian package file list](https://packages.debian.org/bookworm/amd64/python3-pycryptodome/filelist).

Create the ARL file as described below, then run:

```bash
python3 deedl.py "https://www.deezer.com/de/album/ALBUM_ID"
```

`requirements.txt` is not needed when all dependencies are installed with the package manager.

### Option 2: Run in a Virtual Environment

Install Python, virtual environment support, and SoX first.

**Arch Linux:**

```bash
sudo pacman -Syu python python-pip sox
```

**Ubuntu (22.04 or newer):**

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip sox libsox-fmt-all
```

Create the environment and install the dependencies listed in `requirements.txt`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -c "from Crypto.Cipher import Blowfish; import requests, mutagen; print('Dependencies OK')"
```

Create the ARL file as described below, then run:

```bash
python3 deedl.py "https://www.deezer.com/de/album/ALBUM_ID"
```

For later sessions, activate the environment again with `source .venv/bin/activate`. Leave it with `deactivate`.

Alternatively, run without activating the environment:

```bash
.venv/bin/python3 deedl.py "https://www.deezer.com/de/album/ALBUM_ID"
```

`requirements.txt` contains only Python dependencies. SoX must be installed separately using the system package manager. Versions are not pinned; this is not a tested lockfile.

### Executable Script

The existing `#!/usr/bin/env python3` shebang also supports direct execution:

```bash
chmod +x deedl.py
./deedl.py "https://www.deezer.com/de/album/ALBUM_ID"
```

With an activated virtual environment, the shebang uses its Python interpreter. Otherwise it uses the `python3` found in your shell's PATH.

## ARL File

Place the ARL file next to the script, using the same base filename:

```text
deedl.py
deedl.arl
```

### Obtain Your Own ARL Value

1. Sign in to your own account at [deezer.com](https://www.deezer.com/).
2. Open the browser developer tools, usually with `F12` or `Ctrl+Shift+I`.
3. In Firefox, open **Storage**; in Chromium-based browsers, open **Application**.
4. Expand **Cookies**, select the Deezer domain, and find the cookie named `arl`.
5. Copy only its value. If the cookie is missing, reload the page and confirm you are signed in. Browser panel names may vary.

### Create the File

Run this next to `deedl.py` to enter the token without displaying it or placing it in shell history:

```bash
python3 - <<'PYTHON'
from getpass import getpass
from pathlib import Path
import os

os.umask(0o077)
path = Path("deedl.arl")
value = getpass("Paste your ARL value: ").strip()
if not value:
    raise SystemExit("ARL value must not be empty")
path.write_text(value + "\n", encoding="utf-8")
path.chmod(0o600)
print("Created deedl.arl")
PYTHON
```

If your script has a different name, adjust the ARL filename accordingly. For example, `download.py` requires `download.arl`. The command replaces an existing ARL file's contents.

The file must contain only the ARL value, without quotes or an `arl=` prefix. Leading and trailing whitespace is stripped.

The ARL value is an access token. Keep it private and do not commit it to Git. On Linux, restrict access to the file:

```bash
chmod 600 deedl.arl
```

Suggested `.gitignore` entries:

```gitignore
.venv/
*.arl
```

## Usage

Download an album, replacing `ALBUM_ID` with the actual ID:

```bash
python3 deedl.py "https://www.deezer.com/de/album/ALBUM_ID"
```

Pass multiple URLs in one invocation:

```bash
python3 deedl.py \
  "https://www.deezer.com/de/album/ALBUM_ID_1" \
  "https://www.deezer.com/de/album/ALBUM_ID_2"
```

The script also handles track and playlist URLs:

```bash
python3 deedl.py "https://www.deezer.com/de/track/TRACK_ID"
python3 deedl.py "https://www.deezer.com/de/playlist/PLAYLIST_ID"
```

Without arguments, the script exits without downloading anything. Press `Ctrl+C` to interrupt processing. Completed files remain on disk.

## Directory Structure

Downloads are saved relative to the current working directory, which may differ from the script's directory.

Output pattern:

```text
Artist/Year - Album Title/NN - Track Title.flac
```

Example files:

| Path | Description |
| --- | --- |
| `Example Artist/2026 - Example Album/01 - First Track.flac` | Track 1 |
| `Example Artist/2026 - Example Album/02 - Second Track.flac` | Track 2 |
| `Example Artist/2026 - Example Album/03 - Third Track.flac` | Track 3 |

Directories are created with:

```python
album_dir.mkdir(parents=True, exist_ok=True)
```

Existing artist and album directories are reused. This does not skip existing audio files: matching destination files are still overwritten.

### Artist Selection

The directory name uses the first available artist value in this order:

1. `ALB_ART_NAME` (album artist).
2. `ART_NAME` (track artist).
3. The first nonempty `ART_NAME` in `ARTISTS`.
4. `Unbekannter Interpret` if no artist is available.

For album URLs, the discussed change copies `pagedata["DATA"]["ART_NAME"]` into each track's `ALB_ART_NAME` when available. This keeps all tracks under the same album artist directory, including tracks with different individual artists.

Track and playlist processing falls back to the artist information available in each track's page data. It does not separately fetch album artist information.

### Release Year and Filenames

The album directory uses only the first four characters of the first available release date in this order:

1. `ORIGINAL_RELEASE_DATE`
2. `PHYSICAL_RELEASE_DATE`
3. `DIGITAL_RELEASE_DATE`

Track numbers use at least two digits. Missing track numbers become `00`.

The current helper functions retain these German fallback names:

| Missing value | Fallback |
| --- | --- |
| Release year | `Unbekanntes Jahr` |
| Album title | `Unbekanntes Album` |
| Artist | `Unbekannter Interpret` |
| Track title | Song ID |

Problematic filename characters are removed or replaced with underscores.

## Audio Quality and Metadata

Format preference is configured by the order of `FORMATS`:

```python
FORMATS = (
    "FLAC",
    "MP3_320",
)
```

Available FLAC audio is saved directly. For the MP3 fallback, SoX converts the audio to FLAC and normalizes the peak level to −3 dB. Converting MP3 to FLAC does not restore lost audio detail or make the original source lossless. Direct FLAC downloads are not normalized.

The original `set_metadata()` writes only the year to the `date` tag. Directory naming is independent of this metadata setting. Cover artwork and disc numbers are not written.

## Known Limitations

- Existing destination audio files are overwritten. Interrupted downloads cannot be resumed.
- Multi-disc albums may contain matching track numbers and titles, causing filename collisions. Separate disc directories are not implemented.
- Albums by the same artist with identical years and titles share a directory.
- Sanitizing names can cause different original names to resolve to the same path.
- Playlist processing submits nested tasks to the same thread pool and waits for them. Multiple simultaneous playlist requests can occupy all workers and block processing.
- Only tracks included in the returned page data are processed. Additional pagination for large playlists is not implemented.
- The script relies on internal endpoints and embedded page data, so service changes may require code updates.
- Some download exceptions are caught without detailed error messages. A successful process exit does not guarantee that every track was saved.

## Troubleshooting

| Message or issue | What to check |
| --- | --- |
| `ARL file '…' missing` | Create the ARL file next to the script with the matching base filename. |
| `… is not a regular file` | The ARL path must point to a regular file. |
| `account can't download lossless audio` | The script exits if both checked lossless options are disabled, even though an MP3 fallback exists. |
| `couldn't find page data` | Check the URL, session, and returned page content. |
| `No FLAC or MP3_320 available …` | No sources in the requested formats were returned for this track. |
| Import error for `Crypto`, `requests`, or `mutagen` | Follow the dependency checks in your selected installation option; check `Crypto` versus `Cryptodome` for system packages. |
| MP3 fallback fails | Check that `sox` is available and supports MP3 input. |

This README documents the supplied code and the changes discussed in this conversation. Actual downloads were not tested while preparing it.
