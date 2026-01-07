#!/usr/bin/env python3
"""
Transcribe audio files using macOS 26 SpeechAnalyzer via subprocess.
"""

import subprocess
import sys
from pathlib import Path


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
        FileNotFoundError: If input file or transcribe binary not found
        RuntimeError: If transcription fails
    """
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Find transcribe binary relative to this script
    # Script is in src/apple_foundation/, binary is in bin/
    project_root = Path(__file__).parent.parent.parent
    transcribe_bin = project_root / "bin" / "transcribe"

    if not transcribe_bin.exists():
        raise FileNotFoundError(f"Transcribe binary not found: {transcribe_bin}")

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


def main():
    if len(sys.argv) < 3:
        print("Usage: python transcribe.py <input_audio> <output_txt> [locale]")
        print("  locale: Optional, defaults to en-US")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    locale = sys.argv[3] if len(sys.argv) > 3 else "en-US"

    try:
        text = transcribe(input_path, output_path, locale)
        print(f"\nTranscription length: {len(text)} characters")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
