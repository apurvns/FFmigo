import os
import shutil
import time
from pathlib import Path
import json
import re

def get_projects_root():
    return os.path.expanduser('~/.video-editor-app/projects')

def create_project_dir():
    root = get_projects_root()
    ts = int(time.time())
    project_dir = os.path.join(root, str(ts))
    os.makedirs(project_dir, exist_ok=True)
    return project_dir

def copy_video_to_project(src_path, project_dir):
    ext = Path(src_path).suffix
    dst_path = os.path.join(project_dir, f'input{ext}')
    shutil.copy2(src_path, dst_path)
    return dst_path

def _sanitize_filename(name):
    base, ext = os.path.splitext(name)
    # Replace any non-safe characters with underscore
    safe_base = re.sub(r'[^A-Za-z0-9._-]', '_', base)
    # Prevent empty base
    if not safe_base:
        safe_base = 'asset'
    return safe_base + ext

def copy_asset_to_project(src_path, project_dir):
    """
    Copy an arbitrary asset file (image/video/text) into the project's assets directory
    using a sanitized, unique filename. Returns (relative_path_for_ffmpeg, absolute_path).
    """
    assets_dir = os.path.join(project_dir, 'assets')
    os.makedirs(assets_dir, exist_ok=True)

    original_name = os.path.basename(src_path)
    sanitized_name = _sanitize_filename(original_name)

    # Ensure uniqueness
    candidate = sanitized_name
    name_base, name_ext = os.path.splitext(sanitized_name)
    idx = 1
    while os.path.exists(os.path.join(assets_dir, candidate)) and idx < 10000:
        candidate = f"{name_base}_{idx}{name_ext}"
        idx += 1

    abs_dst = os.path.join(assets_dir, candidate)
    shutil.copy2(src_path, abs_dst)

    rel_path = os.path.join('assets', candidate)
    return rel_path, abs_dst

def list_projects():
    root = get_projects_root()
    if not os.path.exists(root):
        return []
    # Only directories with numeric names (timestamps)
    projects = [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)) and d.isdigit()]
    projects.sort(reverse=True)
    return [os.path.join(root, d) for d in projects]

def get_project_name(proj_dir):
    meta_path = os.path.join(proj_dir, '.meta.json')
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            return meta.get('name', os.path.basename(proj_dir))
        except Exception:
            pass
    return os.path.basename(proj_dir)

def rename_project(proj_dir, new_name):
    meta_path = os.path.join(proj_dir, '.meta.json')
    meta = {}
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r') as f:
                meta = json.load(f)
        except Exception:
            meta = {}
    meta['name'] = new_name
    with open(meta_path, 'w') as f:
        json.dump(meta, f)

# Checkpoint management functions
def get_next_checkpoint_number(project_dir):
    """Get the next available checkpoint number"""
    existing_checkpoints = []
    for file in os.listdir(project_dir):
        if file.startswith('checkpoint_') and file.endswith('.mp4'):
            try:
                num = int(file.split('_')[1].split('.')[0])
                existing_checkpoints.append(num)
            except (ValueError, IndexError):
                continue
    return max(existing_checkpoints, default=0) + 1

def create_checkpoint(project_dir, input_file, operation_desc, user_command):
    """Create a checkpoint before an operation"""
    checkpoint_num = get_next_checkpoint_number(project_dir)
    checkpoint_file = os.path.join(project_dir, f'checkpoint_{checkpoint_num}.mp4')
    
    # Copy the current input file to checkpoint
    shutil.copy2(input_file, checkpoint_file)
    
    # Save metadata
    meta = {
        'timestamp': time.time(),
        'operation': operation_desc,
        'user_command': user_command,
        'input_file': os.path.basename(input_file),
        'file_size': os.path.getsize(checkpoint_file),
        'checkpoint_num': checkpoint_num
    }
    save_checkpoint_metadata(project_dir, checkpoint_num, meta)
    return checkpoint_num

def save_checkpoint_metadata(project_dir, checkpoint_num, meta):
    """Save checkpoint metadata to JSON file"""
    meta_file = os.path.join(project_dir, f'checkpoint_{checkpoint_num}.json')
    with open(meta_file, 'w') as f:
        json.dump(meta, f, indent=2)

def load_checkpoint_metadata(project_dir, checkpoint_num):
    """Load checkpoint metadata from JSON file"""
    meta_file = os.path.join(project_dir, f'checkpoint_{checkpoint_num}.json')
    if os.path.exists(meta_file):
        try:
            with open(meta_file, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return None

def list_checkpoints(project_dir):
    """Get all available checkpoints for a project"""
    checkpoints = []
    for file in os.listdir(project_dir):
        if file.startswith('checkpoint_') and file.endswith('.mp4'):
            try:
                checkpoint_num = int(file.split('_')[1].split('.')[0])
                meta = load_checkpoint_metadata(project_dir, checkpoint_num)
                if meta:
                    checkpoints.append((checkpoint_num, meta))
            except (ValueError, IndexError):
                continue
    return sorted(checkpoints, key=lambda x: x[0])

def restore_checkpoint(project_dir, checkpoint_num):
    """Restore a checkpoint to become the current input file"""
    checkpoint_file = os.path.join(project_dir, f'checkpoint_{checkpoint_num}.mp4')
    print(f"[DEBUG] restore_checkpoint: checkpoint_file = {checkpoint_file}")
    print(f"[DEBUG] restore_checkpoint: checkpoint_file exists = {os.path.exists(checkpoint_file)}")
    
    if not os.path.exists(checkpoint_file):
        return False, "Checkpoint file not found"
    
    meta = load_checkpoint_metadata(project_dir, checkpoint_num)
    print(f"[DEBUG] restore_checkpoint: meta = {meta}")
    if not meta:
        return False, "Checkpoint metadata not found"
    
    # Clear old numbered input files before creating the new input file
    print(f"[DEBUG] restore_checkpoint: clearing old input files")
    for file in os.listdir(project_dir):
        if file.startswith('input_') and file.endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
            file_path = os.path.join(project_dir, file)
            print(f"[DEBUG] restore_checkpoint: removing old file {file}")
            os.remove(file_path)
    
    # Use the checkpoint file's actual extension, not the original file's extension
    checkpoint_ext = os.path.splitext(checkpoint_file)[1]
    new_input_file = os.path.join(project_dir, f'input{checkpoint_ext}')
    print(f"[DEBUG] restore_checkpoint: checkpoint_ext = {checkpoint_ext}")
    print(f"[DEBUG] restore_checkpoint: new_input_file = {new_input_file}")
    
    # Copy checkpoint to new input file
    shutil.copy2(checkpoint_file, new_input_file)
    print(f"[DEBUG] restore_checkpoint: copied {checkpoint_file} to {new_input_file}")
    
    return True, new_input_file

def get_current_input_file(project_dir):
    """Get the current input file in the project"""
    # Look for the latest input file (input.mp4, input_1.mp4, input_2.mp4, etc.)
    input_files = []
    for file in os.listdir(project_dir):
        if file.startswith('input') and file.endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
            input_files.append(file)
    
    if not input_files:
        return None
    
    # Sort by number (input.mp4 comes first, then input_1.mp4, input_2.mp4, etc.)
    def get_input_number(filename):
        if filename == 'input.mp4':
            return 0
        try:
            return int(filename.split('input_')[1].split('.')[0])
        except (ValueError, IndexError):
            return 999  # Put unknown files at the end
    
    input_files.sort(key=get_input_number)
    return os.path.join(project_dir, input_files[-1]) 