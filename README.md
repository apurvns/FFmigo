# FFMigo: Chat-Driven Video Editor

FFmigo is a smart tool designed to simplify video and audio editing by translating your plain English instructions into complex FFmpeg commands. Instead of memorizing confusing command-line options, you can simply tell FFmigo what you want to do—like "trim my video to the first 10 seconds" or "add my logo to the bottom right corner"—and it will instantly generates and executes the correct command for you.

At its core, FFmigo uses an AI to understand your request and act as your expert FFmpeg assistant, making powerful video editing accessible to everyone, from content creators to developers. You describe your editing tasks in natural language, and the app uses a local LLM (Large Language Model) to generate and run FFmpeg commands.

---

## Features
- Drag-and-drop video loading
- Chat interface for natural language video editing
- LLM integration (Ollama, LM Studio, etc.)
- Secure FFmpeg command execution
- Processed video preview, play, and export
- Configurable settings (LLM endpoint, model, FFmpeg path, export directory)

---

## Requirements
- **Python 3.10+**
- **FFmpeg** (must be installed and accessible)
- **A local LLM server** (e.g., [Ollama](https://ollama.com/), LM Studio, etc.)

---

## Installation

1. **Clone the repository**

2. **Create a virtual environment (recommended):**
   ```sh
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Install FFmpeg:**
   - **macOS:** `brew install ffmpeg`
   - **Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
   - **Linux:** `sudo apt install ffmpeg`

5. **(Optional) Set up your local LLM server:**
   - Example: [Ollama](https://ollama.com/)
   - Start your LLM server and note the API endpoint and model name

---

## Running the App

```sh
python main.py
```

---

## Configuration

- Click the **Settings** button in the app.
- Set:
  - **LLM API Endpoint** (e.g., `http://localhost:11434/api/generate`)
  - **LLM Model Name** (e.g., `llama3`)
  - **FFmpeg Path** (e.g., `ffmpeg` or full path)
  - **Default Export Directory**

---

## Usage

1. **Load a video**: Drag and drop or click the area to select a file.
2. **Enter commands**: Type natural language instructions (e.g., "trim from 10 to 20 seconds").
3. **Process**: The app will show the FFmpeg command, run it, and display the result.
4. **Play/Export**: Use the Play and Export buttons for the processed video.

---

## Troubleshooting
- If you see errors about missing modules, ensure you installed all dependencies and activated your virtual environment.
- If FFmpeg commands fail, check your FFmpeg path in Settings and test it.
- If LLM commands fail, ensure your local LLM server is running and accessible.

---

## License
MIT 
