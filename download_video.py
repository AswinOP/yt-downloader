import os
import shutil
import subprocess
import sys

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    import yt_dlp
except ImportError:
    print("yt-dlp is not installed. Installing now...")
    install_package('yt-dlp')
    import yt_dlp

def thanks():
    print("\n Thank you for using this tool ❤️")

def download_youtube_music_playlist(playlist_url):
    try:
        print("\nSearching for Youtube Music...\nPlease be patient")
        ydl_opts = {'no_warnings':True,'quiet':True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            playlist_title = info['title']
            video_titles = [video['title'] for video in info['entries']]
            video_urls = [video['id'] for video in info['entries']]

        print("\nAvailable Music to download: ", len(video_titles))

        print("\nSelect songs to download:")
        for i,(title,url) in enumerate(zip(video_titles,video_urls)):
            print(f"{i+1}.{title}({url})")

        selected_videos = input("\nEnter song numbers (space-separated), or 'all' to download all: ")

        if selected_videos.lower()=="all":
            selected_videos=list(range(len(video_titles)))
        else:
            selected_videos=[int(x)-1 for x in selected_videos.split()]

        playlist_dir = playlist_title
        os.makedirs(playlist_dir, exist_ok=True)

        ydl_opts = {
            'outtmpl':os.path.join(playlist_dir,'%(title)s.%(ext)s'),
            'format':'bestaudio/best',
            'merge_output_format':'mp3'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_urls[i] for i in selected_videos])

        print("\n\nDownload complete! files saved in the directory `", playlist_title,"`")

    except Exception as e:
        print(f"An error occurred: {e}")

def download_youtube_video_playlist(playlist_url):
    try:
        print("\nSearching for Youtube Videos...\nPlease be patient")
        ydl_opts = {'no_warnings':True,'quiet':True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            playlist_title = info['title']
            video_titles = [video['title'] for video in info['entries']]
            video_urls = [video['id'] for video in info['entries']]

        print("\nAvailable Videos to download: ", len(video_titles))

        print("\nSelect videos to download:")
        for i,(title,url) in enumerate(zip(video_titles,video_urls)):
            print(f"{i+1}.{title}({url})")

        selected_videos = input("\nEnter video numbers (space-separated), or 'all' to download all: ")

        if selected_videos.lower()=="all":
            selected_videos=list(range(len(video_titles)))
        else:
            selected_videos=[int(x)-1 for x in selected_videos.split()]

        playlist_dir = playlist_title
        os.makedirs(playlist_dir, exist_ok=True)

        ydl_opts = {
            'outtmpl':os.path.join(playlist_dir,'%(title)s.%(ext)s'),
            'format':'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'merge_output_format':'mp4'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_urls[i] for i in selected_videos])

        print("\n\nDownload completed! files saved in the directory `", playlist_title,"`")

    except Exception as e:
        print(f"An error occurred: {e}")

def determine_url_type_and_download(url):
    url_type = 0
    if("playlist" in url):
        url_type=3
    elif ("music" in url) and (("youtube" in url) or ("youtu.be" in url)):
        url_type=1
    elif (("youtube" in url) or ("youtu.be" in url)):
        url_type=2
    else:
        url_type=4

    match url_type:
        case 1:
            print("The link is of YT Music\n\n")
            download_youtube_music(url)
        case 2:
            print("The link is of Youtube\n\n")
            download_youtube_video(url)
        case 3:
            if("music" in url):
                print("\nThe link is YT Music Playlist")
                download_youtube_music_playlist(url)
            else:
                print("\nThe link is YT Video Playlist")
                download_youtube_video_playlist(url)
        case 4:
            print("\n           ⚠️INVALID LINK⚠️\n")

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
            print(f"Download completed! File saved as {info_dict.get('title', 'Unknown Title')}.{info_dict.get('ext','mp3')}")

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
    print("\nAdvanced Option Menu:-\n     1) Download Youtube Video as Music\n     2) Download Youtube Videos Playlist\n     3) Download Youtube Music Playlist\n")
    userChoice = input("Your Choice: ")
    if(userChoice == "1"):
        music_url = input("Enter the Youtube Video URL to be converted to music: ")
        download_youtube_music(music_url)
    elif(userChoice == "2"):
        video_playlist_url = input("Enter the Youtube Videos playlist URL: ")
        download_youtube_video_playlist(video_playlist_url)
    elif(userChoice == "3"):
        music_playlist_url = input("Enter the Youtube Music playlist URL: ")
        download_youtube_music_playlist(music_playlist_url)

if __name__ == "__main__":
    print("Methods Available:-\n     1) Auto Detect\n     2) Download Youtube Video\n     3) Download Youtube Music\n     4) Advanced Options")
    userChoice = input("Your Choice: ")
    if(userChoice=="2"):
        video_url = input("Enter the YouTube video URL: ")
        download_youtube_video(video_url)
    elif(userChoice=="3"):
        music_url = input("Enter the Youtube Music URL: ")
        download_youtube_music(music_url)
    elif(userChoice=="1"):
        check_url = input("Enter the URL: ")
        determine_url_type_and_download(check_url)
    elif(userChoice=="4"):
        advanced_features()

    thanks()