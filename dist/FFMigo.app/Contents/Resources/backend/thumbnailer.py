import subprocess

def generate_thumbnail(video_path, thumbnail_path):
    cmd = [
        'ffmpeg',
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