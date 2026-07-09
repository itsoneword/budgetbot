"""
Local speech-to-text via faster-whisper.

CPU-only, int8 quantization. Model weights come from the host's HuggingFace
cache mounted into the container (see docker-compose.yml); WHISPER_MODEL
selects the size (default: small — already cached on the host). The model
loads lazily on first use and stays in memory; inference is blocking, so it
runs in a worker thread. OGG/Opus bytes are decoded in-memory via PyAV —
no ffmpeg binary or temp files needed.
"""
import asyncio
import io
import logging
import os
import threading

logger = logging.getLogger(__name__)


class STTError(Exception):
    pass


_model = None
_model_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                try:
                    from faster_whisper import WhisperModel
                except ImportError as e:
                    raise STTError(f"faster-whisper is not installed: {e}")
                size = os.getenv("WHISPER_MODEL", "small")
                logger.info("Loading whisper model %r (cpu, int8)", size)
                _model = WhisperModel(size, device="cpu", compute_type="int8")
    return _model


async def transcribe_ogg(data: bytes) -> str:
    """Transcribe OGG/Opus voice bytes. Returns "" if no speech was detected."""

    def _run() -> str:
        model = _get_model()
        # vad_filter skips non-speech so silence doesn't hallucinate words.
        # The segments generator is lazy — joining is what runs inference.
        segments, _info = model.transcribe(io.BytesIO(data), vad_filter=True)
        return "".join(segment.text for segment in segments).strip()

    try:
        return await asyncio.to_thread(_run)
    except STTError:
        raise
    except Exception as e:
        raise STTError(f"transcription failed: {e}")
