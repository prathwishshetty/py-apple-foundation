#!/usr/bin/env python3
"""
Integration tests for Transcription API.
Uses macOS 'say' command to generate real audio for end-to-end testing.
"""

import sys
import unittest
import subprocess
import os
from pathlib import Path

# Add src to path if running directly
sys.path.append(str(Path(__file__).parent.parent / "src"))

from apple_foundation import transcription

@unittest.skipIf(sys.platform != "darwin", "Integration tests require macOS")
class TestTranscriptionIntegration(unittest.TestCase):
    
    def setUp(self):
        self.test_file = Path("integration_test_audio.aiff")
        self.text = "This is a test of the emergency broadcast system."
        # Generate audio using macOS 'say' command
        subprocess.run(
            ["say", "-o", str(self.test_file), self.text], 
            check=True,
            capture_output=True
        )

    def tearDown(self):
        if self.test_file.exists():
            self.test_file.unlink()

    def test_end_to_end_transcription(self):
        """Test full transcription with real audio"""
        # Run transcription
        result = transcription.transcribe(str(self.test_file), full_metadata=True)
        
        # Verify structure
        self.assertIsInstance(result, dict)
        self.assertIn("text", result)
        self.assertIn("segments", result)
        
        # Verify content (fuzzy match due to speech recognition var)
        self.assertIn("emergency broadcast", result["text"].lower())
        self.assertIn("system", result["text"].lower())
        
        # Verify metadata
        self.assertGreater(len(result["segments"]), 0)
        first_segment = result["segments"][0]
        self.assertIn("start", first_segment)
        self.assertIn("confidence", first_segment)
        self.assertGreater(first_segment["confidence"], 0.0)

    def test_streaming_integration(self):
        """Test streaming with real audio"""
        iterator = transcription.transcribe(str(self.test_file), stream=True, full_metadata=True)
        
        segments_received = 0
        all_text_seen = []
        
        for chunk in iterator:
            self.assertIsInstance(chunk, dict)
            if "text" in chunk:
                all_text_seen.append(chunk["text"])
            if "segments" in chunk and chunk["segments"]:
                segments_received += 1
                
        full_output = " ".join(all_text_seen)
        self.assertIn("emergency", full_output.lower())
        self.assertGreater(segments_received, 0)

def main():
    unittest.main()

if __name__ == "__main__":
    main()
