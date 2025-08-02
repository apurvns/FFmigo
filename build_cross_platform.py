#!/usr/bin/env python3
"""
Cross-platform build script for FFMigo
Supports both macOS and Windows builds
"""

import subprocess
import sys
import os
import platform

def install_dependencies():
    """Install required packages for building"""
    print("Installing build dependencies...")
    
    packages = ["pyinstaller", "pillow"]
    
    for package in packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"{package} is already installed")
        except ImportError:
            print(f"Installing {package}...")
            subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)

def build_for_platform():
    """Build for the current platform"""
    current_platform = platform.system()
    print(f"Building for {current_platform}...")
    
    # Base command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--windowed",
        "--icon=ui/resources/icons/app_logo.png",
        "--name=FFMigo",
        "main.py"
    ]
    
    # Platform-specific data paths
    if current_platform == "Darwin":  # macOS
        cmd.extend([
            "--add-data=style.qss:.",
            "--add-data=ui/resources/icons:ui/resources/icons",
            "--add-data=backend:backend",
            "--add-data=ui:ui"
        ])
    elif current_platform == "Windows":
        cmd.extend([
            "--add-data=style.qss;.",
            "--add-data=ui/resources/icons;ui/resources/icons",
            "--add-data=backend;backend",
            "--add-data=ui;ui"
        ])
    
    # Platform-specific options
    if current_platform == "Darwin":  # macOS
        cmd.insert(3, "--onedir")  # Use onedir for macOS
        cmd.extend(["--windowed"])  # Create a proper app bundle
        print("Building macOS application...")
    elif current_platform == "Windows":
        cmd.insert(3, "--onefile")  # Use onefile for Windows
        print("Building Windows executable...")
    else:
        print(f"Unsupported platform: {current_platform}")
        return False
    
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("Build successful!")
        
        if current_platform == "Darwin":
            # Create proper .app bundle structure
            print("Creating macOS .app bundle...")
            app_bundle_path = "dist/FFMigo.app"
            contents_path = f"{app_bundle_path}/Contents"
            macos_path = f"{contents_path}/MacOS"
            resources_path = f"{contents_path}/Resources"
            
            # Create directory structure
            os.makedirs(macos_path, exist_ok=True)
            os.makedirs(resources_path, exist_ok=True)
            
            # Move the built executable to MacOS directory
            if os.path.exists("dist/FFMigo/FFMigo"):
                os.rename("dist/FFMigo/FFMigo", f"{macos_path}/FFMigo")
            
            # Move all other files to Resources
            if os.path.exists("dist/FFMigo"):
                for item in os.listdir("dist/FFMigo"):
                    if item != "FFMigo":  # Skip the executable we already moved
                        src = f"dist/FFMigo/{item}"
                        dst = f"{resources_path}/{item}"
                        if os.path.isdir(src):
                            import shutil
                            shutil.move(src, dst)
                        else:
                            os.rename(src, dst)
                
                # Remove the original directory
                import shutil
                shutil.rmtree("dist/FFMigo")
            
            # Create Info.plist
            info_plist = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>FFMigo</string>
    <key>CFBundleIdentifier</key>
    <string>com.ffmigo.app</string>
    <key>CFBundleName</key>
    <string>FFMigo</string>
    <key>CFBundleDisplayName</key>
    <string>FFMigo</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.14</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>'''
            
            with open(f"{contents_path}/Info.plist", "w") as f:
                f.write(info_plist)
            
            print(f"macOS App Bundle: {app_bundle_path}")
            print(f"Test it: open {app_bundle_path}")
            print("Distribute the FFMigo.app bundle")
        elif current_platform == "Windows":
            print("Windows Executable: dist/FFMigo.exe")
            print("Test it: dist/FFMigo.exe")
            print("Distribute the 'FFMigo.exe' file")
        
        return True
    else:
        print("Build failed!")
        return False

def create_installer_scripts():
    """Create installer scripts for the built application"""
    current_platform = platform.system()
    
    if current_platform == "Darwin":
        # macOS installer script
        mac_installer = '''#!/bin/bash
# FFMigo Installer for macOS

echo "Installing FFMigo..."

# Create Applications directory if it doesn't exist
mkdir -p /Applications

# Copy the application bundle
cp -R "dist/FFMigo.app" /Applications/

# Make it executable
chmod +x /Applications/FFMigo.app/Contents/MacOS/FFMigo

echo "FFMigo has been installed to /Applications/"
echo "You can now launch FFMigo from your Applications folder!"
'''
        
        with open("install_macos.sh", "w") as f:
            f.write(mac_installer)
        os.chmod("install_macos.sh", 0o755)
        print("Created macOS installer: install_macos.sh")
        
    elif current_platform == "Windows":
        # Windows installer script (batch file)
        win_installer = '''@echo off
REM FFMigo Installer for Windows

echo Installing FFMigo...

REM Create Program Files directory if it doesn't exist
if not exist "C:\\Program Files\\FFMigo" mkdir "C:\\Program Files\\FFMigo"

REM Copy the application
xcopy "dist\\FFMigo.exe" "C:\\Program Files\\FFMigo\\" /Y

REM Create desktop shortcut
echo Creating desktop shortcut...
powershell "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\\Desktop\\FFMigo.lnk'); $Shortcut.TargetPath = 'C:\\Program Files\\FFMigo\\FFMigo.exe'; $Shortcut.Save()"

echo FFMigo has been installed to C:\Program Files\FFMigo\
echo You can now launch FFMigo from your Desktop or Start Menu!
pause
'''
        
        with open("install_windows.bat", "w") as f:
            f.write(win_installer)
        print("Created Windows installer: install_windows.bat")

def create_distribution_readme():
    """Create a README for distribution"""
    current_platform = platform.system()
    
    if current_platform == "Darwin":
        readme_content = '''# FFMigo for macOS

## Installation

### Automatic Installation
1. Download the FFMigo application
2. Run: `./install_macos.sh`
3. Launch FFMigo from Applications folder

### Manual Installation
1. Copy the `FFMigo.app` bundle to your desired location
2. Run: `open FFMigo.app`

## Requirements
- macOS 10.14 or later
- FFmpeg installed on the system
- Local LLM server (Ollama, LM Studio, etc.)

## FFmpeg Installation
FFMigo requires FFmpeg to be installed on your system. Here are the recommended installation methods:

### Using Homebrew (Recommended)
```bash
brew install ffmpeg
```

### Using MacPorts
```bash
sudo port install ffmpeg
```

### Manual Installation
1. Download FFmpeg from https://ffmpeg.org/download.html
2. Extract and add to your PATH

## Features
- Drag-and-drop video loading
- Natural language video editing commands
- LLM integration for AI-powered editing
- Processed video preview and export
- Custom application icon

## Troubleshooting
- If FFmpeg is not found, install it using one of the methods above
- The app will automatically search for FFmpeg in common installation locations
- For LLM issues, ensure your local LLM server is running
- If the app doesn't start, check that FFmpeg is properly installed
'''
    elif current_platform == "Windows":
        readme_content = '''# FFMigo for Windows

## Installation

### Automatic Installation
1. Download the FFMigo executable
2. Run: `install_windows.bat`
3. Launch FFMigo from Desktop or Start Menu

### Manual Installation
1. Copy `FFMigo.exe` to your desired location
2. Run: `FFMigo.exe`

## Requirements
- Windows 10 or later
- FFmpeg installed on the system
- Local LLM server (Ollama, LM Studio, etc.)

## Features
- Drag-and-drop video loading
- Natural language video editing commands
- LLM integration for AI-powered editing
- Processed video preview and export
- Custom application icon

## Troubleshooting
- If FFmpeg is not found, download from https://ffmpeg.org/
- Add FFmpeg to your system PATH
- For LLM issues, ensure your local LLM server is running
'''
    
    with open("DISTRIBUTION_README.md", "w") as f:
        f.write(readme_content)
    
    print("📖 Created DISTRIBUTION_README.md")

def main():
    """Main build function"""
    print("FFMigo Cross-Platform Build System")
    print(f"Platform: {platform.system()} {platform.release()}")
    
    try:
        # Install dependencies
        install_dependencies()
        
        # Build for current platform
        success = build_for_platform()
        
        if success:
            # Create installer scripts
            create_installer_scripts()
            
            # Create distribution README
            create_distribution_readme()
            
            print("\nBuild completed successfully!")
            print("Your application is ready for distribution!")
            
            current_platform = platform.system()
            if current_platform == "Darwin":
                print("\nNext steps:")
                print("1. Test: ./dist/FFMigo/FFMigo")
                print("2. Install: ./install_macos.sh")
                print("3. Distribute the 'dist/FFMigo' folder")
            elif current_platform == "Windows":
                print("\nNext steps:")
                print("1. Test: dist/FFMigo.exe")
                print("2. Install: install_windows.bat")
                print("3. Distribute the 'FFMigo.exe' file")
        else:
            print("Build failed. Check the error messages above.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Build error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 