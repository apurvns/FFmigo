# FFMigo for macOS

## Installation

### Automatic Installation
1. Download the FFMigo application
2. Run: `./install_macos.sh`
3. Launch FFMigo from Applications folder

### Manual Installation
1. Copy the `FFMigo` folder to your desired location
2. Make it executable: `chmod +x FFMigo/FFMigo`
3. Run: `./FFMigo/FFMigo`

## Requirements
- macOS 10.14 or later
- FFmpeg installed on the system
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
