# Apple Foundation Models - Python Bindings

Python wrapper for Apple's on-device Foundation Models (macOS 26+). Provides text generation and audio transcription using native macOS APIs.

## Features

- **Text Generation**: OpenAI-like API for Apple's Foundation Models
- **Audio Transcription**: Wrapper for macOS SpeechAnalyzer
- **Structured Output**: JSON Schema support for typed responses

## Installation

```bash
# Install directly from GitHub
uv pip install "git+https://github.com/prathwish/py-apple-foundation.git"

# Or with pip
pip install "git+https://github.com/prathwish/py-apple-foundation.git"
```

Swift binaries are compiled automatically on first use.

## Usage

### Text Generation

```python
from apple_foundation import generate

# Simple generation
result = generate("Write a haiku about coding")

# With parameters
result = generate(
    "Explain quantum computing",
    system_prompt="You are a physics professor",
    temperature=0.7,
    max_tokens=500
)

# Structured output
schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"}
    }
}
result = generate("Extract title and summary", schema=schema)
print(result["title"])

# Tool calling
weather_tool = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            },
            "required": ["location"]
        }
    }
}
result = generate("What's the weather in SF?", tools=[weather_tool])
print(result) # {'function': 'get_weather', 'arguments': {'location': 'SF'}}
```

### Audio Transcription

```python
from apple_foundation import transcribe

# Basic transcription (text only)
text = transcribe("audio.mp3", locale="en-US")
print(text)

# Streaming partial results
for partial_text in transcribe("audio.mp3", stream=True):
    print(partial_text, end="\r")

# Advanced: Full metadata (JSON)
# Returns a dictionary with timestamps, confidence scores, and alternatives
result = transcribe("audio.mp3", full_metadata=True, fast=False, redact=True)
for segment in result["segments"]:
    print(f"[{segment['start']:.2f}s] {segment['text']}")
```

## System Requirements

- **macOS 26 (Tahoe)** or newer (Required for on-device Foundation Models)
- **Xcode 26 Command Line Tools**: Required for auto-compiling Swift binaries.
  ```bash
  xcode-select --install
  ```
- **Python 3.10+**

## Project Structure

```
├── bin/                          # Compiled Swift binaries
├── src/apple_foundation/         # Python package
│   ├── foundation.py             # Text generation
│   ├── transcription.py          # Audio transcription
│   └── swift/                    # Swift source files
└── pyproject.toml
```
