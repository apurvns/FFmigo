import subprocess
import os

def find_ffmpeg():
    """Find FFmpeg executable in common locations"""
    # Common FFmpeg installation paths
    common_paths = [
        '/usr/local/bin/ffmpeg',
        '/opt/homebrew/bin/ffmpeg',  # Apple Silicon Homebrew
        '/usr/bin/ffmpeg',
        '/opt/local/bin/ffmpeg',     # MacPorts
        'C:\\ffmpeg\\bin\\ffmpeg.exe',  # Windows
        'C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe',  # Windows
    ]
    
    # First check if ffmpeg is in PATH
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True, timeout=5)
        if result.returncode == 0:
            return 'ffmpeg'
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Check common installation paths
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None

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