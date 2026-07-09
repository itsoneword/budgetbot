"""Speech-to-text — local faster-whisper backend (T-019)."""
from .whisper_local import transcribe_ogg, STTError

__all__ = ["transcribe_ogg", "STTError"]
