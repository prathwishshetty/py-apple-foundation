#!/usr/bin/env python3
"""
Transcribe audio files using macOS 26 SpeechAnalyzer via subprocess.
"""

import subprocess
import sys
from pathlib import Path

# Import shared binary resolution from foundation module
from .foundation import _get_binary


def transcribe(input_path: str, output_path: str, locale: str = "en-US") -> str:
    """
    Transcribe an audio file using the native transcribe binary.

    Args:
        input_path: Path to the audio file (mp3, m4a, wav, etc.)
        output_path: Path where the transcription will be saved
        locale: Language locale (default: en-US)

    Returns:
        The transcribed text

    Raises:
        FileNotFoundError: If input file or Swift source not found
        RuntimeError: If compilation or transcription fails
    """
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Get transcribe binary (auto-compiles if needed)
    transcribe_bin = _get_binary("transcribe")

    # Run transcription
    result = subprocess.run(
        [str(transcribe_bin), str(input_path), str(output_path), locale],
        capture_output=True,
        text=True
    )

    # Print progress output
    if result.stdout:
        print(result.stdout)

    if result.returncode != 0:
        error_msg = result.stderr or "Unknown error"
        raise RuntimeError(f"Transcription failed: {error_msg}")

    # Read and return the transcription
    output_file = Path(output_path)
    if output_file.exists():
        return output_file.read_text()

    return ""


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python transcription.py <input_audio> <output_txt> [locale]")
        sys.exit(1)

    try:
        text = transcribe(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "en-US")
        print(f"\nTranscription length: {len(text)} characters")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
