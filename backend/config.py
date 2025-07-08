import os
import json

def get_config_path():
    return os.path.expanduser('~/.video-editor-app/config.json')

def get_config():
    path = get_config_path()
    if not os.path.exists(path):
        return {
            'llm_endpoint': 'http://localhost:11434/api/generate',
            'llm_model': 'qwen3:latest',
            'ffmpeg_path': 'ffmpeg',
            'export_dir': os.path.expanduser('~'),
        }
    with open(path, 'r') as f:
        return json.load(f)

def save_config(settings):
    path = get_config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(settings, f, indent=2) 