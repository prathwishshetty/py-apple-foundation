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
```

### Audio Transcription

```python
from apple_foundation import transcribe

text = transcribe("audio.mp3", "output.txt", locale="en-US")
```

## Requirements

- macOS 26+ (Tahoe)
- Python 3.10+
- Swift toolchain (for building binaries)

## Project Structure

```
├── bin/                          # Compiled Swift binaries
├── src/apple_foundation/         # Python package
│   ├── foundation.py             # Text generation
│   ├── transcription.py          # Audio transcription
│   └── swift/                    # Swift source files
└── pyproject.toml
```
