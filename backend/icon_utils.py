import os
from PyQt6.QtGui import QIcon

def get_app_icon_paths(base_dir=None):
    """
    Get the application icon paths (SVG and PNG).
    
    Args:
        base_dir: Base directory path. If None, uses the directory containing this file.
    
    Returns:
        tuple: (svg_path, png_path)
    """
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(__file__))  # Go up one level from backend/
    
    svg_path = os.path.join(base_dir, 'ui', 'resources', 'icons', 'app_logo.svg')
    png_path = os.path.join(base_dir, 'ui', 'resources', 'icons', 'app_logo.png')
    
    return svg_path, png_path

def load_app_icon(base_dir=None):
    """
    Load the application icon, trying PNG first (more reliable), then SVG.
    
    Args:
        base_dir: Base directory path. If None, uses the directory containing this file.
    
    Returns:
        QIcon: The loaded icon, or a null QIcon if loading failed.
    """
    svg_path, png_path = get_app_icon_paths(base_dir)
    
    # Try PNG first (more reliable)
    if os.path.exists(png_path):
        return QIcon(png_path)
    elif os.path.exists(svg_path):
        return QIcon(svg_path)
    else:
        return QIcon()  # Return null icon if neither exists
