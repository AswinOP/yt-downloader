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

def determine_url_type_and_download(url):
    url_type = 0
    if ("music" in url) and (("youtube" in url) or ("youtu.be" in url)):
        url_type=1
    elif (("youtube" in url) or ("youtu.be" in url)):
        url_type=2
    else:
        url_type=3

    match url_type:
        case 1:
            print("The link is of YT Music\n\n")
            download_youtube_music(url)
        case 2:
            print("The link is of YT Music\n\n")
            download_youtube_video(url)
        case 3:
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
            print(f"Download completed! File saved as {info_dict.get('title', 'Unkown Title')}.{info_dict.get('ext','mp3')}")

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
    print("Methods Available:-\n     1) Download Youtube Video as Music\n")
    userChoice = input("Your Choice: ")
    if(userChoice == "1"):
        music_url = input("Enter the Youtube Video to be converted to music: ")
        download_youtube_music(music_url)
    #elif(userChoice == "2"):
        #



if __name__ == "__main__":
    print("Methods Available:-\n     1) Auto Detect\n     2) Download Youtube Video\n     3) Download Youtube Music\n     4) Advanced Options")
    userChoice = input("Your Choice: ")
    if(userChoice=="2"):
        video_url = input("Enter the YouTube video URL: ")
        download_youtube_video(video_url)
        thanks()
    elif(userChoice=="3"):
        music_url = input("Enter the Youtube Music URL: ")
        download_youtube_music(music_url)
        thanks()
    elif(userChoice=="1"):
        check_url = input("Enter the URL: ")
        determine_url_type_and_download(check_url)
        thanks()
    elif(userChoice=="4"):
        advanced_features()
        thanks()