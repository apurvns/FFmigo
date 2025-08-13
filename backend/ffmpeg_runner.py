import subprocess
import re
import shlex
import os
import platform
import tempfile
import shutil

def validate_ffmpeg_command(cmd):
    # Must start with ffmpeg
    if not cmd.strip().startswith('ffmpeg'):
        return False, 'Command must start with ffmpeg.'
    # Must contain input*. and output.
    if not re.search(r'input(_[0-9]+)?\.[a-zA-Z0-9]+', cmd) or 'output.' not in cmd:
        return False, 'Command must reference input*.ext and output.[ext].'
    return True, ''
    # Disallow dangerous shell metacharacters (allow colon for FFmpeg filter args)
    if re.search(r'[;&|`$]', cmd):
        return False, 'Command contains forbidden shell characters.'
    # Should be a single command
    if '\n' in cmd:
        return False, 'Command must be a single line.'
    # Output file must be exactly output.<ext> (no path, no slash, no parent dir)
    match = re.search(r'output\.([a-zA-Z0-9]+)', cmd)
    if not match:
        return False, 'Output file must be named output.<ext>.'
    output_token = f"output.{match.group(1)}"
    # Check for any slash or path in output
    if f"output/{match.group(1)}" in cmd or f"output\\{match.group(1)}" in cmd or f"../output.{match.group(1)}" in cmd or f"/output.{match.group(1)}" in cmd:
        return False, 'Output file must not contain any path or directory.'
    # Check for output.<ext> with any path prefix
    tokens = shlex.split(cmd)
    for t in tokens:
        if t.startswith('output.') and (os.path.sep in t or '/' in t or '\\' in t):
            return False, 'Output file must not contain any path or directory.'
    return True, ''

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

def run_ffmpeg_command(cmd, workdir):
    try:
        # Find FFmpeg executable
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'FFmpeg not found. Please install FFmpeg and ensure it is in your PATH or in a common installation location.',
                'returncode': -1
            }
        
        # Replace 'ffmpeg' with the full path if needed
        if cmd.strip().startswith('ffmpeg'):
            cmd = cmd.replace('ffmpeg', ffmpeg_path, 1)
        
        args = shlex.split(cmd)
        result = subprocess.run(args, cwd=workdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        } 

def repair_video(ffmpeg_path, src, dst):
    """
    Repair video by ignoring errors and re-encoding to a clean MP4/H.264/AAC container.
    """
    cmd = [
        ffmpeg_path,
        "-err_detect", "ignore_err",
        "-i", src,
        "-c:v", "libx264", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "192k",
        "-y", dst
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

def merge_videos_lossless(input_files, output_file, workdir, progress_callback=None):
    """
    Merge videos using a robust approach that handles incompatible videos.
    """
    try:
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'FFmpeg not found.',
                'returncode': -1
            }

        if progress_callback:
            progress_callback("Preparing videos for merge...")

        # Create temporary directory for intermediate files
        temp_dir = tempfile.mkdtemp(dir=workdir)
        normalized_files = []

        # Step 1: Normalize each video to the same format
        for i, video_file in enumerate(input_files):
            normalized_file = os.path.join(temp_dir, f"normalized_{i}.mp4")
            
            normalize_cmd = [
                ffmpeg_path,
                '-i', video_file,
                '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=30',
                '-af', 'aresample=44100',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-y', normalized_file
            ]
            
            if progress_callback:
                progress_callback(f"Normalizing video {i+1}/{len(input_files)}...")
            
            result = subprocess.run(normalize_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                normalized_files.append(normalized_file)
                print(f"[DEBUG] Normalized video {i}: {normalized_file}")
            else:
                print(f"[DEBUG] Failed to normalize video {i}: {result.stderr}")

        if len(normalized_files) != len(input_files):
            print("[DEBUG] Not all videos were normalized successfully")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return {'success': False, 'stdout': '', 'stderr': 'Failed to normalize all videos', 'returncode': -1}

        # Step 2: Create concat list with normalized files
        concat_file = os.path.join(temp_dir, 'concat_list.txt')
        with open(concat_file, 'w') as f:
            for nf in normalized_files:
                f.write(f"file '{os.path.abspath(nf)}'\n")

        if progress_callback:
            progress_callback("Merging normalized videos...")

        # Step 3: Concatenate the normalized files
        concat_cmd = [
            ffmpeg_path,
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',
            '-y', output_file
        ]

        print(f"[DEBUG] Running concat command: {' '.join(concat_cmd)}")
        
        result = subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        print(f"[DEBUG] Concat result: {result.returncode}")
        print(f"[DEBUG] Concat stderr: {result.stderr}")
        print(f"[DEBUG] Output file exists: {os.path.exists(output_file)}")

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }

    except Exception as e:
        print(f"[DEBUG] Exception: {str(e)}")
        # Cleanup on exception
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        return {'success': False, 'stdout': '', 'stderr': str(e), 'returncode': -1} 