# backend/utils/tts.py
import os
import logging
from gtts import gTTS
import pyttsx3
from config import TTS_OUTPUT_DIR

logger = logging.getLogger("tts")

def generate_tts_gtts(text: str, out_path: str, lang='en'):
    try:
        t = gTTS(text=text, lang=lang)
        t.save(out_path)
        return True
    except Exception:
        logger.exception("gTTS failed")
        return False

def generate_tts_pyttsx3(text: str, out_path: str):
    try:
        engine = pyttsx3.init()
        # pyttsx3 saves via speaking to file using save_to_file
        engine.save_to_file(text, out_path)
        engine.runAndWait()
        return True
    except Exception:
        logger.exception("pyttsx3 failed")
        return False

def generate_tts(text: str, filename: str = None, format: str = "mp3"):
    os.makedirs(TTS_OUTPUT_DIR, exist_ok=True)
    if not filename:
        filename = f"tts_{int(os.times()[4])}.{format}"
    out_path = os.path.join(TTS_OUTPUT_DIR, filename)
    # Prefer gTTS for quality; fallback to pyttsx3
    success = generate_tts_gtts(text, out_path) if format == "mp3" else False
    if success:
        return out_path
    if generate_tts_pyttsx3(text, out_path):
        return out_path
    return None
