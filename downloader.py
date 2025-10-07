import os
import re
import sys
import threading
import subprocess
import requests
import pyperclip
import json
import tempfile
from PIL import Image
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
from mutagen.flac import FLAC, Picture
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table

CONFIG_FILE = "yt_downloader_config.json"
class GracefulExit(Exception): pass

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
    except:
        pass

def ensure_dirs():
    if not os.path.exists("Downloads"):
        os.makedirs("Downloads")

def get_clipboard_url():
    try:
        text = pyperclip.paste().strip()
        if re.search(r'(https?://)?(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)/', text):
            return text
    except:
        pass
    return None

def check_yt_dlp_update(console):
    try:
        res = requests.get("https://pypi.org/pypi/yt-dlp/json", timeout=5)
        latest = res.json()["info"]["version"]
        out = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
        current = out.stdout.strip()
        if current != latest:
            ans = Prompt.ask(f"Update available for yt-dlp: {latest}. Update? [Y/n]", choices=["Y","n"], default="Y")
            if ans.lower() == "y":
                console.print("Updating yt-dlp...")
                subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
                console.print("yt-dlp updated. Please restart the program.")
                raise GracefulExit
    except:
        pass

def natural_size(num):
    for unit in ['B','KB','MB','GB','TB']:
        if abs(num) < 1024.0:
            return "%3.1f %s" % (num, unit)
        num /= 1024.0
    return "%.1f PB" % num

def guess_is_music(url):
    return 'music.youtube.com' in url

def is_playlist(url):
    return ('list=' in url or '/playlist?' in url or '/playlist/' in url) and 'watch?' not in url

def parse_selection(selection, total):
    indices = set()
    for part in selection.split(','):
        part = part.strip()
        if '-' in part:
            try:
                start, end = [int(x) for x in part.split('-')]
                indices.update(range(start, end+1))
            except:
                continue
        elif part.isdigit():
            indices.add(int(part))
    return sorted(i for i in indices if 1 <= i <= total)

def fetch_playlist_entries(url):
    from yt_dlp import YoutubeDL
    entries = []
    with YoutubeDL({'quiet': True, 'extract_flat': True, 'forcejson': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        if 'entries' in info:
            for i, e in enumerate(info['entries'], 1):
                title = e.get('title') or f"Untitled {i}"
                entries.append({'index': i, 'id': e.get('id'), 'title': title})
    return entries

def sanitize(s):
    return re.sub(r'[\/\\\:\*\?"<>\|]', '_', s)

def download_thumbnail_convert(thumbnail_url):
    if os.path.exists(thumbnail_url):
        return thumbnail_url
    response = requests.get(thumbnail_url, stream=True, timeout=8)
    ext = os.path.splitext(thumbnail_url)[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as out_img:
        if ext in [".jpg", ".jpeg"]:
            for chunk in response.iter_content(1024):
                out_img.write(chunk)
        else:
            with tempfile.NamedTemporaryFile(delete=True, suffix=ext) as temp_orig:
                for chunk in response.iter_content(1024):
                    temp_orig.write(chunk)
                temp_orig.flush()
                im = Image.open(temp_orig.name).convert("RGB")
                im.save(out_img, "JPEG")
        return out_img.name

def embed_cover_audiofile(path, img_file, fmt):
    if fmt == "mp3":
        audio = None
        try:
            audio = ID3(path)
        except:
            audio = ID3()
        with open(img_file, 'rb') as imgf:
            audio.add(APIC(encoding=3, mime='image/jpeg', type=3, desc=u'Cover', data=imgf.read()))
        audio.save(path)
    elif fmt == "flac":
        audio = FLAC(path)
        image = Picture()
        with open(img_file, 'rb') as imgf:
            image.data = imgf.read()
        image.type = 3
        image.mime = "image/jpeg"
        audio.add_picture(image)
        audio.save()

def write_tags(path, info, fmt, idx=None, album=None):
    tags = {}
    tags['title'] = info.get('title', '')
    tags['artist'] = info.get('uploader') or info.get('channel') or ''
    tags['album'] = album or info.get('album') or info.get('playlist_title') or ''
    tags['date'] = str(info.get('release_year', '') or info.get('upload_date', '')[:4])
    tags['genre'] = info.get('genre', '')
    if idx: tags['tracknumber'] = str(idx)
    if fmt == "mp3":
        try:
            audio = EasyID3(path)
        except Exception:
            audio = EasyID3()
        for k, v in tags.items():
            if v: audio[k] = v
        audio.save(path)
    elif fmt == "flac":
        audio = FLAC(path)
        for k, v in tags.items():
            if v: audio[k] = v
        audio.save()

def save_yt_description(path, desc):
    if desc:
        fn = os.path.splitext(path)[0] + ".txt"
        with open(fn, "w", encoding="utf-8") as f:
            f.write(desc)

def download_task(opts, url_list, summary, mode, console, fmt, playlist_seq=None, album=None, do_lyrics=True, max_retries=2):
    from yt_dlp import YoutubeDL
    with Progress(TextColumn("{task.description}"), BarColumn(), "[progress.percentage]{task.percentage:>3.1f}%", TimeElapsedColumn(), TimeRemainingColumn()) as progress:
        total_vids = len(url_list)
        failed = []
        for idx, url in enumerate(url_list,1):
            retry = 0
            while retry < max_retries:
                task = progress.add_task(f"Downloading {idx} of {total_vids}: {url}", total=None)
                status = "Success"
                final_path = None
                file_type = "Video"
                size = None
                try:
                    with YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        if "requested_downloads" in info:
                            info = info["requested_downloads"][0]
                        if "filepath" in info:
                            final_path = info["filepath"]
                        else:
                            outtmpl = opts.get("outtmpl", info.get("title", "audiofile") + "." + fmt)
                            final_path = outtmpl if isinstance(outtmpl, str) else outtmpl.get("default")
                        if final_path and os.path.exists(final_path):
                            size = os.path.getsize(final_path)
                        if mode == "audio" or (final_path and final_path.lower().endswith(tuple(['.mp3', '.flac', '.m4a']))):
                            file_type = "Audio"
                            tn_url = info.get("thumbnail")
                            if not tn_url:
                                t_list = info.get("thumbnails", [])
                                tn_url = t_list[-1]["url"] if t_list else None
                            print("Thumbnail URL:", tn_url)
                            if tn_url and final_path:
                                try:
                                    img = download_thumbnail_convert(tn_url)
                                    print("Downloaded image file:", img)
                                    embed_cover_audiofile(final_path, img, fmt)
                                    if img and os.path.exists(img) and not os.path.abspath(img).endswith("default.jpg"):
                                        os.remove(img)
                                except Exception as e:
                                    print("Thumbnail error:", e)
                            else:
                                print("No thumbnail found for this audio.")
                            ix = playlist_seq[idx-1] if playlist_seq else None
                            write_tags(final_path, info, fmt, ix, album)
                            if do_lyrics:
                                save_yt_description(final_path, info.get("description"))
                    summary.append([final_path if final_path else url, file_type, status, natural_size(size) if size else ""])
                    progress.remove_task(task)
                    break
                except Exception as e:
                    status = f"FAIL: {e}"
                    retry += 1
                    progress.remove_task(task)
                    if retry >= max_retries:
                        console.print(f"❌ Failed to download: {url} - {str(e)}")
                        failed.append(url)
                        summary.append([final_path if final_path else url, file_type, status, natural_size(size) if size else ""])
                        break
                    else:
                        console.print(f"Retrying ({retry}/{max_retries}) for {url} ...")
                        continue
        if failed:
            console.print("[bold red]These failed:[/bold red]")
            for url in failed:
                console.print(url)

def open_folder(path):
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])
    except:
        pass

def pick_audio_format():
    ch = Prompt.ask("Pick audio format", choices=["mp3", "m4a", "flac"], default="mp3")
    return ch

def main():
    console = Console()
    while True:
        try:
            ensure_dirs()
            check_yt_dlp_update(console)
        except GracefulExit:
            sys.exit(0)
        config = load_config()
        last_output_folder = config.get("last_output_folder", "Downloads")
        urls = []
        clipboard_url = get_clipboard_url()
        if clipboard_url:
            try:
                if Confirm.ask(f"Detected a YouTube link: {clipboard_url} Use it?", default=True):
                    urls = [clipboard_url]
            except KeyboardInterrupt:
                console.print("\n[red]Operation cancelled by user.[/red]")
                sys.exit(0)
        if not urls:
            try:
                url_input = Prompt.ask("Enter YouTube URL or type 'file' to load URLs from file or 'q' to quit", default="")
                if url_input.lower() == 'q':
                    console.print("Goodbye!")
                    sys.exit(0)
                if url_input.lower() == "file":
                    file_path = Prompt.ask("Enter the path to the txt file with URLs")
                    with open(file_path) as f:
                        urls = [x.strip() for x in f if x.strip()]
                else:
                    urls = [url_input]
            except KeyboardInterrupt:
                console.print("\n[red]Operation cancelled by user.[/red]")
                sys.exit(0)
        url = urls[0]
        choice = Prompt.ask("Download as", choices=["video", "audio"], default="video")
        if choice == "audio":
            fmt = pick_audio_format()
            mode = "audio"
        else:
            mode = "video"
            fmt = "mp4"

        folder = Prompt.ask("Output folder", default=last_output_folder)
        if not os.path.exists(folder):
            os.makedirs(folder)
        config["last_output_folder"] = folder
        save_config(config)
        opts = {}
        playlist_mode = False
        playlist_indices = None
        playlist_urls = []
        playlist_seq = None
        album = None
        if is_playlist(url):
            playlist_mode = True
            entries = fetch_playlist_entries(url)
            console.print(f"[bold]Playlist detected. {len(entries)} videos found:[/bold]")
            for e in entries:
                console.print(f"[{e['index']:>2}] {e['title']}")
            try:
                sel = Prompt.ask("Enter numbers or ranges to download (e.g. 1,2,5-7) or leave blank for all", default="")
            except KeyboardInterrupt:
                console.print("\n[red]Operation cancelled by user.[/red]")
                sys.exit(0)
            if sel.strip():
                playlist_indices = parse_selection(sel, len(entries))
                opts["playlist_items"] = ",".join(str(i) for i in playlist_indices)
            else:
                playlist_indices = list(range(1, len(entries)+1))
            for ix in playlist_indices:
                entry = entries[ix-1]
                playlist_urls.append(f"https://www.youtube.com/watch?v={entry['id']}")
            playlist_seq = list(range(1, len(playlist_urls)+1))
            album = entries[0].get("playlist_title") or None
        fnpat = "%(uploader)s"
        if mode == "audio":
            if playlist_mode and album:
                fnpat += os.sep + sanitize(album)
                outtmpl = os.path.join(folder, fnpat, "%(playlist_index)02d - %(title)s.%(ext)s")
            elif playlist_mode:
                outtmpl = os.path.join(folder, fnpat, "%(playlist_index)02d - %(title)s.%(ext)s")
            else:
                outtmpl = os.path.join(folder, fnpat, "%(title)s.%(ext)s")
            if fmt == "mp3":
                opts = dict(format="bestaudio/best", extractaudio=True, audioformat="mp3",
                    postprocessors=[{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}], outtmpl=outtmpl)
            elif fmt == "m4a":
                opts = dict(format="bestaudio[ext=m4a]/bestaudio/best", extractaudio=True, audioformat="m4a",
                    postprocessors=[{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}], outtmpl=outtmpl)
            elif fmt == "flac":
                opts = dict(format="bestaudio/best", extractaudio=True, audioformat="flac",
                    postprocessors=[{"key": "FFmpegExtractAudio", "preferredcodec": "flac"}], outtmpl=outtmpl)
        else:
            outtmpl = os.path.join(folder, fnpat, "%(title)s.%(ext)s")
            opts["format"] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            opts["merge_output_format"] = "mp4"
            opts["outtmpl"] = outtmpl
            opts["writesubtitles"] = True
            opts["embedsubtitles"] = True
            opts["subtitleslangs"] = ["en"]
            opts["writeautomaticsub"] = True
            opts["sponsorblock_remove"] = ["all"]
        summary = []
        urls_to_download = playlist_urls if playlist_mode else urls
        if playlist_mode and playlist_indices:
            table = Table(title="Selected Videos to Download")
            table.add_column("Index", justify="right")
            table.add_column("Title")
            for i, ix in enumerate(playlist_indices,1):
                e = entries[ix-1]
                table.add_row(str(i), e['title'])
            console.print(table)
            try:
                proceed = Confirm.ask(f"You have selected {len(playlist_indices)} videos to download. Proceed?", default=True)
            except KeyboardInterrupt:
                console.print("\n[red]Operation cancelled by user.[/red]")
                sys.exit(0)
            if not proceed:
                console.print("Download cancelled.")
                sys.exit(0)
        try:
            if Confirm.ask("Start download?", default=True):
                download_task(opts, urls_to_download, summary, mode, console, fmt, playlist_seq, album, True)
        except KeyboardInterrupt:
            console.print("\n[red]Download interrupted by user.[/red]")
            sys.exit(0)
        table = Table(title="Download Summary")
        table.add_column("File")
        table.add_column("Type", justify="center")
        table.add_column("Status", justify="center")
        table.add_column("Size", justify="right")
        for row in summary:
            table.add_row(*[str(x) if x else "" for x in row])
        console.print(table)
        again = Confirm.ask("Download another batch?", default=False)
        if not again:
            try:
                if Confirm.ask("Open download folder now?", default=True):
                    open_folder(os.path.abspath(folder))
            except KeyboardInterrupt:
                console.print("\n[red]Operation cancelled by user.[/red]")
            break

if __name__ == '__main__':
    try:
        main()
    except GracefulExit:
        pass
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
