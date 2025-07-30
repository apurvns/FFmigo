#!/usr/bin/env python3
"""
Test script to simulate GitHub Actions build process locally
This helps verify that the build will work before creating a release
"""

import subprocess
import sys
import os
import platform
import shutil

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔨 {description}...")
    print(f"   Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed!")
        print(f"   Error: {e.stderr}")
        return False

def test_windows_build():
    """Test Windows build process"""
    print("\n🪟 Testing Windows build...")
    
    # Install dependencies
    if not run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], "Installing dependencies"):
        return False
    
    # Build executable
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--icon=ui/resources/icons/app_logo.png",
        "--name=FFMigo",
        "--add-data=style.qss;.",
        "--add-data=ui/resources/icons;ui/resources/icons",
        "--add-data=backend;backend",
        "--add-data=ui;ui",
        "main.py"
    ]
    
    if not run_command(cmd, "Building Windows executable"):
        return False
    
    # Check if executable was created
    if os.path.exists("dist/FFMigo.exe"):
        print("✅ Windows executable created: dist/FFMigo.exe")
        return True
    else:
        print("❌ Windows executable not found!")
        return False

def test_macos_build():
    """Test macOS build process"""
    print("\n🍎 Testing macOS build...")
    
    # Install dependencies
    if not run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], "Installing dependencies"):
        return False
    
    # Build application
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",
        "--windowed",
        "--icon=ui/resources/icons/app_logo.png",
        "--name=FFMigo",
        "--add-data=style.qss:.",
        "--add-data=ui/resources/icons:ui/resources/icons",
        "--add-data=backend:backend",
        "--add-data=ui:ui",
        "main.py"
    ]
    
    if not run_command(cmd, "Building macOS application"):
        return False
    
    # Check if application was created
    if os.path.exists("dist/FFMigo"):
        print("✅ macOS application created: dist/FFMigo")
        
        # Test DMG creation if create-dmg is available
        try:
            result = subprocess.run(["which", "create-dmg"], capture_output=True, text=True)
            if result.returncode == 0:
                print("📦 Testing DMG creation...")
                dmg_cmd = [
                    "create-dmg",
                    "--volname", "FFMigo",
                    "--volicon", "ui/resources/icons/app_logo.png",
                    "--window-pos", "200", "120",
                    "--window-size", "600", "400",
                    "--icon-size", "100",
                    "--icon", "FFMigo.app", "175", "120",
                    "--hide-extension", "FFMigo.app",
                    "--app-drop-link", "425", "120",
                    "FFMigo.dmg",
                    "dist/"
                ]
                
                if run_command(dmg_cmd, "Creating DMG file"):
                    if os.path.exists("FFMigo.dmg"):
                        print("✅ DMG file created: FFMigo.dmg")
                        return True
                    else:
                        print("❌ DMG file not found!")
                        return False
                else:
                    print("⚠️  DMG creation failed, but application was built successfully")
                    return True
            else:
                print("⚠️  create-dmg not available, skipping DMG creation")
                return True
        except Exception as e:
            print(f"⚠️  Could not test DMG creation: {e}")
            return True
    else:
        print("❌ macOS application not found!")
        return False

def cleanup():
    """Clean up build artifacts"""
    print("\n🧹 Cleaning up build artifacts...")
    
    dirs_to_clean = ["build", "dist", "__pycache__"]
    files_to_clean = ["FFMigo.spec", "FFMigo.dmg"]
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"   Removed: {dir_name}/")
    
    for file_name in files_to_clean:
        if os.path.exists(file_name):
            os.remove(file_name)
            print(f"   Removed: {file_name}")

def main():
    """Main test function"""
    print("🧪 FFMigo Build Test")
    print(f"📋 Platform: {platform.system()} {platform.release()}")
    
    current_platform = platform.system()
    
    try:
        if current_platform == "Windows":
            success = test_windows_build()
        elif current_platform == "Darwin":  # macOS
            success = test_macos_build()
        else:
            print(f"⚠️  Unsupported platform: {current_platform}")
            print("   This test script only supports Windows and macOS")
            return
        
        if success:
            print("\n🎉 Build test completed successfully!")
            print("✅ Your application is ready for GitHub Actions release!")
            
            if current_platform == "Windows":
                print("\n📁 Windows executable: dist/FFMigo.exe")
                print("💡 Test it: dist/FFMigo.exe")
            elif current_platform == "Darwin":
                print("\n📁 macOS application: dist/FFMigo")
                print("💡 Test it: ./dist/FFMigo/FFMigo")
                if os.path.exists("FFMigo.dmg"):
                    print("📦 DMG file: FFMigo.dmg")
        else:
            print("\n❌ Build test failed!")
            print("🔧 Please fix the issues before creating a GitHub release")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Build test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Build test error: {e}")
        sys.exit(1)
    finally:
        # Ask if user wants to clean up
        try:
            response = input("\n🧹 Clean up build artifacts? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                cleanup()
                print("✅ Cleanup completed")
        except KeyboardInterrupt:
            print("\n⏹️  Skipping cleanup")

if __name__ == "__main__":
    main() 