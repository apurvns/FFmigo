import os
import shutil
import time
from pathlib import Path

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

def list_projects():
    root = get_projects_root()
    if not os.path.exists(root):
        return []
    # Only directories with numeric names (timestamps)
    projects = [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)) and d.isdigit()]
    projects.sort(reverse=True)
    return [os.path.join(root, d) for d in projects] 