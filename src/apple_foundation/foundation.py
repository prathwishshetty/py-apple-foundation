#!/usr/bin/env python3
"""
Python wrapper for Apple FoundationModels via the generate CLI.

Provides an OpenAI-like interface to Apple's on-device language model.
"""

import subprocess
import json
from pathlib import Path
from typing import Any


def generate(
    prompt: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
    schema: dict[str, Any] | None = None,
    # Phase 1: New parameters
    system_prompt: str | None = None,
    instructions: str | None = None,  # Alias for system_prompt
    sampling_mode: str | None = None,  # "greedy", "top_k", "top_p"
    top_k: int | None = None,
    top_p: float | None = None,
    seed: int | None = None,
    model: str | None = None,  # "default", "content_tagging"
    use_case: str | None = None,  # Alias for model
    guardrails: str | None = None,  # "default", "permissive"
) -> str | dict[str, Any]:
    """
    Generate text using Apple's on-device Foundation Model.

    Args:
        prompt: The text prompt to send to the model.
        temperature: Controls randomness (0.0 to 2.0). Higher = more creative.
        max_tokens: Maximum number of tokens in the response.
        schema: Optional JSON Schema dict for structured output.
                Supported types: object, array, string, number, boolean, enum.
        
        # Phase 1 parameters
        system_prompt: System-level instructions for the model (defines role/behavior).
        instructions: Alias for system_prompt.
        sampling_mode: Sampling strategy - "greedy" (deterministic), "top_k", or "top_p".
        top_k: Number of top tokens to sample from (for top_k mode, default: 40).
        top_p: Cumulative probability threshold (for top_p mode, default: 0.9).
        seed: Random seed for reproducible outputs.
        model: Model selection - "default" (general) or "content_tagging".
        use_case: Alias for model.
        guardrails: Content safety mode - "default" (strict) or "permissive".

    Returns:
        str: The generated text if no schema provided.
        dict: The parsed JSON object if schema was provided.

    Raises:
        FileNotFoundError: If the generate binary is not found.
        RuntimeError: If generation fails.

    Example:
        >>> from src.foundation_service import generate
        
        # Simple text generation
        >>> result = generate("Write a haiku about coding")
        >>> print(result)
        
        # With system prompt
        >>> result = generate(
        ...     "What is 2+2?",
        ...     system_prompt="You are a calculator. Only respond with numbers."
        ... )
        
        # With sampling control
        >>> result = generate(
        ...     "Write a creative story",
        ...     sampling_mode="top_k",
        ...     top_k=40,
        ...     seed=42
        ... )

        # Structured output
        >>> schema = {"type": "object", "properties": {"title": {"type": "string"}}}
        >>> result = generate("Extract the title", schema=schema)
        >>> print(result["title"])
    """
    # Find binary relative to this script
    # Script is in src/apple_foundation/, binary is in bin/
    project_root = Path(__file__).parent.parent.parent
    generate_bin = project_root / "bin" / "generate"

    if not generate_bin.exists():
        raise FileNotFoundError(f"Generate binary not found: {generate_bin}")

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

    # Phase 1: Add new parameters
    if final_system_prompt:
        cmd.extend(["--system-prompt", final_system_prompt])

    if sampling_mode:
        # Convert Python naming to CLI naming (top_k -> top-k)
        cli_mode = sampling_mode.replace("_", "-")
        cmd.extend(["--sampling", cli_mode])

    if top_k is not None:
        cmd.extend(["--top-k", str(top_k)])

    if top_p is not None:
        cmd.extend(["--top-p", str(top_p)])

    if seed is not None:
        cmd.extend(["--seed", str(seed)])

    if final_model:
        # Convert Python naming to CLI naming
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
            # Return raw output if parsing fails
            return output

    return output


def main():
    """Simple test of the generate function."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python foundation_service.py <prompt>")
        sys.exit(1)

    prompt = sys.argv[1]
    try:
        result = generate(prompt)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
