#!/usr/bin/env python3

import os
import subprocess
import sys

def find_ffmpeg():
    """Find FFmpeg executable"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True, timeout=5)
        if result.returncode == 0:
            return 'ffmpeg'
    except:
        pass
    
    # Check common paths
    common_paths = [
        '/usr/local/bin/ffmpeg',
        '/opt/homebrew/bin/ffmpeg',
        '/usr/bin/ffmpeg',
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None

def test_merge(video1, video2, output):
    """Test simple video merge"""
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        print("FFmpeg not found!")
        return False
    
    print(f"Using FFmpeg: {ffmpeg_path}")
    print(f"Video 1: {video1}")
    print(f"Video 2: {video2}")
    print(f"Output: {output}")
    
    # Simple concat demuxer approach
    concat_file = "concat_list.txt"
    with open(concat_file, 'w') as f:
        f.write(f"file '{os.path.abspath(video1)}'\n")
        f.write(f"file '{os.path.abspath(video2)}'\n")
    
    cmd = [
        ffmpeg_path,
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file,
        '-c', 'copy',
        '-y', output
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    print(f"Return code: {result.returncode}")
    print(f"STDOUT: {result.stdout}")
    print(f"STDERR: {result.stderr}")
    
    if result.returncode == 0:
        print(f"Success! Output file exists: {os.path.exists(output)}")
        if os.path.exists(output):
            # Check file size
            size = os.path.getsize(output)
            print(f"Output file size: {size} bytes")
    else:
        print("Failed!")
    
    # Cleanup
    if os.path.exists(concat_file):
        os.remove(concat_file)
    
    return result.returncode == 0

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python debug_merge.py <video1.mp4> <video2.mp4> <output.mp4>")
        sys.exit(1)
    
    video1 = sys.argv[1]
    video2 = sys.argv[2]
    output = sys.argv[3]
    
    if not os.path.exists(video1):
        print(f"Video 1 not found: {video1}")
        sys.exit(1)
    
    if not os.path.exists(video2):
        print(f"Video 2 not found: {video2}")
        sys.exit(1)
    
    test_merge(video1, video2, output) 