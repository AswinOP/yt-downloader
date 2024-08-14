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

if __name__ == "__main__":
    video_url = input("Enter the YouTube video URL: ")
    download_youtube_video(video_url)
