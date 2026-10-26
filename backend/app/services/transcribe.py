import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# ponytail: tiny model cached on CPU. upgrade to small/medium or GPU CUDA when VRAM available.

_model = None

def get_whisper_model(model_size: str = "tiny"):
    global _model
    if _model is None:
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Loading faster-whisper model '{model_size}' on CPU...")
            _model = WhisperModel(model_size, device="cpu", compute_type="int8")
        except Exception as e:
            logger.error(f"Failed to initialize faster-whisper: {e}")
            raise
    return _model

def transcribe_audio(audio_path: str, model_size: str = "tiny") -> Tuple[str, List[Dict[str, Any]]]:
    try:
        model = get_whisper_model(model_size)
        segments_gen, info = model.transcribe(audio_path, beam_size=3)
        language = info.language
        segments = []
        full_text_parts = []

        for seg in segments_gen:
            text = seg.text.strip()
            if text:
                segments.append({
                    "start": round(seg.start, 2),
                    "end": round(seg.end, 2),
                    "text": text
                })
                full_text_parts.append(text)

        full_text = " ".join(full_text_parts)
        return language, segments
    except Exception as e:
        logger.warning(f"Transcription fallback triggered due to: {e}")
        # Graceful fallback: return empty/mock segment if audio lacks speech or model error
        return "und", []
