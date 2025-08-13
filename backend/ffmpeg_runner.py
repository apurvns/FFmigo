import subprocess
import re
import shlex
import os
import platform

def validate_ffmpeg_command(cmd):
    # Must start with ffmpeg
    if not cmd.strip().startswith('ffmpeg'):
        return False, 'Command must start with ffmpeg.'
    # Must contain input*. and output.
    if not re.search(r'input(_[0-9]+)?\.[a-zA-Z0-9]+', cmd) or 'output.' not in cmd:
        return False, 'Command must reference input*.ext and output.[ext].'
    
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
        
        # Add timeout to prevent hanging (30 minutes for video processing)
        result = subprocess.run(args, cwd=workdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1800)
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': 'FFmpeg command timed out after 30 minutes. The operation may have failed or taken too long.',
            'returncode': -1
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        } 