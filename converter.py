import os
import subprocess

def convert_specific_mp4_to_mp3(filename):
    if filename.endswith('.mp4'):
        mp3_file = filename.replace('.mp4', '.mp3')
        command = ['ffmpeg', '-i', filename, '-q:a', '0', '-map', 'a', mp3_file]
        subprocess.run(command, check=True)
        print(f"Converted {filename} to {mp3_file}")
    else:
        print(f"File {filename} is not an .mp4 file.")

def list_mp4_files(directory='.'):
    mp4_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.mp4'):
                mp4_files.append(os.path.join(root, file))
    if not mp4_files:
        print("No .mp4 files found.")
    return mp4_files

def choose_and_convert():
    mp4_files = list_mp4_files()
    if mp4_files:
        print("Available .mp4 files:\n")
        for idx, file in enumerate(mp4_files, start=1):
            print(f"{idx}. {file}")
        
        try:
            choice = int(input("Enter the number of the file you want to convert: ")) - 1
            if 0 <= choice < len(mp4_files):
                convert_specific_mp4_to_mp3(mp4_files[choice])
            else:
                print("Invalid choice. Please run the script again.")
        except ValueError:
            print("Please enter a valid number.")
