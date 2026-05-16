import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from typing import Optional

import requests
import pyperclip
from PIL import Image
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover
from rich.console import Console
from rich.progress import (
    Progress, BarColumn, TextColumn,
    TimeElapsedColumn, TimeRemainingColumn,
    SpinnerColumn, TransferSpeedColumn, FileSizeColumn
)
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

CONFIG_FILE = "yt_downloader_config.json"
DEFAULT_FOLDER = "Downloads"
AUDIO_FORMATS = ["mp3", "m4a", "flac"]
VIDEO_RESOLUTIONS = ["best", "4320", "2160", "1440", "1080", "720", "480", "360"]
RESOLUTION_LABELS = {
    "best": "Best available",
    "4320": "4320p — 8K",
    "2160": "2160p — 4K",
    "1440": "1440p — 2K",
    "1080": "1080p — Full HD",
    "720":  "720p  — HD",
    "480":  "480p  — SD",
    "360":  "360p  — Low",
}
YT_URL_PATTERN = re.compile(
    r'https?://(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)/'
)
UNSAFE_CHARS = re.compile(r'[\/\\\:\*\?"<>\|]')

logging.basicConfig(
    filename="yt_downloader.log",
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

@dataclass
class Config:
    last_output_folder: str = DEFAULT_FOLDER
    download_history: list = field(default_factory=list)

    @staticmethod
    def load() -> "Config":
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                return Config(**{k: v for k, v in data.items() if k in Config.__dataclass_fields__})
            except Exception as exc:
                log.warning("Failed to load config: %s", exc)
        return Config()

    def save(self) -> None:
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2)
        except Exception as exc:
            log.warning("Failed to save config: %s", exc)

    def reset(self) -> None:
        default = Config()
        self.last_output_folder = default.last_output_folder
        self.download_history = default.download_history
        self.save()


@dataclass
class DownloadResult:
    url: str
    file_path: str
    file_type: str
    status: str
    size_bytes: int = 0

    @property
    def success(self) -> bool:
        return self.status == "success"

    @property
    def size_str(self) -> str:
        return _human_size(self.size_bytes) if self.size_bytes else "—"


def _human_size(num: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


def sanitize(s: str) -> str:
    return UNSAFE_CHARS.sub("_", s).strip()


def is_youtube_url(text: str) -> bool:
    return bool(YT_URL_PATTERN.search(text))


def is_playlist_url(url: str) -> bool:
    """
    True only for genuine playlist URLs.
    Watches with a list= param are single videos in a playlist context —
    we treat them as single downloads unless the user wants the full list.
    """
    return "/playlist?" in url or url.startswith("https://www.youtube.com/playlist")


def get_clipboard_url() -> Optional[str]:
    try:
        text = pyperclip.paste().strip()
        if is_youtube_url(text):
            return text
    except Exception:
        pass
    return None


def open_folder(path: str) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception as exc:
        log.warning("Could not open folder: %s", exc)


class GracefulExit(Exception):
    pass


def check_for_update(console: Console) -> None:
    try:
        with console.status("[dim]Checking yt-dlp version...[/dim]", spinner="dots"):
            resp = requests.get("https://pypi.org/pypi/yt-dlp/json", timeout=5)
            resp.raise_for_status()
            latest = resp.json()["info"]["version"]
            proc = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
            current = proc.stdout.strip()

        if current != latest:
            console.print(
                f"\n[yellow]yt-dlp update available:[/yellow] {current} → {latest}"
            )
            if Confirm.ask("Update now?", default=True):
                console.print("[blue]Updating yt-dlp…[/blue]")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
                    check=True,
                )
                console.print("[green]Updated. Please restart the program.[/green]")
                raise GracefulExit
    except GracefulExit:
        raise
    except Exception as exc:
        log.debug("Update check failed: %s", exc)


def _best_thumbnail_url(info: dict) -> Optional[str]:
    """
    Prefer highest-resolution thumbnail. yt-dlp lists them smallest-first
    by convention, so we walk in reverse and return the first with a URL.
    """
    thumbnails = info.get("thumbnails") or []
    for t in reversed(thumbnails):
        url = t.get("url")
        if url:
            return url
    return info.get("thumbnail")


def download_thumbnail(url: str) -> Optional[str]:
    try:
        resp = requests.get(url, stream=True, timeout=10)
        resp.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            for chunk in resp.iter_content(8192):
                tmp.write(chunk)
            return tmp.name
    except Exception as exc:
        log.warning("Thumbnail download failed: %s", exc)
        return None


def embed_cover(path: str, img_path: str, fmt: str) -> None:
    if not (img_path and os.path.exists(img_path)):
        return
    try:
        with open(img_path, "rb") as f:
            img_data = f.read()

        if fmt == "mp3":
            audio = ID3(path)
            audio.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=img_data))
            audio.save(v2_version=3)

        elif fmt == "flac":
            audio = FLAC(path)
            pic = Picture()
            pic.data = img_data
            pic.type = 3
            pic.mime = "image/jpeg"
            pic.desc = "Cover"
            audio.clear_pictures()
            audio.add_picture(pic)
            audio.save()

        elif fmt == "m4a":
            audio = MP4(path)
            audio["covr"] = [MP4Cover(img_data, imageformat=MP4Cover.FORMAT_JPEG)]
            audio.save()

    except Exception as exc:
        log.warning("Cover embed failed for %s: %s", path, exc)
    finally:
        try:
            os.remove(img_path)
        except OSError:
            pass


def write_tags(path: str, info: dict, fmt: str, track_num: Optional[int], track_total: Optional[int], album: Optional[str]) -> None:
    title = info.get("title", "").strip()
    artist = (
        info.get("artist")
        or info.get("uploader")
        or info.get("channel")
        or ""
    )
    album_name = album or info.get("album") or info.get("playlist_title") or ""
    year = (
        str(info.get("release_year", ""))
        or (info.get("upload_date", "")[:4] if info.get("upload_date") else "")
    )
    genre = info.get("genre") or "Music"

    try:
        if fmt == "mp3":
            audio = EasyID3(path)
            if title:      audio["title"] = title
            if artist:     audio["artist"] = artist
            if album_name: audio["album"] = album_name
            if year:       audio["date"] = year
            if genre:      audio["genre"] = genre
            if track_num:
                audio["tracknumber"] = (
                    f"{track_num}/{track_total}" if track_total else str(track_num)
                )
            audio.save()

        elif fmt == "flac":
            audio = FLAC(path)
            if title:      audio["title"] = title
            if artist:     audio["artist"] = artist
            if album_name: audio["album"] = album_name
            if year:       audio["date"] = year
            if genre:      audio["genre"] = genre
            if track_num:
                audio["tracknumber"] = str(track_num)
                if track_total:
                    audio["tracktotal"] = str(track_total)
            audio.save()

        elif fmt == "m4a":
            audio = MP4(path)
            if title:      audio["\xa9nam"] = title
            if artist:     audio["\xa9ART"] = artist
            if album_name: audio["\xa9alb"] = album_name
            if year:       audio["\xa9day"] = year
            if genre:      audio["\xa9gen"] = genre
            if track_num:
                audio["trkn"] = [(track_num, track_total or 0)]
            audio.save()

    except Exception as exc:
        log.warning("Tag write failed for %s: %s", path, exc)


def save_description(audio_path: str, description: str) -> None:
    if not description:
        return
    txt_path = os.path.splitext(audio_path)[0] + ".txt"
    try:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(description)
    except OSError as exc:
        log.warning("Could not save description: %s", exc)


def build_audio_opts(fmt: str, folder: str, playlist_mode: bool, album: Optional[str]) -> dict:
    uploader_part = "%(uploader)s"

    if playlist_mode and album:
        outtmpl = os.path.join(folder, uploader_part, sanitize(album), "%(playlist_index)02d - %(title)s.%(ext)s")
    elif playlist_mode:
        outtmpl = os.path.join(folder, uploader_part, "%(playlist_index)02d - %(title)s.%(ext)s")
    else:
        outtmpl = os.path.join(folder, uploader_part, "%(title)s.%(ext)s")

    codec_map = {"mp3": "mp3", "m4a": "m4a", "flac": "flac"}
    fmt_selector = {
        "mp3":  "bestaudio/best",
        "m4a":  "bestaudio[ext=m4a]/bestaudio/best",
        "flac": "bestaudio/best",
    }

    return {
        "format": fmt_selector[fmt],
        "extractaudio": True,
        "audioformat": codec_map[fmt],
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": codec_map[fmt]}],
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "retries": 5,
        "fragment_retries": 5,
    }


def build_video_opts(resolution: str, folder: str) -> dict:
    uploader_part = "%(uploader)s"
    outtmpl = os.path.join(folder, uploader_part, "%(title)s.%(ext)s")

    if resolution == "best":
        fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    else:
        fmt = (
            f"bestvideo[height<={resolution}][ext=mp4]+bestaudio[ext=m4a]"
            f"/best[height<={resolution}][ext=mp4]"
            f"/best[height<={resolution}]"
        )

    return {
        "format": fmt,
        "merge_output_format": "mp4",
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "retries": 10,
        "fragment_retries": 10,
        "skip_unavailable_fragments": True,
        "continue_dl": True,
    }


def fetch_playlist_info(url: str, console: Console) -> tuple[str, list[dict]]:
    """Returns (playlist_title, list of entry dicts)."""
    from yt_dlp import YoutubeDL

    with console.status("[dim]Fetching playlist…[/dim]", spinner="dots"):
        with YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:
            info = ydl.extract_info(url, download=False)

    playlist_title = info.get("title") or ""
    entries = []
    for i, e in enumerate(info.get("entries") or [], 1):
        entries.append({
            "index": i,
            "id": e.get("id", ""),
            "title": e.get("title") or f"Track {i}",
            "duration": e.get("duration"),
        })
    return playlist_title, entries


def parse_track_selection(selection: str, total: int) -> list[int]:
    indices: set[int] = set()
    for part in selection.split(","):
        part = part.strip()
        if "-" in part:
            try:
                start, end = (int(x) for x in part.split("-", 1))
                indices.update(range(start, end + 1))
            except ValueError:
                continue
        elif part.isdigit():
            indices.add(int(part))
    return sorted(i for i in indices if 1 <= i <= total)


def fmt_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "—"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def show_queue_preview(entries: list[dict], console: Console) -> None:
    """Show a compact preview table of what's about to be downloaded."""
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold dim", pad_edge=False)
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Title", style="cyan", max_width=55, overflow="ellipsis")
    table.add_column("Duration", style="dim", justify="right", width=9)

    for e in entries:
        table.add_row(str(e["index"]), e["title"], fmt_duration(e.get("duration")))

    console.print(table)


def _resolve_final_path(ydl, info: dict, opts: dict) -> Optional[str]:
    """Best-effort resolution of the actual output file path."""
    requested = info.get("requested_downloads")
    if requested:
        path = requested[0].get("filepath")
        if path and os.path.exists(path):
            return path

    path = info.get("filepath") or ydl.prepare_filename(info)
    if path and os.path.exists(path):
        return path

    return None


def download_single(
    url: str,
    opts: dict,
    mode: str,
    fmt: str,
    track_num: Optional[int],
    track_total: Optional[int],
    album: Optional[str],
    console: Console,
) -> DownloadResult:
    from yt_dlp import YoutubeDL

    result = DownloadResult(url=url, file_path=url, file_type="Video", status="failed")

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)

        final_path = _resolve_final_path(ydl, info, opts)
        if not final_path:
            result.status = "failed — output file not found"
            return result

        result.file_path = final_path
        result.size_bytes = os.path.getsize(final_path)

        if mode == "audio":
            result.file_type = "Audio"

            tn_url = _best_thumbnail_url(info)
            if tn_url:
                img = download_thumbnail(tn_url)
                if img:
                    embed_cover(final_path, img, fmt)
                    console.print("    [green]✓[/green] Cover art embedded")
                else:
                    console.print("    [yellow]⚠[/yellow] Cover art unavailable")
            else:
                console.print("    [yellow]⚠[/yellow] No thumbnail found")

            write_tags(final_path, info, fmt, track_num, track_total, album)
            console.print("    [green]✓[/green] Metadata written")

            if info.get("description"):
                save_description(final_path, info["description"])
                console.print("    [green]✓[/green] Description saved")

        result.status = "success"

    except Exception as exc:
        result.status = f"failed — {str(exc)[:80]}"
        log.error("Download failed for %s: %s", url, exc)

    return result


def download_all(
    urls: list[str],
    opts: dict,
    mode: str,
    fmt: str,
    track_total: Optional[int],
    album: Optional[str],
    console: Console,
    max_workers: int = 3,
) -> list[DownloadResult]:
    """
    Downloads all URLs. Playlist audio uses parallel workers;
    video downloads are sequential to avoid disk contention.
    """
    results: list[DownloadResult] = []
    total = len(urls)
    workers = max_workers if (mode == "audio" and total > 1) else 1

    progress_cols = [
        SpinnerColumn("dots", style="blue"),
        TextColumn("[bold]{task.description}"),
        BarColumn(bar_width=35),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        FileSizeColumn(),
        TransferSpeedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
    ]

    with Progress(*progress_cols, console=console, transient=False) as progress:
        overall = progress.add_task(
            f"[cyan]{'🎵' if mode == 'audio' else '🎬'} {total} item(s)", total=total
        )

        def run(index_url: tuple[int, str]) -> DownloadResult:
            idx, url = index_url
            track_opts = dict(opts)
            if mode == "audio" and total > 1:
                track_opts["playlist_items"] = str(idx)

            res = download_single(
                url=url,
                opts=track_opts,
                mode=mode,
                fmt=fmt,
                track_num=idx,
                track_total=track_total,
                album=album,
                console=console,
            )
            progress.advance(overall)
            return res

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(run, (i, url)): url for i, url in enumerate(urls, 1)}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as exc:
                    url = futures[future]
                    log.error("Unexpected error for %s: %s", url, exc)
                    results.append(DownloadResult(url=url, file_path=url, file_type="?", status=f"failed — {exc}"))

    return results


def show_summary(results: list[DownloadResult], console: Console) -> None:
    table = Table(
        title="Download Summary",
        box=box.ROUNDED,
        header_style="bold",
        title_style="bold green",
        show_lines=False,
    )
    table.add_column("File", style="cyan", overflow="fold")
    table.add_column("Type", justify="center", width=7)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Size", justify="right", width=10, style="yellow")

    success = 0
    for r in results:
        status_text = "[green]✓ OK[/green]" if r.success else "[red]✗ Fail[/red]"
        table.add_row(
            os.path.basename(r.file_path),
            r.file_type,
            status_text,
            r.size_str,
        )
        if r.success:
            success += 1

    console.print()
    console.print(table)
    console.print(
        f"\n[green]✓[/green] {success}/{len(results)} downloaded successfully"
    )


def print_header(console: Console) -> None:
    title = Text()
    title.append("YouTube & YouTube Music Downloader", style="bold white")
    console.print(
        Panel(
            title,
            subtitle="audio · video · playlists · metadata",
            style="cyan",
            box=box.HEAVY,
            padding=(0, 2),
        )
    )
    console.print()


def pick_url(config: Config, console: Console) -> list[str]:
    clipboard = get_clipboard_url()
    if clipboard:
        console.print(Panel(
            f"[green]Clipboard:[/green] {clipboard}",
            box=box.SIMPLE,
            style="dim",
        ))
        if Confirm.ask("Use this URL?", default=True):
            return [clipboard]

    console.print("[bold]Enter a YouTube URL[/bold]")
    console.print("  • Paste a URL directly")
    console.print("  • Type [cyan]file[/cyan] to load from a text file")
    console.print("  • Type [cyan]q[/cyan] to quit\n")

    url_input = Prompt.ask("URL").strip()

    if url_input.lower() == "q":
        console.print("\n[dim]Goodbye.[/dim]")
        sys.exit(0)

    if url_input.lower() == "file":
        file_path = Prompt.ask("Path to URLs file").strip()
        try:
            with open(file_path, encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip()]
            console.print(f"[green]Loaded {len(urls)} URL(s) from file.[/green]")
            return urls
        except OSError as exc:
            console.print(f"[red]Could not read file: {exc}[/red]")
            sys.exit(1)

    return [url_input]


def pick_mode(console: Console) -> str:
    console.print("\n[bold]Download type[/bold]")
    table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    table.add_column(width=8)
    table.add_column()
    table.add_row("[cyan]audio[/cyan]", "MP3 / FLAC / M4A — with metadata and cover art")
    table.add_row("[cyan]video[/cyan]", "MP4 — best quality, merged audio+video")
    console.print(table)
    return Prompt.ask("\nChoose", choices=["audio", "video"], default="audio")


def pick_audio_format(console: Console) -> str:
    console.print("\n[bold]Audio format[/bold]")
    table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    table.add_column(width=6)
    table.add_column(width=14)
    table.add_column(style="dim")
    table.add_row("[cyan]mp3[/cyan]",  "Lossy",    "Universal compatibility, smaller files")
    table.add_row("[cyan]m4a[/cyan]",  "Lossy",    "Better quality than MP3 at same bitrate")
    table.add_row("[cyan]flac[/cyan]", "Lossless", "Best quality, large files")
    console.print(table)
    return Prompt.ask("\nFormat", choices=AUDIO_FORMATS, default="mp3")


def pick_resolution(console: Console) -> str:
    console.print("\n[bold]Maximum resolution[/bold]")
    table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    table.add_column(width=8)
    table.add_column()
    for key, label in RESOLUTION_LABELS.items():
        table.add_row(f"[cyan]{key}[/cyan]", label)
    console.print(table)
    return Prompt.ask("\nResolution", choices=VIDEO_RESOLUTIONS, default="best")


def pick_folder(config: Config, console: Console) -> str:
    console.print(f"\n[bold]Output folder[/bold]  [dim](last: {config.last_output_folder})[/dim]")
    folder = Prompt.ask("Folder", default=config.last_output_folder).strip()
    if not os.path.exists(folder):
        os.makedirs(folder)
        console.print(f"[dim]Created: {folder}[/dim]")
    return folder


def run_session(console: Console, config: Config) -> bool:
    """
    Runs one full download session. Returns True if the user wants another session.
    """
    try:
        urls = pick_url(config, console)
    except KeyboardInterrupt:
        return False

    url = urls[0]

    try:
        mode = pick_mode(console)
    except KeyboardInterrupt:
        return False

    fmt = ""
    resolution = ""
    if mode == "audio":
        try:
            fmt = pick_audio_format(console)
        except KeyboardInterrupt:
            return False
    else:
        try:
            resolution = pick_resolution(console)
        except KeyboardInterrupt:
            return False

    try:
        folder = pick_folder(config, console)
    except KeyboardInterrupt:
        return False

    config.last_output_folder = folder
    config.save()

    playlist_mode = is_playlist_url(url)
    album: Optional[str] = None
    download_urls: list[str] = []
    preview_entries: list[dict] = []

    if playlist_mode:
        console.print()
        try:
            playlist_title, entries = fetch_playlist_info(url, console)
        except Exception as exc:
            console.print(f"[red]Failed to fetch playlist: {exc}[/red]")
            return False

        album = playlist_title or None
        console.print(
            f"[bold]Playlist:[/bold] [cyan]{playlist_title or 'Untitled'}[/cyan] "
            f"— [green]{len(entries)}[/green] tracks\n"
        )

        show_queue_preview(entries, console)

        try:
            sel = Prompt.ask(
                "\nTracks to download (e.g. 1-3,5) or [cyan]Enter[/cyan] for all",
                default=""
            ).strip()
        except KeyboardInterrupt:
            return False

        if sel:
            chosen = parse_track_selection(sel, len(entries))
            entries = [e for e in entries if e["index"] in set(chosen)]
            console.print(f"[green]{len(entries)}[/green] track(s) selected.")
        else:
            console.print(f"All [green]{len(entries)}[/green] tracks selected.")

        download_urls = [f"https://www.youtube.com/watch?v={e['id']}" for e in entries]
        preview_entries = entries

    else:
        download_urls = urls
        console.print()
        try:
            with console.status("[dim]Fetching info…[/dim]", spinner="dots"):
                from yt_dlp import YoutubeDL
                peek_opts = {"quiet": True, "extract_flat": False, "skip_download": True}
                with YoutubeDL(peek_opts) as ydl:
                    info = ydl.extract_info(url, download=False)

            table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
            table.add_column(style="dim", width=10)
            table.add_column()
            table.add_row("Title",    info.get("title") or "—")
            table.add_row("Channel",  info.get("uploader") or "—")
            table.add_row("Duration", fmt_duration(info.get("duration")))
            console.print(table)
            preview_entries = [{"index": 1, "title": info.get("title", url), "duration": info.get("duration")}]

        except Exception as exc:
            log.warning("Preview fetch failed: %s", exc)
            console.print(f"[dim](Could not fetch preview: {exc})[/dim]")
            preview_entries = [{"index": 1, "title": url, "duration": None}]

    console.print()
    try:
        if not Confirm.ask(
            f"Start download? ({len(download_urls)} item(s))",
            default=True,
        ):
            return True
    except KeyboardInterrupt:
        return False

    track_total = len(download_urls) if playlist_mode else None
    if mode == "audio":
        opts = build_audio_opts(fmt, folder, playlist_mode, album)
    else:
        opts = build_video_opts(resolution, folder)

    console.print()
    results = download_all(
        urls=download_urls,
        opts=opts,
        mode=mode,
        fmt=fmt,
        track_total=track_total,
        album=album,
        console=console,
    )

    for r in results:
        if r.success:
            config.download_history.append(r.file_path)
    config.save()

    show_summary(results, console)

    failed = [r for r in results if not r.success]
    if failed:
        console.print(f"\n[yellow]{len(failed)} item(s) failed.[/yellow]")
        try:
            if Confirm.ask("Retry failed downloads?", default=True):
                retry_results = download_all(
                    urls=[r.url for r in failed],
                    opts=opts,
                    mode=mode,
                    fmt=fmt,
                    track_total=None,
                    album=album,
                    console=console,
                )
                show_summary(retry_results, console)
                for r in retry_results:
                    if r.success:
                        config.download_history.append(r.file_path)
                config.save()
        except KeyboardInterrupt:
            pass

    console.print()
    try:
        if Confirm.ask(f"Open folder [cyan]{folder}[/cyan]?", default=True):
            open_folder(os.path.abspath(folder))
    except KeyboardInterrupt:
        pass

    console.print()
    try:
        return Confirm.ask("Download another batch?", default=False)
    except KeyboardInterrupt:
        return False


def main() -> None:
    console = Console()
    config = Config.load()

    os.makedirs(DEFAULT_FOLDER, exist_ok=True)

    print_header(console)

    try:
        check_for_update(console)
    except GracefulExit:
        sys.exit(0)

    while True:
        try:
            again = run_session(console, config)
        except KeyboardInterrupt:
            break

        if not again:
            break

        console.print("\n" + "─" * 60 + "\n")

    console.print("\n[dim]Done.[/dim]\n")


if __name__ == "__main__":
    main()