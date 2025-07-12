import subprocess
import re
import shlex
import os

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

def run_ffmpeg_command(cmd, workdir):
    try:
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