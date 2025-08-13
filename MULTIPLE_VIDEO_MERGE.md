# Multiple Video Merging Feature

## Overview

FFMigo now supports merging multiple video files automatically when you select or drag multiple videos. This feature performs lossless merging using FFmpeg's concat demuxer, preserving video quality without re-encoding.

## How to Use

### Drag and Drop
1. Select multiple video files from your file manager
2. Drag them onto the FFMigo drag-and-drop area
3. The app will automatically detect multiple files and start the merging process

### File Selection
1. Click on the drag-and-drop area
2. In the file dialog, hold Ctrl (or Cmd on Mac) to select multiple video files
3. Click "Open" to start the merging process

## What Happens During Merging

1. **File Copying**: All selected videos are copied to the project directory
2. **Progress Display**: A progress dialog shows the merging status
3. **Lossless Merge**: Videos are merged using FFmpeg's concat demuxer with `-c copy` (no re-encoding)
4. **Order Preservation**: Videos are merged in the exact order they were selected
5. **Output**: A single merged video file is created and loaded into the editor

## Supported Formats

The merging feature supports all video formats that FFmpeg can handle:
- MP4 (.mp4)
- MOV (.mov)
- AVI (.avi)
- MKV (.mkv)
- WebM (.webm)
- FLV (.flv)
- WMV (.wmv)

## Technical Details

### Lossless Merging
- Uses FFmpeg's concat demuxer for fast, lossless concatenation
- No video re-encoding, preserving original quality
- Maintains original codec and bitrate

### Error Handling
- If merging fails, the project directory is cleaned up
- Error messages are displayed to the user
- The app returns to the initial state

### Background Processing
- Merging happens in a background thread
- UI remains responsive during the process
- Progress updates are shown in real-time

## Limitations

- Videos should ideally have the same resolution and codec for best results
- Very large files may take longer to merge
- Some complex video formats might require re-encoding for compatibility

## Troubleshooting

If merging fails:
1. Check that FFmpeg is properly installed
2. Ensure all video files are valid and not corrupted
3. Try with videos of similar format and resolution
4. Check the error message for specific issues 