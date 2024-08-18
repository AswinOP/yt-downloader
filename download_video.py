import os
import subprocess
import sys
import threading
import threading_downloading
from converter import choose_and_convert

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    import yt_dlp
except ImportError:
    print("yt-dlp is not installed. Installing now...")
    install_package('yt-dlp')
    import yt_dlp

def thanks():
    print("\nThank you for using this tool ❤️")

def download_youtube_music_playlist(playlist_url):
    try:
        print("\nSearching for Youtube Music...\nPlease be patient")
        ydl_opts ={'quiet':True,'force-generic-extractor':True,'extract_flat':True}
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            playlist_title = info['title']
            video_titles = [video['title'] for video in info['entries']]
            video_urls = [video['url'] for video in info['entries']]

        print("\nAvailable Music to download: ", len(video_titles))

        print("\nSelect songs to download:")
        for i, (title, url) in enumerate(zip(video_titles, video_urls)):
            print(f"{i+1}. {title} ({url})")

        selected_videos = input("\nEnter song numbers (space-separated), or 'all' to download all: ")

        if selected_videos.lower() == "all":
            selected_videos = list(range(len(video_titles)))
        else:
            selected_videos = [int(x) - 1 for x in selected_videos.split()]

        playlist_dir = playlist_title
        os.makedirs(playlist_dir, exist_ok=True)

        threads = []
        for i in selected_videos:
            url = video_urls[i]
            print("Downloading Music - ", url)
            thread = threading.Thread(target=threading_downloading.download_youtube_music_multi,args=(url,playlist_dir,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        print("\n\nDownload complete! Files saved in the directory `", playlist_title, "`")

    except Exception as e:
        print(f"An error occurred: {e}")

def download_youtube_video_playlist(playlist_url):
    try:
        print("\nSearching for Youtube Videos...\nPlease be patient")
        ydl_opts ={'quiet':True,'force-generic-extractor':True,'extract_flat':True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url,download=False)
            playlist_title = info['title']
            video_urls=[entry['url'] for entry in info['entries']]
            video_titles = [video['title'] for video in info['entries']]

        print("\nAvailable Videos to download: ", len(video_titles))
        print("\nSelect videos to download:")
        for i, (title, url) in enumerate(zip(video_titles, video_urls)):
            print(f"{i+1}. {title} ({url})")

        selected_videos = input("\nEnter video numbers (space-separated), or 'all' to download all: ")

        if selected_videos.lower() == "all":
            selected_videos = list(range(len(video_titles)))
        else:
            selected_videos = [int(x) - 1 for x in selected_videos.split()]

        playlist_dir = playlist_title
        os.makedirs(playlist_dir, exist_ok=True)

        threads = []
        for i in selected_videos:
            url = video_urls[i]
            print("Downloading Video - ", url)
            thread = threading.Thread(target=threading_downloading.download_youtube_video_multi,args=(url,playlist_dir,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        print("\n\nDownload completed! Files saved in the directory `", playlist_title, "`")

    except Exception as e:
        print(f"An error occurred: {e}")

def determine_url_type_and_download(url):
    if "playlist" in url:
        if "music" in url:
            print("\nThe link is YT Music Playlist")
            download_youtube_music_playlist(url)
        else:
            print("\nThe link is YT Video Playlist")
            download_youtube_video_playlist(url)
    elif "music" in url and ("youtube" in url or "youtu.be" in url):
        print("The link is of YT Music\n\n")
        download_youtube_music(url)
    elif "youtube" in url or "youtu.be" in url:
        print("The link is of Youtube\n\n")
        download_youtube_video(url)
    else:
        print("\n⚠️INVALID LINK⚠️\n")

def download_youtube_music(url):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'merge_output_format': 'mp3',
            'outtmpl': '%(title)s.%(ext)s'
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            print(f"Title: {info_dict.get('title', 'Unknown Title')}")
            print(f"Download completed! File saved as {info_dict.get('title', 'Unknown Title')}.{info_dict.get('ext', 'mp3')}")

    except Exception as e:
        print(f"An error occurred: {e}")

def download_youtube_video(url):
    try:
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'outtmpl': '%(title)s.%(ext)s',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            print(f"Title: {info_dict.get('title', 'Unknown Title')}")
            print(f"Download completed! File saved as {info_dict.get('title', 'Unknown Title')}.{info_dict.get('ext', 'mp4')}")

    except Exception as e:
        print(f"An error occurred: {e}")

def advanced_features():
    print("\nAdvanced Option Menu:")
    print("     1) Download Youtube Video as Music")
    print("     2) Download Youtube Videos Playlist")
    print("     3) Download Youtube Music Playlist")
    print("     4) Extract Music (.mp3) from Videos (.mp4)")
    print("     5) Go Back")
    
    user_choice = input("Your Choice: ")
    
    if user_choice == "1":
        music_url = input("Enter the Youtube Video URL to be converted to music: ")
        download_youtube_music(music_url)
    elif user_choice == "2":
        video_playlist_url = input("Enter the Youtube Videos playlist URL: ")
        download_youtube_video_playlist(video_playlist_url)
    elif user_choice == "3":
        music_playlist_url = input("Enter the Youtube Music playlist URL: ")
        download_youtube_music_playlist(music_playlist_url)
    elif user_choice == '4':
        choose_and_convert()
    elif user_choice == "5":
        main_methods()

def main_methods():
    print("Methods Available:")
    print("     1) Auto Detect")
    print("     2) Download Youtube Video")
    print("     3) Download Youtube Music")
    print("     4) Advanced Options")
    
    user_choice = input("Your Choice: ")
    
    if user_choice == "2":
        video_url = input("Enter the YouTube video URL: ")
        download_youtube_video(video_url)
    elif user_choice == "3":
        music_url = input("Enter the Youtube Music URL: ")
        download_youtube_music(music_url)
    elif user_choice == "1":
        check_url = input("Enter the URL: ")
        determine_url_type_and_download(check_url)
    elif user_choice == "4":
        advanced_features()

if __name__ == "__main__":
    main_methods()
    thanks()
