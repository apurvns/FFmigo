#!/usr/bin/env python3
"""
Build script for FFMigo desktop application
Creates a standalone executable that can be installed on client machines
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_app():
    print("🚀 Building FFMigo Desktop Application...")
    
    # Install PyInstaller if not already installed
    try:
        import PyInstaller
        print("✅ PyInstaller is already installed")
    except ImportError:
        print("📦 Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # Clean previous builds
    if os.path.exists("dist"):
        print("🧹 Cleaning previous builds...")
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")
    
    # Create PyInstaller spec file
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('style.qss', '.'),
        ('ui/resources/icons/*', 'ui/resources/icons/'),
        ('backend/*.py', 'backend/'),
        ('ui/*.py', 'ui/'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'PyQt6.QtMultimedia',
        'PyQt6.QtMultimediaWidgets',
        'requests',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FFMigo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ui/resources/icons/app_logo.png',
)
'''
    
    with open("FFMigo.spec", "w") as f:
        f.write(spec_content)
    
    print("Created PyInstaller spec file")
    
    # Build the application
    print("🔨 Building executable...")
    
    # Platform-specific data paths
    import platform
    cmd = [
        sys.executable, "-m", "PyInstaller", 
        "--clean", 
        "--onefile", 
        "--windowed",  # No console window
        "--icon=ui/resources/icons/app_logo.png",
        "--name=FFMigo",
        "main.py"
    ]
    
    if platform.system() == "Windows":
        cmd.extend([
            "--add-data=style.qss;.",
            "--add-data=ui/resources/icons;ui/resources/icons",
            "--add-data=backend;backend",
            "--add-data=ui;ui"
        ])
    else:  # macOS and Linux
        cmd.extend([
            "--add-data=style.qss:.",
            "--add-data=ui/resources/icons:ui/resources/icons",
            "--add-data=backend:backend",
            "--add-data=ui:ui"
        ])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Build completed successfully!")
        print(f"📁 Executable location: {os.path.abspath('dist/FFMigo')}")
        
        # Create a simple installer script
        create_installer_script()
        
        print("\n🎉 FFMigo Desktop Application is ready!")
        print("📦 Users can now install and run FFMigo without Python")
        print("💡 The executable is in the 'dist' folder")
        
    else:
        print("❌ Build failed!")
        print("Error output:")
        print(result.stderr)
        return False
    
    return True

def create_installer_script():
    """Create a simple installer script for the built application"""
    
    # macOS installer script
    mac_installer = '''#!/bin/bash
# FFMigo Installer for macOS

echo "🚀 Installing FFMigo..."

# Create Applications directory if it doesn't exist
mkdir -p /Applications

# Copy the application
cp -R "dist/FFMigo" /Applications/

# Make it executable
chmod +x /Applications/FFMigo

echo "✅ FFMigo has been installed to /Applications/"
echo "🎉 You can now launch FFMigo from your Applications folder!"
'''
    
    with open("install_macos.sh", "w") as f:
        f.write(mac_installer)
    
    # Make installer script executable
    os.chmod("install_macos.sh", 0o755)
    
    print("📝 Created macOS installer script: install_macos.sh")

def create_readme():
    """Create a README for the built application"""
    
    readme_content = '''# FFMigo Desktop Application

## Installation

### macOS
1. Download the FFMigo executable
2. Run the installer: `./install_macos.sh`
3. Launch FFMigo from Applications folder

### Manual Installation
1. Copy the `FFMigo` executable to your desired location
2. Make it executable: `chmod +x FFMigo`
3. Run: `./FFMigo`

## Requirements
- macOS 10.14 or later
- FFmpeg installed on the system (required for video processing)
- Local LLM server (Ollama, LM Studio, etc.)

## Features
- Drag-and-drop video loading
- Natural language video editing commands
- LLM integration for AI-powered editing
- Processed video preview and export
- Custom application icon

## Troubleshooting
- If FFmpeg is not found, install it: `brew install ffmpeg`
- If the app doesn't start, check that FFmpeg is in your PATH
- For LLM issues, ensure your local LLM server is running

## Support
For issues or questions, please check the main project documentation.
'''
    
    with open("BUILD_README.md", "w") as f:
        f.write(readme_content)
    
    print("📖 Created BUILD_README.md with installation instructions")

if __name__ == "__main__":
    try:
        success = build_app()
        if success:
            create_readme()
            print("\n🎯 Next steps:")
            print("1. Test the executable: ./dist/FFMigo")
            print("2. Run installer: ./install_macos.sh")
            print("3. Distribute the executable to users")
        else:
            print("❌ Build failed. Check the error messages above.")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Build error: {e}")
        sys.exit(1) 