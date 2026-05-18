# backend/config.py
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ------------------------
# PATHS  (PUT IT HERE)
# ------------------------
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

# ✅ ADD THESE TWO LINES HERE
SAVES_DIR = os.path.join(BASE_DIR, "saves")
os.makedirs(SAVES_DIR, exist_ok=True)

DATA_DIR = os.path.join(BASE_DIR, "data")
LOCAL_MODELS_DIR = os.path.join(BASE_DIR, "local_models")
META_PATH = os.path.join(BASE_DIR, "uploads_meta.json")
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")

# CORS origins
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Chunking / safety
MAX_RAW_CHAR_SAFE = 200_000
DEFAULT_CHUNK_TOKENS = 512
DEFAULT_OVERLAP = 64

# PDF extraction limit
MAX_PDF_PAGES = 50

# Model names
MODEL_CONFIG = {
    "t5_local": os.path.join(LOCAL_MODELS_DIR, "led-2048"),
    "t5_remote": "pszemraj/LED-base-book-summary",
    "embed_local": os.path.join(LOCAL_MODELS_DIR, "all-MiniLM-L6-v2"),
    "embed_remote": "sentence-transformers/all-MiniLM-L6-v2",
}

MODEL_CONFIG["local_models_dir"] = LOCAL_MODELS_DIR

# TTS settings
TTS_OUTPUT_DIR = os.path.join(BASE_DIR, "uploads", "tts")
os.makedirs(TTS_OUTPUT_DIR, exist_ok=True)
