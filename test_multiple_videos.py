#!/usr/bin/env python3
"""
Test script for multiple video merging functionality
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend import ffmpeg_runner, project_manager

def create_test_video_files():
    """Create some test video files for testing"""
    test_dir = tempfile.mkdtemp()
    video_files = []
    
    # Create 3 test video files with different content
    for i in range(3):
        video_path = os.path.join(test_dir, f'test_video_{i}.mp4')
        
        # Use ffmpeg to create a simple test video
        cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', f'testsrc=duration=2:size=320x240:rate=1',
            '-f', 'lavfi', '-i', f'sine=frequency=1000:duration=2',
            '-c:v', 'libx264', '-c:a', 'aac', '-shortest',
            video_path
        ]
        
        try:
            import subprocess
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                video_files.append(video_path)
                print(f"Created test video: {video_path}")
            else:
                print(f"Failed to create test video {i}: {result.stderr}")
        except Exception as e:
            print(f"Error creating test video {i}: {e}")
    
    return test_dir, video_files

def test_video_merging():
    """Test the video merging functionality"""
    print("Testing video merging functionality...")
    
    # Create test videos
    test_dir, video_files = create_test_video_files()
    
    if len(video_files) < 2:
        print("Need at least 2 test videos to test merging")
        return False
    
    try:
        # Create a project directory
        project_dir = project_manager.create_project_dir()
        print(f"Created project directory: {project_dir}")
        
        # Copy videos to project
        copied_paths = project_manager.copy_multiple_videos_to_project(video_files, project_dir)
        print(f"Copied {len(copied_paths)} videos to project")
        
        # Test merging
        output_file = os.path.join(project_dir, 'merged_output.mp4')
        
        def progress_callback(message):
            print(f"Progress: {message}")
        
        print("Starting video merge...")
        result = ffmpeg_runner.merge_videos_lossless(
            copied_paths, 
            output_file, 
            project_dir, 
            progress_callback
        )
        
        if result['success']:
            print("✅ Video merge successful!")
            print(f"Output file: {output_file}")
            print(f"File size: {os.path.getsize(output_file)} bytes")
            return True
        else:
            print("❌ Video merge failed!")
            print(f"Error: {result['stderr']}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False
    finally:
        # Clean up
        try:
            shutil.rmtree(test_dir)
            if 'project_dir' in locals():
                shutil.rmtree(project_dir)
        except:
            pass

if __name__ == "__main__":
    success = test_video_merging()
    sys.exit(0 if success else 1) 