
# YouTube & YouTube Music CLI Downloader

A modern, all-in-one Python tool to download **audio (MP3, FLAC, M4A)** and **video (MP4)** from YouTube and YouTube Music—**with album art**, smart file/folder naming, playlist support, lyrics saving, batch mode, and automatic metadata tagging.

## Features

- Download individual videos/music or full playlists
- Extract audio as MP3, FLAC, or M4A (your choice)
- Save videos as MP4 (best available quality)
- **Embed YouTube cover art as album art for audio files**
- Write artist, album, title, year, genre, and track numbers into tags
- Save lyrics/video descriptions as text files alongside your music
- Batch/playlist downloading, clean UX, automatic retries
- Works on Windows, macOS, Linux

## Installation

### 1. Install Python 3.8+
[Download Python](https://www.python.org/downloads/) if you don't have it.

### 2. Install ffmpeg

**Windows:**
- Download [ffmpeg build](https://www.gyan.dev/ffmpeg/builds/)
- Unzip and add `bin` folder to PATH
- Verify: `ffmpeg -version`

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt update && sudo apt install ffmpeg
```

### 3. Get the Script & Install Dependencies

```bash
git clone https://github.com/aswinop/yt-downloader.git
cd yt-downloader
pip install -r requirements.txt
```

### Dependencies:
- `rich` – Beautiful CLI interface
- `yt-dlp` – YouTube download backend
- `pyperclip` – Clipboard detection
- `requests` – HTTP requests
- `pillow` – Image processing
- `mutagen` – Audio metadata editing

## Usage

```bash
python downloader.py
```

### Step-by-Step:

1. **URL Input**
   - Automatically detects YouTube links in clipboard
   - Or paste URL manually
   - Or load multiple URLs from text file

2. **Format Selection**
   - Audio: MP3, FLAC, or M4A
   - Video: MP4 (best quality)

3. **Output Folder**
   - Choose download location
   - Default: `Downloads/` folder

4. **Playlist Support**
   - View all playlist entries
   - Select specific tracks (e.g., `1-3,5,7`)

5. **Download & Processing**
   - Progress bars with ETA
   - Automatic retries on failure
   - Metadata embedding
   - Cover art extraction

6. **Completion**
   - Summary table of all downloads
   - Option to open download folder
   - Batch mode for multiple downloads

## Sample Session

```
🎵 YouTube & YouTube Music Downloader 🎬
═══════════════════════════════════════════════════════════════════════════════
🎯 Smart organization    📁 Playlist support    🎨 Cover art embedding    
🏷️ Metadata tagging      📝 Lyrics saving       🔄 Batch processing       

🔗 Enter YouTube URL
• Paste a YouTube/YouTube Music URL
• Type 'file' to load from text file
• Type 'q' to quit

URL (): https://youtu.be/abc123def456

📥 Download Type
🎵 audio - Music (MP3, FLAC, M4A) with metadata & cover art
🎬 video - Video (MP4) with subtitles

Choose type [video/audio] (video): video

📁 Output Folder
Files will be saved in: Downloads
Change folder (Downloads): MyVideos

🎯 Ready to download: https://youtu.be/abc123def456

🚀 Start download? [y/n] (y): y

⠴ 🎬 Downloading 1/1 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:45
[download] Destination: MyVideos/Example Channel/Sample Video Title.f401.mp4
[download] Destination: MyVideos/Example Channel/Sample Video Title.f140.m4a
[Merger] Merging formats into "MyVideos/Example Channel/Sample Video Title.mp4"

🎉 Download Summary
┌─────────────────────────────────────────────────────────────────────────────┐
│ File: MyVideos/Example Channel/Sample Video Title.mp4                       │                     
│ Type: Video                    Status: ✅ Success          Size: 124.5 MB  │
└─────────────────────────────────────────────────────────────────────────────┘

✅ Successfully downloaded 1 file(s)
📊 Total size: 124.5 MB

🔄 Download another batch? [y/n] (n): n
📂 Open download folder? [y/n] (y): y

🎊 All done! Happy watching! 🎬
```

## Output Structure

```
Downloads/
├── Channel Name/
│   ├── Video Title.mp4
│   └── Video Title.txt (description)
└── Artist Name/
    └── Album Name/
        ├── 01 - Song Title.flac
        ├── 01 - Song Title.txt (lyrics)
        ├── 02 - Song Title.flac
        └── 02 - Song Title.txt (lyrics)
```

## Features Details

**Audio Files:**
- Embedded cover art from YouTube thumbnails
- ID3 tags (MP3) or Vorbis comments (FLAC)
- Track numbering for playlists
- Lyrics/descriptions saved as text files

**Video Files:**
- Best available MP4 quality
- Embedded subtitles (English)
- SponsorBlock segments removed
- Clean filenames

**Playlists:**
- Selective track downloading
- Maintains playback order
- Album metadata from playlist

## Troubleshooting

**No album art?**
- YouTube may not provide high-quality thumbnails for some content

**ffmpeg not found?**
- Ensure ffmpeg is in your PATH: `ffmpeg -version`

**Installation issues?**
- Try: `pip install --upgrade pip`
- Use virtual environment for clean installation

**Download failures?**
- Check internet connection
- Verify YouTube URL is accessible
- Some content may be region-restricted

## License

MIT License - see LICENSE file for details.
