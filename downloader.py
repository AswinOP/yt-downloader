import os
import re
import sys
import subprocess
import requests
import pyperclip
import json
import tempfile
from PIL import Image
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn, SpinnerColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich import box

CONFIG_FILE = "yt_downloader_config.json"

class GracefulExit(Exception):
    pass

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
        with console.status("[bold blue]Checking for updates...", spinner="dots"):
            res = requests.get("https://pypi.org/pypi/yt-dlp/json", timeout=5)
            latest = res.json()["info"]["version"]
            out = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
            current = out.stdout.strip()
            if current != latest:
                console.print(f"\n🔄 [yellow]Update available: yt-dlp {current} → {latest}[/yellow]")
                ans = Prompt.ask("Update now?", choices=["Y","n"], default="Y")
                if ans.lower() == "y":
                    console.print("📥 [blue]Updating yt-dlp...[/blue]")
                    subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
                    console.print("✅ [green]yt-dlp updated successfully! Please restart the program.[/green]")
                    raise GracefulExit
    except:
        pass

def natural_size(num):
    for unit in ['B','KB','MB','GB','TB']:
        if abs(num) < 1024.0:
            return "%3.1f %s" % (num, unit)
        num /= 1024.0
    return "%.1f PB" % num

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
    with console.status("[bold blue]Fetching playlist info...", spinner="dots"):
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
    try:
        response = requests.get(thumbnail_url, stream=True, timeout=10)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as out_img:
            for chunk in response.iter_content(1024):
                out_img.write(chunk)
            return out_img.name
    except Exception as e:
        return None

def embed_cover_audiofile(path, img_file, fmt):
    if not img_file or not os.path.exists(img_file):
        return
        
    try:
        if fmt == "mp3":
            audio = ID3(path)
            with open(img_file, 'rb') as imgf:
                image_data = imgf.read()
            audio.add(APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc=u'Cover',
                data=image_data
            ))
            audio.save(v2_version=3)
            
        elif fmt == "flac":
            audio = FLAC(path)
            image = Picture()
            with open(img_file, 'rb') as imgf:
                image.data = imgf.read()
            image.type = 3
            image.mime = "image/jpeg"
            image.desc = "Cover"
            audio.clear_pictures()
            audio.add_picture(image)
            audio.save()
            
        elif fmt == "m4a":
            audio = MP4(path)
            with open(img_file, 'rb') as imgf:
                cover_data = imgf.read()
            audio["covr"] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]
            audio.save()
            
    except Exception as e:
        pass
    finally:
        if img_file and os.path.exists(img_file):
            try:
                os.remove(img_file)
            except:
                pass

def write_tags(path, info, fmt, idx=None, album=None):
    try:
        title = info.get('title', '').strip()
        artist = info.get('uploader') or info.get('channel') or info.get('artist') or ''
        album_name = album or info.get('album') or info.get('playlist_title') or ''
        release_year = info.get('release_year') or (info.get('upload_date', '')[:4] if info.get('upload_date') else '')
        genre = info.get('genre') or 'Music'
        
        if fmt == "mp3":
            audio = EasyID3(path)
            if title: audio['title'] = title
            if artist: audio['artist'] = artist
            if album_name: audio['album'] = album_name
            if release_year: audio['date'] = release_year
            if genre: audio['genre'] = genre
            if idx: audio['tracknumber'] = str(idx)
            audio.save()
            
        elif fmt == "flac":
            audio = FLAC(path)
            if title: audio['title'] = title
            if artist: audio['artist'] = artist
            if album_name: audio['album'] = album_name
            if release_year: audio['date'] = release_year
            if genre: audio['genre'] = genre
            if idx: 
                audio['tracknumber'] = str(idx)
                audio['tracktotal'] = str(idx)
            audio.save()
            
        elif fmt == "m4a":
            audio = MP4(path)
            if title: audio['\xa9nam'] = title
            if artist: audio['\xa9ART'] = artist
            if album_name: audio['\xa9alb'] = album_name
            if release_year: audio['\xa9day'] = release_year
            if genre: audio['\xa9gen'] = genre
            if idx: audio['trkn'] = [(idx, 0)]
            audio.save()
            
    except Exception as e:
        pass

def save_yt_description(path, desc):
    if desc:
        try:
            fn = os.path.splitext(path)[0] + ".txt"
            with open(fn, "w", encoding="utf-8") as f:
                f.write(desc)
        except:
            pass

def create_header():
    header_text = Text()
    header_text.append("🎵 ", style="bold yellow")
    header_text.append("YouTube & YouTube Music Downloader", style="bold blue")
    header_text.append(" 🎬", style="bold red")
    
    header_panel = Panel(
        header_text,
        subtitle="Download videos and music with metadata, cover art, and organized folders",
        style="bold cyan",
        box=box.DOUBLE_EDGE
    )
    return header_panel

def create_feature_columns():
    features = [
        "🎯 Smart organization",
        "📁 Playlist support", 
        "🎨 Cover art embedding",
        "🏷️ Metadata tagging",
        "📝 Lyrics saving",
        "🔄 Batch processing"
    ]
    
    feature_texts = [Text(feature, style="green") for feature in features]
    return Columns(feature_texts, equal=True, expand=True)

def download_task(opts, url_list, summary, mode, console, fmt, playlist_seq=None, album=None, do_lyrics=True, max_retries=2):
    from yt_dlp import YoutubeDL
    
    custom_columns = [
        SpinnerColumn("dots", style="blue"),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
    ]
    
    with Progress(*custom_columns, console=console) as progress:
        total_vids = len(url_list)
        failed = []
        
        for idx, url in enumerate(url_list, 1):
            retry = 0
            while retry < max_retries:
                emoji = "🎵" if mode == "audio" else "🎬"
                task_desc = f"{emoji} Downloading {idx}/{total_vids}"
                task = progress.add_task(task_desc, total=None)
                
                status = "✅ Success"
                final_path = None
                file_type = "Video"
                size = None
                
                try:
                    with YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        
                        if "requested_downloads" in info:
                            downloaded_file = info["requested_downloads"][0]
                            final_path = downloaded_file.get("filepath", "")
                        else:
                            final_path = info.get("filepath", "")
                            
                        if not final_path or not os.path.exists(final_path):
                            outtmpl = opts.get("outtmpl", "downloads/%(title)s.%(ext)s")
                            final_path = ydl.prepare_filename(info)
                            
                        if os.path.exists(final_path):
                            size = os.path.getsize(final_path)
                            
                        if mode == "audio" or (final_path and final_path.lower().endswith(tuple(['.mp3', '.flac', '.m4a']))):
                            file_type = "Audio"
                            
                            tn_url = info.get("thumbnail")
                            if not tn_url:
                                thumbnails = info.get("thumbnails", [])
                                if thumbnails:
                                    tn_url = thumbnails[-1].get("url")
                            
                            if tn_url:
                                try:
                                    img_file = download_thumbnail_convert(tn_url)
                                    if img_file:
                                        embed_cover_audiofile(final_path, img_file, fmt)
                                        console.print(f"   🖼️  Cover art embedded", style="green")
                                    else:
                                        console.print(f"   ⚠️  Cover art unavailable", style="yellow")
                                except Exception as e:
                                    console.print(f"   ⚠️  Cover art failed: {str(e)[:50]}", style="yellow")
                            else:
                                console.print(f"   ⚠️  No thumbnail found", style="yellow")
                            
                            ix = playlist_seq[idx-1] if playlist_seq else None
                            write_tags(final_path, info, fmt, ix, album)
                            console.print(f"   🏷️  Metadata added", style="green")
                            
                            if do_lyrics and info.get("description"):
                                save_yt_description(final_path, info.get("description"))
                                console.print(f"   📝 Description saved", style="green")
                                
                    summary.append([final_path if final_path else url, file_type, status, natural_size(size) if size else ""])
                    progress.remove_task(task)
                    break
                    
                except Exception as e:
                    status = f"❌ FAIL: {str(e)[:50]}..."
                    retry += 1
                    progress.remove_task(task)
                    
                    if retry >= max_retries:
                        console.print(f"   ❌ Failed to download: {str(e)[:100]}", style="red")
                        failed.append(url)
                        summary.append([final_path if final_path else url, file_type, status, natural_size(size) if size else ""])
                        break
                    else:
                        console.print(f"   🔄 Retrying ({retry}/{max_retries})...", style="yellow")
                        continue
                        
        if failed:
            console.print("\n[bold red]❌ Failed downloads:[/bold red]")
            for url in failed:
                console.print(f"   • {url}", style="red")

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
    console.print("\n[bold]🎵 Audio Format Selection[/bold]")
    formats = {
        "mp3": "• Good quality, universal compatibility",
        "m4a": "• Better quality, smaller file size", 
        "flac": "• Lossless, best quality, large files"
    }
    
    for fmt, desc in formats.items():
        console.print(f"  [cyan]{fmt.upper():>4}[/cyan] - {desc}")
    
    ch = Prompt.ask("\nChoose format", choices=["mp3", "m4a", "flac"], default="mp3")
    return ch

def show_summary_table(summary, console):
    if not summary:
        return
        
    table = Table(
        title="🎉 Download Summary",
        box=box.ROUNDED,
        header_style="bold magenta",
        title_style="bold green"
    )
    
    table.add_column("File", style="cyan", overflow="fold")
    table.add_column("Type", justify="center", style="blue")
    table.add_column("Status", justify="center", style="green")
    table.add_column("Size", justify="right", style="yellow")
    
    success_count = 0
    total_size = 0
    
    for row in summary:
        file_path, file_type, status, size_str = row
        table.add_row(file_path, file_type, status, size_str)
        
        if "Success" in status:
            success_count += 1
        if size_str and "MB" in size_str:
            try:
                size_mb = float(size_str.split()[0])
                total_size += size_mb
            except:
                pass
                
    console.print(table)
    
    if success_count > 0:
        console.print(f"\n✅ [green]Successfully downloaded {success_count} file(s)[/green]", style="bold")
        if total_size > 0:
            console.print(f"📊 Total size: {total_size:.1f} MB", style="blue")

def main():
    global console
    console = Console()
    
    while True:
        try:
            ensure_dirs()
            check_yt_dlp_update(console)
        except GracefulExit:
            sys.exit(0)
            
        console.print(create_header())
        console.print(create_feature_columns())
        console.print()
        
        config = load_config()
        last_output_folder = config.get("last_output_folder", "Downloads")
        urls = []
        
        clipboard_url = get_clipboard_url()
        if clipboard_url:
            console.print(Panel(
                f"[green]📋 Clipboard detected:[/green]\n{clipboard_url}",
                title="🔍 URL Found",
                border_style="green"
            ))
            if Confirm.ask("Use this URL?", default=True):
                urls = [clipboard_url]
                
        if not urls:
            console.print("\n[bold]🔗 Enter YouTube URL[/bold]")
            console.print("• Paste a YouTube/YouTube Music URL")
            console.print("• Type 'file' to load from text file") 
            console.print("• Type 'q' to quit\n")
            
            try:
                url_input = Prompt.ask("URL", default="")
                if url_input.lower() == 'q':
                    console.print("\n👋 [blue]Goodbye![/blue]")
                    sys.exit(0)
                if url_input.lower() == "file":
                    file_path = Prompt.ask("📁 Path to URLs file")
                    with open(file_path, encoding='utf-8') as f:
                        urls = [x.strip() for x in f if x.strip()]
                    console.print(f"📥 Loaded {len(urls)} URLs from file", style="green")
                else:
                    urls = [url_input]
            except KeyboardInterrupt:
                console.print("\n❌ [red]Operation cancelled[/red]")
                sys.exit(0)
                
        url = urls[0]
        
        console.print("\n[bold]📥 Download Type[/bold]")
        console.print("🎵 [cyan]audio[/cyan] - Music (MP3, FLAC, M4A) with metadata & cover art")
        console.print("🎬 [cyan]video[/cyan] - Video (MP4) with subtitles\n")
        
        choice = Prompt.ask("Choose type", choices=["video", "audio"], default="video")
        if choice == "audio":
            fmt = pick_audio_format()
            mode = "audio"
        else:
            mode = "video"
            fmt = "mp4"
            
        console.print(f"\n[bold]📁 Output Folder[/bold]")
        console.print(f"Files will be saved in: [cyan]{last_output_folder}[/cyan]")
        folder = Prompt.ask("Change folder", default=last_output_folder)
        
        if not os.path.exists(folder):
            os.makedirs(folder)
            console.print(f"📂 Created folder: [green]{folder}[/green]")
            
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
            console.print("\n[bold blue]📋 Playlist Detected[/bold blue]")
            
            with console.status("[bold blue]Fetching playlist information...", spinner="dots"):
                entries = fetch_playlist_entries(url)
                
            console.print(f"🎵 Found [green]{len(entries)}[/green] tracks:")
            
            preview_table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
            preview_table.add_column("#", style="dim", width=4)
            preview_table.add_column("Title", style="cyan")
            
            for e in entries[:5]:
                title = e['title'][:50] + "..." if len(e['title']) > 50 else e['title']
                preview_table.add_row(str(e['index']), title)
                
            if len(entries) > 5:
                preview_table.add_row("...", f"[dim]+ {len(entries) - 5} more tracks[/dim]")
                
            console.print(preview_table)
            
            try:
                sel = Prompt.ask(
                    "\nEnter track numbers (e.g.: 1,2,5-7) or leave blank for all",
                    default=""
                )
            except KeyboardInterrupt:
                console.print("\n❌ [red]Operation cancelled[/red]")
                sys.exit(0)
                
            if sel.strip():
                playlist_indices = parse_selection(sel, len(entries))
                opts["playlist_items"] = ",".join(str(i) for i in playlist_indices)
                console.print(f"✅ Selected [green]{len(playlist_indices)}[/green] tracks")
            else:
                playlist_indices = list(range(1, len(entries)+1))
                console.print("✅ Selected [green]all[/green] tracks")
                
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
                opts.update(dict(
                    format="bestaudio/best",
                    extractaudio=True,
                    audioformat="mp3",
                    postprocessors=[{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
                    outtmpl=outtmpl
                ))
            elif fmt == "m4a":
                opts.update(dict(
                    format="bestaudio[ext=m4a]/bestaudio/best",
                    extractaudio=True,
                    audioformat="m4a",
                    postprocessors=[{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}],
                    outtmpl=outtmpl
                ))
            elif fmt == "flac":
                opts.update(dict(
                    format="bestaudio/best",
                    extractaudio=True,
                    audioformat="flac",
                    postprocessors=[{"key": "FFmpegExtractAudio", "preferredcodec": "flac"}],
                    outtmpl=outtmpl
                ))
        else:
            outtmpl = os.path.join(folder, fnpat, "%(title)s.%(ext)s")
            opts.update(dict(
                format='bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                merge_output_format="mp4",
                outtmpl=outtmpl,
                # Disable subtitles to avoid 429 errors
                # writesubtitles=False,
                # writeautomaticsub=False,
                # sponsorblock_remove=["all"],
                # Add retries and better error handling
                retries=10,
                fragment_retries=10,
                skip_unavailable_fragments=True,
                continue_dl=True
            ))
            
        summary = []
        urls_to_download = playlist_urls if playlist_mode else urls
        
        if playlist_mode and playlist_indices:
            console.print(f"\n🎯 Ready to download [green]{len(playlist_indices)}[/green] tracks")
        else:
            console.print(f"\n🎯 Ready to download: [cyan]{urls_to_download[0]}[/cyan]")
            
        try:
            if Confirm.ask("\n🚀 Start download?", default=True):
                console.print()
                download_task(opts, urls_to_download, summary, mode, console, fmt, playlist_seq, album, True)
        except KeyboardInterrupt:
            console.print("\n❌ [red]Download interrupted[/red]")
            sys.exit(0)
            
        if summary:
            show_summary_table(summary, console)
            
            console.print()
            again = Confirm.ask("🔄 Download another batch?", default=False)
            if not again:
                try:
                    if Confirm.ask(f"📂 Open download folder?", default=True):
                        open_folder(os.path.abspath(folder))
                        console.print(f"📁 Opened: [cyan]{os.path.abspath(folder)}[/cyan]")
                except KeyboardInterrupt:
                    pass
                    
                console.print("\n🎊 [bold green]All done! Happy listening! 🎵[/bold green]")
                break
        else:
            console.print("\n❌ [red]No files were downloaded[/red]")
            break

if __name__ == '__main__':
    try:
        main()
    except GracefulExit:
        pass
    except KeyboardInterrupt:
        console.print("\n👋 [blue]Goodbye![/blue]")
        sys.exit(0)
