#!/usr/bin/env python3
"""
Simple test script to verify FFmpeg merge functionality
"""

import os
import sys
import subprocess
import tempfile

def test_ffmpeg_merge():
    """Test FFmpeg merge with the exact same command structure"""
    
    # Get the project directory from command line or use a test one
    if len(sys.argv) > 1:
        project_dir = sys.argv[1]
    else:
        print("Usage: python test_ffmpeg_merge.py <project_directory>")
        print("Example: python test_ffmpeg_merge.py ~/.video-editor-app/projects/1234567890")
        return False
    
    print(f"Testing FFmpeg merge in directory: {project_dir}")
    
    # Check if input files exist
    input_files = []
    for i in range(10):  # Check for up to 10 input files
        if i == 0:
            test_file = os.path.join(project_dir, 'input.mp4')
        else:
            test_file = os.path.join(project_dir, f'input_{i}.mp4')
        
        if os.path.exists(test_file):
            input_files.append(test_file)
            print(f"Found input file: {test_file}")
        else:
            break
    
    if len(input_files) < 2:
        print("Need at least 2 input files to test merging")
        return False
    
    # Create concat file
    concat_file = os.path.join(project_dir, 'test_concat_list.txt')
    with open(concat_file, 'w') as f:
        for input_file in input_files:
            rel_path = os.path.relpath(input_file, project_dir)
            f.write(f"file '{rel_path}'\n")
    
    print(f"Created concat file: {concat_file}")
    print("Concat file contents:")
    with open(concat_file, 'r') as f:
        print(f.read())
    
    # Test output file
    output_file = os.path.join(project_dir, 'input.mp4')
    
    # Build FFmpeg command
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', 'test_concat_list.txt',
        '-c', 'copy',
        '-avoid_negative_ts', 'make_zero',
        output_file
    ]
    
    print(f"FFmpeg command: {' '.join(cmd)}")
    print(f"Working directory: {project_dir}")
    print(f"Output file: {output_file}")
    
    # Run FFmpeg
    print("\nRunning FFmpeg...")
    try:
        result = subprocess.run(
            cmd,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60  # 1 minute timeout
        )
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        
        if result.returncode == 0:
            print(f"✅ Success! Output file created: {output_file}")
            print(f"Output file size: {os.path.getsize(output_file)} bytes")
            return True
        else:
            print("❌ FFmpeg failed!")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ FFmpeg timed out after 1 minute")
        return False
    except Exception as e:
        print(f"❌ Error running FFmpeg: {e}")
        return False
    finally:
        # Clean up test files
        try:
            os.remove(concat_file)
            if os.path.exists(output_file):
                os.remove(output_file)
        except:
            pass

if __name__ == "__main__":
    success = test_ffmpeg_merge()
    sys.exit(0 if success else 1) 