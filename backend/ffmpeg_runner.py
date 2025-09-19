import subprocess
import re
import shlex
import os
import platform

def validate_ffmpeg_command(cmd):
    """
    Validate FFmpeg command for security and basic correctness.
    Blocks dangerous patterns while allowing valid commands.
    """
    cmd = cmd.strip()
    
    # Must start with ffmpeg
    if not cmd.startswith('ffmpeg'):
        return False, 'Command must start with ffmpeg.'
    
    
    # Block attempts to execute other programs
    dangerous_programs = ['rm ', 'del ', 'format ', 'mkfs', 'dd ', 'shutdown', 'reboot', 'sudo ', 'su ', 'chmod ', 'chown ']
    for prog in dangerous_programs:
        if prog in cmd.lower():
            return False, f'Command attempts to execute dangerous program: {prog.strip()}'
    
    # Block path traversal attempts
    path_traversal_patterns = ['../', '..\\', '/etc/', '/bin/', '/usr/bin/', '/sbin/', '/usr/sbin/', '/root/', '/home/', 'C:\\', 'D:\\', 'E:\\']
    for pattern in path_traversal_patterns:
        if pattern in cmd:
            return False, f'Command contains path traversal attempt: {pattern}'
    
    # Block attempts to write to system directories or outside project
    system_write_patterns = ['/tmp/', '/var/', '/proc/', '/sys/', 'C:\\Windows\\', 'C:\\Program Files\\', 'C:\\ProgramData\\']
    for pattern in system_write_patterns:
        if pattern in cmd.lower():
            return False, f'Command attempts to write to system directory: {pattern}'
    
    # Must contain valid input and output references (basic check)
    # Allow flexible input patterns: input.ext, input_1.ext, etc.
    input_pattern = r'input(_\d+)?\.[a-zA-Z0-9]+'
    if not re.search(input_pattern, cmd):
        return False, 'Command must reference input file in format input.ext or input_N.ext'
    
    # Must contain output reference
    if 'output.' not in cmd:
        return False, 'Command must reference output file as output.ext'
    
    # Block multiple output files (security concern)
    output_count = cmd.count('output.')
    if output_count > 1:
        return False, 'Command cannot have multiple output files'
    
    
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