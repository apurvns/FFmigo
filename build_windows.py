#!/usr/bin/env python3
"""
Windows-specific build script for FFMigo
Run this on a Windows machine to build the Windows executable
"""

import subprocess
import sys
import os

def build_windows():
    print("Building FFMigo for Windows...")
    
    # Install dependencies
    try:
        import PyInstaller
        print("PyInstaller is already installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    try:
        import PIL
        print("Pillow is already installed")
    except ImportError:
        print("Installing Pillow...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pillow"], check=True)
    
    # Windows build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",  # Single executable for Windows
        "--windowed",  # No console window
        "--icon=ui/resources/icons/app_logo.png",
        "--name=FFMigo",
        "--add-data=style.qss;.",
        "--add-data=ui/resources/icons;ui/resources/icons",
        "--add-data=backend;backend",
        "--add-data=ui;ui",
        "main.py"
    ]
    
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("Windows build successful!")
        print("Executable: dist/FFMigo.exe")
        print("Test it: dist/FFMigo.exe")
        print("Distribute the 'FFMigo.exe' file to Windows users")
        
        # Create Windows installer
        create_windows_installer()
        
    else:
        print("Windows build failed!")

def create_windows_installer():
    """Create a Windows installer script"""
    installer_content = '''@echo off
REM FFMigo Windows Installer

echo Installing FFMigo...

REM Create Program Files directory
if not exist "C:\\Program Files\\FFMigo" mkdir "C:\\Program Files\\FFMigo"

REM Copy the application
xcopy "dist\\FFMigo.exe" "C:\\Program Files\\FFMigo\\" /Y

REM Create desktop shortcut
echo Creating desktop shortcut...
powershell "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\\Desktop\\FFMigo.lnk'); $Shortcut.TargetPath = 'C:\\Program Files\\FFMigo\\FFMigo.exe'; $Shortcut.Save()"

REM Create start menu shortcut
if not exist "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\FFMigo" mkdir "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\FFMigo"
powershell "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\FFMigo\\FFMigo.lnk'); $Shortcut.TargetPath = 'C:\\Program Files\\FFMigo\\FFMigo.exe'; $Shortcut.Save()"

echo FFMigo has been installed to C:\Program Files\FFMigo\
echo You can now launch FFMigo from your Desktop or Start Menu!
pause
'''
    
    with open("install_windows.bat", "w") as f:
        f.write(installer_content)
    
    print("Created Windows installer: install_windows.bat")

if __name__ == "__main__":
    build_windows() 