# backend/utils/chunking.py
import logging
from typing import List, Optional
from config import MAX_RAW_CHAR_SAFE, DEFAULT_CHUNK_TOKENS, DEFAULT_OVERLAP

logger = logging.getLogger("chunking")

def split_paragraphs(text: str, min_chars=2000) -> List[str]:
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = []
    cur_len = 0
    for p in paras:
        p_len = len(p)
        if cur_len + p_len > min_chars and current:
            chunks.append("\n\n".join(current))
            current = [p]
            cur_len = p_len
        else:
            current.append(p)
            cur_len += p_len
    if current:
        chunks.append("\n\n".join(current))
    return chunks if chunks else [text]

def tokenize_and_chunk(text: str, tokenizer=None, chunk_tokens: int = DEFAULT_CHUNK_TOKENS, overlap: int = DEFAULT_OVERLAP) -> List[str]:
    if tokenizer is None:
        logger.warning("No tokenizer - using paragraph fallback")
        return split_paragraphs(text, min_chars=chunk_tokens*2)
    
    try:
        token_ids = tokenizer.encode(text, add_special_tokens=False)
    except Exception:
        logger.exception("Tokenizer.encode failed - paragraph fallback")
        return split_paragraphs(text, min_chars=chunk_tokens*2)
    chunks = []
    start = 0
    n = len(token_ids)
    while start < n:
        end = min(start + chunk_tokens, n)
        chunk_ids = token_ids[start:end]
        chunk_text = tokenizer.decode(chunk_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True)
        chunks.append(chunk_text.strip())
        start = end - overlap if end < n else end
        if start < 0: start = 0
    return chunks
