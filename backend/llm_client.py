import requests
import re

def get_ffmpeg_command(user_query, input_filename, input_ext, endpoint, model):
    prompt = f"""
You are an expert in FFmpeg. Your task is to convert a user's natural language instruction into a single, executable FFmpeg command.

**Constraints:**
1.  The input file will always be named '{input_filename}' (the extension will vary).
2.  The output file must always be named 'output.{input_ext}'. You will determine the correct output extension based on the user's request (e.g., 'output.mp4', 'output.gif').
3.  Do NOT generate any command that could delete or overwrite files outside of the designated output file (e.g., no 'rm', 'mv' commands).
4.  Do NOT add any explanations, apologies, or extra text. Your response must be ONLY the FFmpeg command.
5.  The command must not require user interaction (`-y` flag should be used to overwrite the output file automatically).

**User's Request:** "{user_query}"

**FFmpeg Command:**
"""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    try:
        resp = requests.post(endpoint, json=payload, timeout=200)
        resp.raise_for_status()
        data = resp.json()
        # Try to extract the command from the response
        if 'response' in data:
            raw = data['response'].strip()
        elif 'choices' in data and data['choices']:
            raw = data['choices'][0]['text'].strip()
        else:
            return None
        # Remove <think>...</think> and similar tags
        raw = re.sub(r'<think>[\s\S]*?</think>', '', raw, flags=re.IGNORECASE)
        # Find the first line that starts with ffmpeg
        for line in raw.splitlines():
            if line.strip().startswith('ffmpeg'):
                return line.strip()
        # Fallback: try to extract ffmpeg command from anywhere
        match = re.search(r'(ffmpeg[^\n]*)', raw)
        if match:
            return match.group(1).strip()
        return None
    except Exception as e:
        return None 