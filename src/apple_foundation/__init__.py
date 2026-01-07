"""
Apple Foundation Models - Python bindings for macOS on-device AI.

Provides:
- generate(): Text generation via Foundation Models
- transcribe(): Audio transcription via SpeechAnalyzer
"""

from .foundation import generate
from .transcription import transcribe

__all__ = ["generate", "transcribe"]
__version__ = "0.1.0"
