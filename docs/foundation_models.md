# Foundation Models Python API

This module provides a Python interface to Apple's on-device Foundation Models (macOS 26+).

## Installation

No additional dependencies required. The module wraps the compiled `bin/generate` CLI.

## Usage

```python
from src.foundation_service import generate

# Simple text generation
response = generate("Summarize the key points of machine learning")
print(response)

# With parameters
response = generate(
    "Write a creative story",
    temperature=1.5,  # More creative
    max_tokens=500
)

# Structured output with JSON Schema
schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "keywords": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["title", "summary"]
}
result = generate("Extract metadata from this article...", schema=schema)
print(result["title"])  # Typed access
```

## API Reference

### `generate(prompt, **options)`

#### Core Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | `str` | Required | The input prompt |
| `temperature` | `float` | None | 0.0-2.0. Higher = more creative |
| `max_tokens` | `int` | None | Maximum response tokens |
| `schema` | `dict` | None | JSON Schema for structured output |

#### Phase 1 Parameters (New!)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `system_prompt` | `str` | None | System-level instructions (alias: `instructions`) |
| `sampling_mode` | `str` | None | `"greedy"`, `"top_k"`, or `"top_p"` |
| `top_k` | `int` | None | Top-K sampling (default in CLI: 40) |
| `top_p` | `float` | None | Nucleus sampling threshold (default: 0.9) |
| `seed` | `int` | None | Random seed for reproducibility |
| `model` | `str` | `"default"` | `"default"` or `"content_tagging"` (alias: `use_case`) |
| `guardrails` | `str` | `"default"` | `"default"` (strict) or `"permissive"` |

**Returns:** `str` (plain text) or `dict` (if schema provided)

### Extended Examples

```python
from src.foundation_service import generate

# 1. System Prompts - Control model behavior
result = generate(
    "What is Python?",
    system_prompt="You are a technical writer. Explain concepts simply."
)

# 2. Sampling Modes - Control randomness
# Greedy (deterministic)
result = generate("Count to 5", sampling_mode="greedy")

# Top-K sampling (pick from top 40 tokens)
result = generate(
    "Write a creative story opening",
    sampling_mode="top_k",
    top_k=40,
    temperature=0.8
)

# Nucleus (Top-P) sampling
result = generate(
    "Generate a poem",
    sampling_mode="top_p",
    top_p=0.9
)

# 3. Reproducible Outputs with Seeds
result1 = generate("Random creative text", sampling_mode="top_k", seed=42)
result2 = generate("Random creative text", sampling_mode="top_k", seed=42)
assert result1 == result2  # Same output!

# 4. Model Selection
# Content tagging for classification
tags = generate(
    "This product is amazing! I love it!",
    model="content_tagging"
)

# 5. Guardrails Control
# Permissive mode for content transformation
summary = generate(
    "Summarize this potentially sensitive article...",
    guardrails="permissive"
)

# 6. Combining Features
result = generate(
    prompt="Analyze this podcast transcript...",
    system_prompt="You are a podcast chapter analyzer",
    sampling_mode="greedy",  # Deterministic
    temperature=0.3,  # Low creativity
    max_tokens=200,
    model="default",
    guardrails="default"
)
```

## Supported JSON Schema Features

| Feature | Supported | Example |
|---------|-----------|---------|
| `type: "object"` | ✅ | `{"type": "object", "properties": {...}}` |
| `type: "array"` | ✅ | `{"type": "array", "items": {...}}` |
| `type: "string"` | ✅ | `{"type": "string"}` |
| `type: "number"` | ✅ | `{"type": "number"}` |
| `type: "boolean"` | ✅ | `{"type": "boolean"}` |
| `enum` | ✅ | `{"enum": ["a", "b", "c"]}` |
| `required` | ✅ | `{"required": ["field1"]}` |
| `minItems/maxItems` | ✅ | For arrays |
| `$ref` | ❌ | Not yet supported |
| `allOf/oneOf` | ❌ | Not yet supported |

## Limitations

- Requires macOS 26+ with Apple Intelligence enabled
- Context window limits apply (see Apple docs for details)
- On-device model only — no network requests
