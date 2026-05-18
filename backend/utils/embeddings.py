# backend/utils/embeddings.py
import logging
import os
import numpy as np
from typing import List, Tuple
from config import MODEL_CONFIG
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("embeddings")
EMBED_MODEL = None

def try_load_embedder():
    global EMBED_MODEL
    if EMBED_MODEL:
        return EMBED_MODEL
    local = MODEL_CONFIG.get("embed_local")
    if local and os.path.exists(local):
        try:
            EMBED_MODEL = SentenceTransformer(local)
            logger.info("Loaded local embedder")
            return EMBED_MODEL
        except Exception:
            logger.exception("Local embedder load failed")
    try:
        EMBED_MODEL = SentenceTransformer(MODEL_CONFIG.get("embed_remote"))
        logger.info("Loaded remote embedder")
        return EMBED_MODEL
    except Exception:
        logger.exception("Embedder load failed")
        EMBED_MODEL = None
        return None

def embed_texts(texts: List[str]) -> np.ndarray:
    model = try_load_embedder()
    if model is None:
        raise RuntimeError("Embedder not available")
    return np.array(model.encode(texts, show_progress_bar=False, convert_to_numpy=True))

def cosine_sim(a: np.ndarray, b: np.ndarray):
    # a: (d,), b: (n,d)
    a_norm = a / (np.linalg.norm(a) + 1e-12)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-12)
    return np.dot(b_norm, a_norm)

# Simple file-based index per upload (store chunks and embeddings as npz)
def save_index(upload_id: str, chunks: List[str], embeddings: np.ndarray, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    np.savez_compressed(os.path.join(out_dir, f"{upload_id}_index.npz"), chunks=chunks, embeddings=embeddings)
    logger.info("Saved index for %s", upload_id)

def load_index(upload_id: str, out_dir: str):
    path = os.path.join(out_dir, f"{upload_id}_index.npz")
    if not os.path.exists(path):
        return None
    data = np.load(path, allow_pickle=True)
    return list(data["chunks"]), data["embeddings"]
