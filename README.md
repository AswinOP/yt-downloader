# YouTube & YouTube Music CLI Downloader

A clean, deliberate Python tool to download **audio (MP3, FLAC, M4A)** and **video (MP4)** from YouTube and YouTube Music — with cover art, metadata tagging, playlist support, and smart file organisation.

## Features

- Download individual videos or full playlists
- Audio: MP3, FLAC, or M4A with embedded cover art and ID3/Vorbis/MP4 tags
- Video: MP4 up to 8K, with selectable maximum resolution
- Queue preview before download — see title and duration for each item
- Parallel playlist downloads (audio)
- Automatic retry of failed downloads at end of session
- Clipboard URL detection
- Batch mode — download multiple URLs from a text file
- Download history tracked in config
- Clean Rich-based terminal UI; raw yt-dlp output suppressed
- Errors logged to `yt_downloader.log` for debugging
- Works on Windows, macOS, Linux

## Installation

### 1. Install Python 3.10+

[Download Python](https://www.python.org/downloads/)

### 2. Install ffmpeg

**Windows:**
```bash
# Download from https://www.gyan.dev/ffmpeg/builds/
# Unzip and add the bin/ folder to PATH
ffmpeg -version  # verify
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt update && sudo apt install ffmpeg
```

### 3. Install the script and dependencies

```bash
git clone https://github.com/aswinop/yt-downloader.git
cd yt-downloader
pip install -r requirements.txt
```

## Usage

```bash
python downloader.py
```

### Step-by-step

1. **URL input** — paste a URL, or let the tool detect one from your clipboard. Type `file` to load a list of URLs from a text file.
2. **Download type** — choose `audio` or `video`.
3. **Format / resolution** — audio: MP3, M4A, or FLAC. Video: pick a maximum resolution (best, 8K, 4K, 2K, 1080p, down to 360p).
4. **Output folder** — defaults to your last-used folder.
5. **Playlist handling** — for playlist URLs, a track list with durations is shown. Select specific tracks (e.g. `1-3,5`) or press Enter for all.
6. **Queue preview** — for single URLs, title and duration are shown before download begins.
7. **Download** — progress bar with speed and ETA. Playlist audio downloads run in parallel.
8. **Retry** — any failures are offered for retry at the end of the session.
9. **Summary** — a table shows each file, its type, status, and size.

## Output structure

```
Downloads/
├── Channel Name/
│   └── Video Title.mp4
└── Artist Name/
    └── Album or Playlist Name/
        ├── 01 - Song Title.flac
        ├── 01 - Song Title.txt
        └── 02 - Song Title.flac
```

Audio files are organised by uploader → album/playlist. Text files alongside audio contain the video description.

## Audio metadata

Tags written per format:

| Tag         | MP3 (ID3) | FLAC (Vorbis) | M4A (MP4) |
|-------------|-----------|---------------|-----------|
| Title       | ✓         | ✓             | ✓         |
| Artist      | ✓         | ✓             | ✓         |
| Album       | ✓         | ✓             | ✓         |
| Year        | ✓         | ✓             | ✓         |
| Genre       | ✓         | ✓             | ✓         |
| Track №     | ✓         | ✓             | ✓         |
| Track total | ✓         | ✓             | ✓         |
| Cover art   | ✓         | ✓             | ✓         |

## Config

Settings are stored in `yt_downloader_config.json` in the working directory:

```json
{
  "last_output_folder": "Downloads",
  "download_history": []
}
```

Delete this file to reset all settings.

## Troubleshooting

**ffmpeg not found**
Ensure ffmpeg is on your PATH: `ffmpeg -version`

**No cover art**
YouTube may not provide thumbnails for some content. The tool tries the highest-resolution thumbnail available and falls back gracefully.

**Download failures**
Check `yt_downloader.log` for details. Common causes: region restrictions, network issues, or a stale yt-dlp version.

**yt-dlp out of date**
The tool checks for updates on startup and offers to install them automatically.

**Python version**
Python 3.10 or later is required (uses structural pattern features and modern type hints).

## Dependencies

| Package     | Purpose                        |
|-------------|--------------------------------|
| yt-dlp      | YouTube download backend       |
| rich        | Terminal UI                    |
| requests    | Thumbnail fetching, update check |
| mutagen     | Audio tag writing              |
| pillow      | Image handling                 |
| pyperclip   | Clipboard detection            |

## License

MIT License — see LICENSE file for details.