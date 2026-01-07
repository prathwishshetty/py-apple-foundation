#!/usr/bin/env python3
"""
Python wrapper for Apple FoundationModels via the generate CLI.

Provides an OpenAI-like interface to Apple's on-device language model.
"""

import subprocess
import json
import sys
from pathlib import Path
from typing import Any


def _get_cache_dir() -> Path:
    """Get the cache directory for compiled Swift binaries."""
    cache_dir = Path.home() / ".cache" / "apple-foundation" / "bin"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _get_swift_source_dir() -> Path:
    """Get the directory containing Swift source files."""
    return Path(__file__).parent / "swift"


def _compile_binary(name: str) -> Path:
    """Compile a Swift binary on-demand."""
    cache_dir = _get_cache_dir()
    binary_path = cache_dir / name
    source_path = _get_swift_source_dir() / f"{name}.swift"
    
    if not source_path.exists():
        raise FileNotFoundError(f"Swift source not found: {source_path}")
    
    # Check if we need to recompile (source is newer than binary)
    if binary_path.exists():
        if binary_path.stat().st_mtime >= source_path.stat().st_mtime:
            return binary_path
    
    print(f"Compiling {name}.swift...", file=sys.stderr)
    try:
        subprocess.run(
            ["swiftc", str(source_path), "-o", str(binary_path)],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to compile {name}.swift: {e.stderr}") from e
    except FileNotFoundError:
        raise RuntimeError(
            "Swift compiler not found. Install Xcode command line tools: "
            "xcode-select --install"
        ) from None
    
    return binary_path


def _get_binary(name: str) -> Path:
    """Get path to a binary, compiling if necessary."""
    cache_dir = _get_cache_dir()
    binary_path = cache_dir / name
    
    if binary_path.exists():
        # Check if source is newer (needs recompile)
        source_path = _get_swift_source_dir() / f"{name}.swift"
        if source_path.exists() and source_path.stat().st_mtime > binary_path.stat().st_mtime:
            return _compile_binary(name)
        return binary_path
    
    # Compile on first use
    return _compile_binary(name)


def generate(
    prompt: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
    schema: dict[str, Any] | None = None,
    system_prompt: str | None = None,
    instructions: str | None = None,
    sampling_mode: str | None = None,
    top_k: int | None = None,
    top_p: float | None = None,
    seed: int | None = None,
    model: str | None = None,
    use_case: str | None = None,
    guardrails: str | None = None,
) -> str | dict[str, Any]:
    """
    Generate text using Apple's on-device Foundation Model.

    Args:
        prompt: The text prompt to send to the model.
        temperature: Controls randomness (0.0 to 2.0). Higher = more creative.
        max_tokens: Maximum number of tokens in the response.
        schema: Optional JSON Schema dict for structured output.
        system_prompt: System-level instructions for the model.
        instructions: Alias for system_prompt.
        sampling_mode: Sampling strategy - "greedy", "top_k", or "top_p".
        top_k: Number of top tokens to sample from (for top_k mode).
        top_p: Cumulative probability threshold (for top_p mode).
        seed: Random seed for reproducible outputs.
        model: Model selection - "default" or "content_tagging".
        use_case: Alias for model.
        guardrails: Content safety mode - "default" or "permissive".

    Returns:
        str: The generated text if no schema provided.
        dict: The parsed JSON object if schema was provided.

    Raises:
        FileNotFoundError: If Swift source is not found.
        RuntimeError: If compilation or generation fails.
    """
    generate_bin = _get_binary("generate")

    # Handle parameter aliases
    final_system_prompt = instructions or system_prompt
    final_model = use_case or model

    # Build command
    cmd = [str(generate_bin), prompt]

    if temperature is not None:
        cmd.extend(["--temperature", str(temperature)])

    if max_tokens is not None:
        cmd.extend(["--max-tokens", str(max_tokens)])

    if schema is not None:
        schema_json = json.dumps(schema)
        cmd.extend(["--json-schema", schema_json])

    if final_system_prompt:
        cmd.extend(["--system-prompt", final_system_prompt])

    if sampling_mode:
        cli_mode = sampling_mode.replace("_", "-")
        cmd.extend(["--sampling", cli_mode])

    if top_k is not None:
        cmd.extend(["--top-k", str(top_k)])

    if top_p is not None:
        cmd.extend(["--top-p", str(top_p)])

    if seed is not None:
        cmd.extend(["--seed", str(seed)])

    if final_model:
        cli_model = final_model.replace("_", "-")
        cmd.extend(["--model", cli_model])

    if guardrails:
        cmd.extend(["--guardrails", guardrails])

    # Run generation
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        error_msg = result.stderr or "Unknown error"
        raise RuntimeError(f"Generation failed: {error_msg}")

    output = result.stdout.strip()

    # If schema was provided, try to parse as JSON
    if schema is not None:
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return output

    return output


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python foundation.py <prompt>")
        sys.exit(1)

    try:
        result = generate(sys.argv[1])
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
