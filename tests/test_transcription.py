#!/usr/bin/env python3
"""
Test suite for Transcription API.
Tests CLI argument generation, JSON parsing, and streaming logic.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json

# Add src to path if running directly
sys.path.append(str(Path(__file__).parent.parent / "src"))

from apple_foundation import transcription

class TestTranscription(unittest.TestCase):
    
    @patch("apple_foundation.transcription._get_binary")
    @patch("subprocess.run")
    def test_basic_transcription_args(self, mock_run, mock_get_binary):
        """Test basic transcription arguments"""
        mock_get_binary.return_value = "/path/to/transcribe"
        mock_run.return_value = MagicMock(returncode=0, stdout="Hello world")
        
        with patch("pathlib.Path.exists", return_value=True):
            transcription.transcribe("test.mp3", locale="es-ES")
            
        cmd = mock_run.call_args[0][0]
        self.assertIn("/path/to/transcribe", cmd)
        self.assertIn("test.mp3", cmd)
        self.assertIn("--locale", cmd)
        self.assertIn("es-ES", cmd)
        
        # Verify default flags NOT present
        self.assertNotIn("--fast", cmd)
        self.assertNotIn("--redact", cmd)
        self.assertNotIn("--json", cmd)

    @patch("apple_foundation.transcription._get_binary")
    @patch("subprocess.run")
    def test_advanced_flags(self, mock_run, mock_get_binary):
        """Test fast, redact, and full_metadata flags"""
        mock_get_binary.return_value = "/bin/transcribe"
        mock_run.return_value = MagicMock(returncode=0, stdout='{}')
        
        with patch("pathlib.Path.exists", return_value=True):
            transcription.transcribe(
                "test.mp3", 
                fast=True, 
                redact=True, 
                full_metadata=True
            )
            
        cmd = mock_run.call_args[0][0]
        self.assertIn("--fast", cmd)
        self.assertIn("--redact", cmd)
        self.assertIn("--json", cmd)
        self.assertIn("--confidence", cmd)
        self.assertIn("--alternatives", cmd)

    @patch("apple_foundation.transcription._get_binary")
    @patch("subprocess.Popen")
    def test_streaming_args(self, mock_popen, mock_get_binary):
        """Test streaming mode arguments"""
        mock_get_binary.return_value = "/bin/transcribe"
        process_mock = MagicMock()
        process_mock.stdout = ["partial", "final"]
        process_mock.returncode = 0
        mock_popen.return_value = process_mock
        
        with patch("pathlib.Path.exists", return_value=True):
            iter_result = transcription.transcribe("test.mp3", stream=True)
            list(iter_result) # consume iterator
            
        cmd = mock_popen.call_args[0][0]
        self.assertIn("--stream", cmd)

    @patch("apple_foundation.transcription._get_binary")
    @patch("subprocess.run")
    def test_json_parsing(self, mock_run, mock_get_binary):
        """Test JSON output parsing"""
        mock_get_binary.return_value = "/bin/transcribe"
        json_output = json.dumps({
            "text": "Hello",
            "segments": [{"text": "Hello", "start": 0.0, "duration": 1.0, "confidence": 0.9}]
        })
        mock_run.return_value = MagicMock(returncode=0, stdout=json_output)
        
        with patch("pathlib.Path.exists", return_value=True):
            result = transcription.transcribe("test.mp3", full_metadata=True)
            
        self.assertIsInstance(result, dict)
        self.assertEqual(result["text"], "Hello")
        self.assertEqual(len(result["segments"]), 1)
        self.assertEqual(result["segments"][0]["confidence"], 0.9)

    def test_file_not_found(self):
        """Test error when file doesn't exist"""
        with self.assertRaises(FileNotFoundError):
            transcription.transcribe("nonexistent.mp3")

def main():
    unittest.main()

if __name__ == "__main__":
    main()
