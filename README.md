# Apple Foundation Models - Python Bindings

Python wrapper for Apple's on-device Foundation Models (macOS 26+). Provides text generation and audio transcription using native macOS APIs.

## Features

- **Text Generation**: OpenAI-like API for Apple's Foundation Models.
- **Audio Transcription**: Wrapper for macOS SpeechAnalyzer with support for streaming and redaction.
- **Structured Output**: JSON Schema support for typed responses and function calling.
- **Swift Integration**: Automatically compiles necessary Swift binaries on first use.

## Installation

```bash
# Install directly from GitHub using uv (recommended)
uv pip install "git+https://github.com/prathwish/py-apple-foundation.git"

# Or with pip
pip install "git+https://github.com/prathwish/py-apple-foundation.git"
```

## Usage

### Text Generation

The `generate` function provides a powerful interface to Apple's Large Language Models.

```python
from apple_foundation import generate

# 1. Simple Generation
print(generate("Write a haiku about coding"))

# 2. Advanced Configuration
response = generate(
    "Explain quantum computing",
    system_prompt="You are a theoretical physicist. Be concise.",
    temperature=0.8,      # 0.0 to 1.0 (Higher = more creative)
    max_tokens=100,       # Limit response length
    sampling_mode="top_p", # "greedy", "top_k", or "top_p"
    top_p=0.9,
    model="default"       # "default" or "content_tagging"
)
print(response)

# 3. Structured Output (JSON Schema)
schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["title", "summary"]
}
# Returns a Python dict
data = generate("Summarize the history of the internet", schema=schema)
print(data['title'])

# 4. Tool Calling
weather_tool = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"]
        }
    }
}
# Returns a dict with function name and arguments
call = generate("How is the weather in Tokyo?", tools=[weather_tool])
print(call)
```

### Audio Transcription

The `transcribe` function wraps the system's `SpeechAnalyzer`.

```python
from apple_foundation import transcribe

# 1. Basic Transcription
text = transcribe("interview.mp3")
print(text)

# 2. Streaming Output (Real-time feedback)
print("Transcribing...")
for segment in transcribe("interview.mp3", stream=True):
    print(segment, end="", flush=True)

# 3. Full Metadata (Timestamps, Confidence)
# Returns a dictionary with detailed segments
result = transcribe(
    "interview.mp3",
    full_metadata=True,
    locale="en-US",
    redact=True,        # Auto-redact sensitive info
    fast=False          # Set True for faster, lower accuracy
)

for segment in result["segments"]:
    start = segment["start"]
    text = segment["text"]
    print(f"[{start:.2f}s]: {text}")
```

## API Reference

### `generate()`

| Parameter | Type | Description |
|-----------|------|-------------|
| `prompt` | `str` | The input text prompt. |
| `system_prompt` | `str` | System instructions to guide the model's behavior. (Alias: `instructions`) |
| `temperature` | `float` | Controls randomness (0.0 - 2.0). Higher values yield more creative output. |
| `max_tokens` | `int` | Maximum number of tokens to generate. |
| `schema` | `dict` | JSON schema for structured output. Returns `dict` if set. |
| `tools` | `list` | List of OpenAI-style tool definitions. |
| `sampling_mode` | `str` | Strategy: `"greedy"`, `"top_k"`, or `"top_p"`. |
| `top_k` | `int` | Number of top tokens to sample from (used with `top_k` mode). |
| `top_p` | `float` | Cumulative probability threshold (used with `top_p` mode). |
| `seed` | `int` | Random seed for reproducible generation. |
| `model` | `str` | Model to use: `"default"` or `"content_tagging"`. (Alias: `use_case`) |
| `guardrails` | `str` | Safety filters: `"default"` or `"permissive"`. |

### `transcribe()`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_path` | `str` | - | Path to the audio file. |
| `locale` | `str` | `"en-US"` | Language locale code. |
| `stream` | `bool` | `False` | Yield results as they are processed (returns Iterator). |
| `fast` | `bool` | `False` | Prioritize speed over accuracy. |
| `redact` | `bool` | `False` | Redact sensitive information (e.g., names, numbers). |
| `full_metadata` | `bool` | `False` | Return JSON object with timestamps and confidence scores. |

## System Requirements

- **macOS 26 (Tahoe)** or later (Required for on-device Foundation Models).
- **Xcode 26 Command Line Tools**: Required for compiling the Swift bindings.
  ```bash
  xcode-select --install
  ```
- **Python 3.10** or later.

## Project Structure

```
├── src/apple_foundation/
│   ├── foundation.py     # Text generation logic
│   ├── transcription.py  # Audio transcription logic
│   └── swift/           # Native Swift source files
│       ├── generate.swift
│       └── transcribe.swift
├── bin/                 # Compiled binaries (auto-generated)
└── pyproject.toml       # Project configuration
```
