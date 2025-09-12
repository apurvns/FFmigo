import subprocess
import os
from .ffmpeg_runner import find_ffmpeg

def generate_thumbnail(video_path, thumbnail_path):
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        return False
        
    cmd = [
        ffmpeg_path,
        '-ss', '00:00:01',
        '-i', video_path,
        '-frames:v', '1',
        '-q:v', '2',
        thumbnail_path,
        '-y'
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except subprocess.CalledProcessError:
        return False 