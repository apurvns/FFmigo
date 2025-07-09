import os
import shutil
import time
from pathlib import Path
import json

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