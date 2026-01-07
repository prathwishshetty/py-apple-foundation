#!/usr/bin/env python3
"""
Transcribe audio files using macOS 26 SpeechAnalyzer via subprocess.
"""

import subprocess
import sys
from pathlib import Path

# Import shared binary resolution from foundation module
from .foundation import _get_binary


import json
from typing import Iterator, Union, Dict, Any

def transcribe(
    input_path: str,
    locale: str = "en-US",
    stream: bool = False,
    fast: bool = False,
    redact: bool = False,
    full_metadata: bool = False
) -> Union[str, Dict[str, Any], Iterator[Union[str, Dict[str, Any]]]]:
    """
    Transcribe an audio file using the native transcribe binary.

    Args:
        input_path: Path to the audio file (mp3, m4a, wav, etc.)
        locale: Language locale (default: en-US)
        stream: Whether to stream results (yield iterator) (default: False)
        fast: Use fast transcription (lower accuracy)
        redact: Redact sensitive info (politics/swear words based on etiquette)
        full_metadata: Return proper JSON with confidence/timestamps (default: False)

    Returns:
        String text (if full_metadata=False), or Dict with metadata (if True).
        If stream=True, returns Iterator of the above.
    """
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Get transcribe binary (auto-compiles if needed)
    transcribe_bin = _get_binary("transcribe")

    cmd = [str(transcribe_bin), str(input_path), "--locale", locale]
    if stream:
        cmd.append("--stream")
    if fast:
        cmd.append("--fast")
    if redact:
        cmd.append("--redact")
        
    if full_metadata:
        cmd.append("--json")
        cmd.append("--confidence")
        cmd.append("--alternatives")

    if stream:
        # Stream output line by line
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,  # Capture stderr to avoid leaking to console
            text=True,
            bufsize=1
        )
        
        def result_iterator():
            if process.stdout:
                for line in process.stdout:
                    line = line.strip()
                    if full_metadata:
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            pass # Skip non-json lines if any
                    else:
                        yield line
                        
            process.wait()
            if process.returncode != 0:
                error_msg = process.stderr.read() if process.stderr else "Unknown error"
                raise RuntimeError(f"Transcription failed: {error_msg}")
        
        return result_iterator()
    else:
        # Run normally and capture all output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            error_msg = result.stderr or "Unknown error"
            raise RuntimeError(f"Transcription failed: {error_msg}")

        output = result.stdout.strip()
        
        if full_metadata:
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                # Fallback or error?
                raise RuntimeError(f"Failed to parse JSON output: {output}")
        
        return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Transcribe audio file")
    parser.add_argument("input_path", help="Path to input audio file")
    parser.add_argument("--locale", default="en-US", help="Locale code (default: en-US)")
    parser.add_argument("--stream", action="store_true", help="Stream output")
    parser.add_argument("--fast", action="store_true", help="Use fast transcription")
    parser.add_argument("--redact", action="store_true", help="Redact sensitive info")
    parser.add_argument("--json", dest="full_metadata", action="store_true", help="Output full JSON metadata")
    
    args = parser.parse_args()

    try:
        result = transcribe(
            args.input_path,
            locale=args.locale,
            stream=args.stream,
            fast=args.fast,
            redact=args.redact,
            full_metadata=args.full_metadata
        )
        if args.stream:
            for snippet in result:
                if args.full_metadata:
                    print(json.dumps(snippet))
                else:
                    print(snippet)
        else:
            if args.full_metadata:
                print(json.dumps(result, indent=2))
            else:
                print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
