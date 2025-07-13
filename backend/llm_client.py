import requests
import re

def get_ffmpeg_command(user_query, input_filename, input_ext, endpoint, model, provider='Ollama', api_key=None):
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
    import requests
    import re
    headers = {}
    payload = None
    # Provider-specific logic
    if provider == 'Ollama':
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        url = endpoint
    elif provider == 'OpenAI':
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an expert in FFmpeg. Your task is to convert a user's natural language instruction into a single, executable FFmpeg command. Only output the command, no explanation."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0,
            "stream": False
        }
        url = endpoint
    elif provider == 'Gemini':
        # Gemini uses API key in URL param
        import urllib.parse
        url = endpoint
        if "?" in url:
            url += f"&key={api_key}"
        else:
            url += f"?key={api_key}"
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ]
        }
        headers = {"Content-Type": "application/json"}
    elif provider == 'Claude':
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "max_tokens": 512,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        url = endpoint
    else:
        return None
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=200)
        resp.raise_for_status()
        data = resp.json()
        # Provider-specific response parsing
        if provider == 'Ollama':
            if 'response' in data:
                raw = data['response'].strip()
            elif 'choices' in data and data['choices']:
                raw = data['choices'][0]['text'].strip()
            else:
                return None
        elif provider == 'OpenAI':
            # OpenAI: choices[0].message.content
            if 'choices' in data and data['choices']:
                raw = data['choices'][0]['message']['content'].strip()
            else:
                return None
        elif provider == 'Gemini':
            # Gemini: candidates[0].content.parts[0].text
            candidates = data.get('candidates', [])
            if candidates and 'content' in candidates[0]:
                parts = candidates[0]['content'].get('parts', [])
                if parts and 'text' in parts[0]:
                    raw = parts[0]['text'].strip()
                else:
                    return None
            else:
                return None
        elif provider == 'Claude':
            # Claude: content in response
            if 'content' in data:
                raw = data['content'].strip()
            elif 'messages' in data and data['messages']:
                raw = data['messages'][0]['content'].strip()
            else:
                return None
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

def list_ollama_models(endpoint):
    """
    Returns a list of model names available in the local Ollama server.
    endpoint: The base URL of the Ollama API (e.g., http://localhost:11434)
    """
    import requests
    import urllib.parse
    # Remove trailing /api/generate or /api/chat if present
    base = endpoint.rstrip('/')
    if base.endswith('/api/generate') or base.endswith('/api/chat'):
        base = base[:base.rfind('/api/')]
    tags_url = urllib.parse.urljoin(base + '/', 'api/tags')
    try:
        resp = requests.get(tags_url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return [m['name'] for m in data.get('models', [])]
    except Exception as e:
        return [] 