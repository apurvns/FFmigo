#!/usr/bin/env python3
"""
Simple build script for FFMigo
"""

import subprocess
import sys
import os

def build():
    print("🚀 Building FFMigo executable...")
    
    # Install required packages
    try:
        import PyInstaller
        print("✅ PyInstaller is already installed")
    except ImportError:
        print("📦 Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    try:
        import PIL
        print("✅ Pillow is already installed")
    except ImportError:
        print("📦 Installing Pillow...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pillow"], check=True)
    
    # Build command - using onedir instead of onefile for macOS
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",  # Changed from --onefile for macOS compatibility
        "--windowed",
        "--icon=ui/resources/icons/app_logo.png",
        "--name=FFMigo",
        "--add-data=style.qss:.",
        "--add-data=ui/resources/icons:ui/resources/icons",
        "--add-data=backend:backend",
        "--add-data=ui:ui",
        "main.py"
    ]
    
    print("🔨 Running:", " ".join(cmd))
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("✅ Build successful!")
        print("📁 Executable: dist/FFMigo/FFMigo")
        print("💡 Test it: ./dist/FFMigo/FFMigo")
        print("📦 You can distribute the entire 'dist/FFMigo' folder")
    else:
        print("❌ Build failed!")

if __name__ == "__main__":
    build() 