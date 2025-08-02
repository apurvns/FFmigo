# FFMigo for macOS

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
