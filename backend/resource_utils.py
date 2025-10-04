"""
Resource path utilities for PyInstaller bundled applications.
"""
import os
import sys


def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    
    Args:
        relative_path: Path relative to the project root
        
    Returns:
        str: Absolute path to the resource
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Development environment - use the directory containing main.py
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return os.path.join(base_path, relative_path)


def get_icon_path(icon_name):
    """
    Get the absolute path to an icon file.
    
    Args:
        icon_name: Name of the icon file (e.g., 'app_logo.png')
        
    Returns:
        str: Absolute path to the icon
    """
    return resource_path(os.path.join('ui', 'resources', 'icons', icon_name))


def get_style_path():
    """
    Get the absolute path to the style.qss file.
    
    Returns:
        str: Absolute path to style.qss
    """
    return resource_path('style.qss')
