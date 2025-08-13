#!/usr/bin/env python3

import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.video_merger import VideoMerger

def test_merger():
    print("Testing VideoMerger...")
    
    # Test with a single video file (if available)
    test_videos = []
    
    # Look for some test videos in common locations
    possible_test_videos = [
        "test.mp4",
        "sample.mp4", 
        "video.mp4",
        "/tmp/test.mp4",
        "/Users/aaa/Desktop/test.mp4"
    ]
    
    for video in possible_test_videos:
        if os.path.exists(video):
            test_videos.append(video)
            print(f"Found test video: {video}")
    
    if not test_videos:
        print("No test videos found. Please provide video file paths as command line arguments.")
        if len(sys.argv) > 1:
            test_videos = sys.argv[1:]
            print(f"Using command line arguments: {test_videos}")
        else:
            print("Usage: python test_merger.py <video1> [video2] [video3] ...")
            return
    
    # Create merger
    merger = VideoMerger()
    
    # Test compatibility check
    print(f"\nTesting compatibility check with {len(test_videos)} videos...")
    is_compatible, info = merger.check_video_compatibility(test_videos)
    print(f"Compatible: {is_compatible}")
    print(f"Info: {info}")
    
    # Test merge
    output_path = "merged_output.mp4"
    print(f"\nTesting merge to {output_path}...")
    
    def progress_callback(percent, message):
        print(f"Progress: {percent}% - {message}")
    
    result = merger.merge_videos(test_videos, output_path, progress_callback)
    
    print(f"\nMerge result: {result}")
    
    if result.get('success'):
        print(f"Success! Output file: {output_path}")
        if os.path.exists(output_path):
            print(f"File size: {os.path.getsize(output_path)} bytes")
    else:
        print(f"Failed: {result.get('error')}")

if __name__ == "__main__":
    test_merger() 