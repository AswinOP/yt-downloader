import os
import threading
import yt_dlp

def download_youtube_music_multi(url,playlist_dir):
    try:
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/best[ext=mp3]',
            'merge_output_format': 'mp3',
            'outtmpl': os.path.join(playlist_dir, '%(title)s.%(ext)s'),
            'quiet':True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)

    except Exception as e:
        print(f"An error occurred: {e}")

def download_youtube_video_multi(url,playlist_dir):
    try:
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(playlist_dir, '%(title)s.%(ext)s'),
            'quiet':True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)

    except Exception as e:
        print(f"An error occurred: {e}")