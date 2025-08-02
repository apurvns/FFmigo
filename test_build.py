#!/usr/bin/env python3
"""
Test script to verify the build process
"""

import subprocess
import os
import platform
import sys

def test_build():
    """Test the build process"""
    print("Testing FFMigo build process...")
    
    # Clean previous builds
    print("Cleaning previous builds...")
    for item in ['build', 'dist', 'FFMigo.spec']:
        if os.path.exists(item):
            if os.path.isdir(item):
                import shutil
                shutil.rmtree(item)
            else:
                os.remove(item)
    
    # Run the build
    print("Running build...")
    result = subprocess.run([sys.executable, "build_cross_platform.py"], 
                          capture_output=True, text=True)
    
    print("Build output:")
    print(result.stdout)
    if result.stderr:
        print("Build errors:")
        print(result.stderr)
    
    if result.returncode != 0:
        print("❌ Build failed!")
        return False
    
    # Check what was created
    current_platform = platform.system()
    if current_platform == "Darwin":
        expected_path = "dist/FFMigo"
        if os.path.exists(expected_path):
            print(f"✅ macOS app directory created: {expected_path}")
            
            # Check if executable exists
            executable_path = f"{expected_path}/FFMigo"
            if os.path.exists(executable_path):
                print("✅ Executable found in app directory")
            else:
                print("❌ Executable not found in app directory")
                return False
        else:
            print(f"❌ Expected app directory not found: {expected_path}")
            return False
            
    elif current_platform == "Windows":
        expected_path = "dist/FFMigo.exe"
        if os.path.exists(expected_path):
            print(f"✅ Windows executable created: {expected_path}")
        else:
            print(f"❌ Expected executable not found: {expected_path}")
            return False
    
    print("✅ Build test completed successfully!")
    return True

if __name__ == "__main__":
    success = test_build()
    sys.exit(0 if success else 1) 