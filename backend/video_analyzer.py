import subprocess
import json
import os
import hashlib
import time
from pathlib import Path

# Global cache for video analysis results
_analysis_cache = {}
_cache_file = None

def init_cache(cache_dir):
    """Initialize the analysis cache with a cache directory"""
    global _cache_file
    os.makedirs(cache_dir, exist_ok=True)
    _cache_file = os.path.join(cache_dir, 'video_analysis_cache.json')
    _load_cache()

def _load_cache():
    """Load existing cache from disk"""
    global _analysis_cache
    if _cache_file and os.path.exists(_cache_file):
        try:
            with open(_cache_file, 'r') as f:
                _analysis_cache = json.load(f)
        except Exception as e:
            print(f"[WARNING] Failed to load video analysis cache: {e}")
            _analysis_cache = {}

def _save_cache():
    """Save cache to disk"""
    if _cache_file:
        try:
            with open(_cache_file, 'w') as f:
                json.dump(_analysis_cache, f, indent=2)
        except Exception as e:
            print(f"[WARNING] Failed to save video analysis cache: {e}")

def _get_file_hash(file_path):
    """Get a hash of file path + modification time for cache key"""
    try:
        stat = os.stat(file_path)
        content = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
        return hashlib.md5(content.encode()).hexdigest()
    except Exception:
        return hashlib.md5(file_path.encode()).hexdigest()

def find_ffprobe():
    """Find ffprobe executable (similar to ffmpeg finder)"""
    # Common ffprobe installation paths
    common_paths = [
        '/usr/local/bin/ffprobe',
        '/opt/homebrew/bin/ffprobe',  # Apple Silicon Homebrew
        '/usr/bin/ffprobe',
        '/opt/local/bin/ffprobe',     # MacPorts
        'C:\\ffmpeg\\bin\\ffprobe.exe',  # Windows
        'C:\\Program Files\\ffmpeg\\bin\\ffprobe.exe',  # Windows
    ]
    
    # First check if ffprobe is in PATH
    try:
        result = subprocess.run(['ffprobe', '-version'], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True, timeout=5)
        if result.returncode == 0:
            return 'ffprobe'
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Check common installation paths
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None

def analyze_video(file_path):
    """
    Analyze a video/audio file and return detailed information.
    Returns dict with video/audio specs or None if analysis fails.
    """
    if not os.path.exists(file_path):
        print(f"[ERROR] File not found for analysis: {file_path}")
        return None
    
    # Check cache first
    file_hash = _get_file_hash(file_path)
    if file_hash in _analysis_cache:
        print(f"[DEBUG] Using cached analysis for {os.path.basename(file_path)}")
        return _analysis_cache[file_hash]
    
    ffprobe_path = find_ffprobe()
    if not ffprobe_path:
        print(f"[ERROR] ffprobe not found, cannot analyze {file_path}")
        return None
    
    try:
        # Run ffprobe to get detailed media information
        cmd = [
            ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"[ERROR] ffprobe failed for {file_path}: {result.stderr}")
            return None
        
        data = json.loads(result.stdout)
        
        # Extract relevant information
        analysis = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'format': {},
            'video_streams': [],
            'audio_streams': [],
            'other_streams': []
        }
        
        # Format information
        if 'format' in data:
            fmt = data['format']
            analysis['format'] = {
                'duration': float(fmt.get('duration', 0)),
                'size': int(fmt.get('size', 0)),
                'bit_rate': int(fmt.get('bit_rate', 0)) if fmt.get('bit_rate') else None,
                'format_name': fmt.get('format_name', ''),
                'format_long_name': fmt.get('format_long_name', '')
            }
        
        # Stream information
        for stream in data.get('streams', []):
            stream_info = {
                'index': stream.get('index', 0),
                'codec_name': stream.get('codec_name', ''),
                'codec_long_name': stream.get('codec_long_name', ''),
                'codec_type': stream.get('codec_type', ''),
            }
            
            if stream['codec_type'] == 'video':
                stream_info.update({
                    'width': stream.get('width', 0),
                    'height': stream.get('height', 0),
                    'pixel_format': stream.get('pix_fmt', ''),
                    'frame_rate': _parse_frame_rate(stream.get('r_frame_rate', '0/1')),
                    'duration': float(stream.get('duration', 0)) if stream.get('duration') else None,
                    'bit_rate': int(stream.get('bit_rate', 0)) if stream.get('bit_rate') else None,
                    'sample_aspect_ratio': stream.get('sample_aspect_ratio', '1:1'),
                    'display_aspect_ratio': stream.get('display_aspect_ratio', '16:9')
                })
                analysis['video_streams'].append(stream_info)
                
            elif stream['codec_type'] == 'audio':
                stream_info.update({
                    'sample_rate': int(stream.get('sample_rate', 0)) if stream.get('sample_rate') else None,
                    'channels': stream.get('channels', 0),
                    'channel_layout': stream.get('channel_layout', ''),
                    'duration': float(stream.get('duration', 0)) if stream.get('duration') else None,
                    'bit_rate': int(stream.get('bit_rate', 0)) if stream.get('bit_rate') else None,
                })
                analysis['audio_streams'].append(stream_info)
            else:
                analysis['other_streams'].append(stream_info)
        
        # Cache the result
        _analysis_cache[file_hash] = analysis
        _save_cache()
        
        print(f"[DEBUG] Analyzed {os.path.basename(file_path)}: {len(analysis['video_streams'])}v/{len(analysis['audio_streams'])}a streams")
        return analysis
        
    except Exception as e:
        print(f"[ERROR] Exception analyzing {file_path}: {e}")
        return None

def _parse_frame_rate(rate_str):
    """Parse FFmpeg frame rate string like '25/1' to float"""
    try:
        if '/' in rate_str:
            num, den = rate_str.split('/')
            return float(num) / float(den) if float(den) != 0 else 0
        return float(rate_str)
    except (ValueError, ZeroDivisionError):
        return 0

def get_video_summary(analysis):
    """Get a human-readable summary of video analysis for LLM prompt"""
    if not analysis:
        return "No video information available"
    
    summary = []
    
    # Format info
    if analysis['format'].get('duration'):
        duration = analysis['format']['duration']
        mins = int(duration // 60)
        secs = duration % 60
        summary.append(f"Duration: {mins}:{secs:05.2f}")
    
    # Video streams
    for i, stream in enumerate(analysis['video_streams']):
        video_info = f"Video{i}: {stream['width']}x{stream['height']}"
        if stream['frame_rate']:
            video_info += f" @ {stream['frame_rate']:.2f}fps"
        if stream['pixel_format']:
            video_info += f" ({stream['pixel_format']})"
        if stream['codec_name']:
            video_info += f" [{stream['codec_name']}]"
        summary.append(video_info)
    
    # Audio streams  
    for i, stream in enumerate(analysis['audio_streams']):
        audio_info = f"Audio{i}: {stream['sample_rate']}Hz"
        if stream['channels']:
            audio_info += f" {stream['channels']}ch"
        if stream['codec_name']:
            audio_info += f" [{stream['codec_name']}]"
        summary.append(audio_info)
    
    return ", ".join(summary) 