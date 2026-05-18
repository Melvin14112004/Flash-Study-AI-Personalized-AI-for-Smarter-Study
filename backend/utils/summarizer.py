# backend/utils/summarizer.py
import logging
from typing import Optional, Tuple, List, Dict
import os
import sys
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

from config import MODEL_CONFIG
from utils.chunking import tokenize_and_chunk

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

SUM_MODEL = None
SUM_TOKENIZER = None
SUM_NAME = None


# ---------------------------------------------------------
# LOAD LED-2048 MODEL
# ---------------------------------------------------------
def try_load_summarizer():
    global SUM_MODEL, SUM_TOKENIZER, SUM_NAME

    if SUM_MODEL:
        return SUM_MODEL, SUM_TOKENIZER, SUM_NAME

    local_path = MODEL_CONFIG["t5_local"]

    tok = AutoTokenizer.from_pretrained(local_path, local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(local_path, local_files_only=True)

    SUM_MODEL, SUM_TOKENIZER, SUM_NAME = model, tok, local_path
    logger.info(f"Loaded LED model: {local_path}")
    return model, tok, local_path


# ---------------------------------------------------------
# LED GENERATION (global attention)
# ---------------------------------------------------------
def led_generate(model, tokenizer, text, max_out=512):

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=2048
    )

    # Global attention on first token
    global_attention_mask = torch.zeros_like(inputs["input_ids"])
    global_attention_mask[:, 0] = 1

    outputs = model.generate(
        input_ids=inputs["input_ids"],
        attention_mask=inputs["attention_mask"],
        global_attention_mask=global_attention_mask,
        max_length=max_out,
        num_beams=3,
        early_stopping=True
    )

    return tokenizer.decode(outputs[0], skip_special_tokens=True)


# ---------------------------------------------------------
# SINGLE CHUNK SUMMARY
# ---------------------------------------------------------
def summarize_chunk_safe(chunk: str, mode="chapter", max_length=512):
    model, tok, _ = try_load_summarizer()

    prefix = ""

    if mode == "chapter":
        prefix = "summarize: "
    elif mode == "notes":
        prefix = "summarize into exam-ready notes: "
    elif mode == "sections":
        prefix = "summarize with section breakdown: "
    elif mode == "bullets":
        prefix = "summarize into long bullet list: "
    elif mode == "qa":
        prefix = "answer question: "

    return led_generate(model, tok, prefix + chunk, max_out=max_length)


# ---------------------------------------------------------
# FULL PACK SUMMARY
# ---------------------------------------------------------
def summarize_text(text: str, mode: str = "chapter",
                   chunk_tokens: int = None, overlap: int = None):

    if chunk_tokens is None:
        from config import DEFAULT_CHUNK_TOKENS
        chunk_tokens = DEFAULT_CHUNK_TOKENS

    if overlap is None:
        from config import DEFAULT_OVERLAP
        overlap = DEFAULT_OVERLAP

    model, tok, name = try_load_summarizer()
    tokenizer_for_chunk = tok if tok else None

    chunks = tokenize_and_chunk(text, tokenizer_for_chunk,
                                chunk_tokens=chunk_tokens, overlap=overlap)

    logger.info("Split into %d chunks", len(chunks))

    # FIRST PASS — chunk-level summaries
    chunk_summaries = []
    for c in chunks:
        try:
            s = summarize_chunk_safe(c, mode="chapter")
        except Exception:
            logger.exception("Chunk summary failed")
            s = c[:2000]
        chunk_summaries.append(s)

    joined = "\n\n".join(chunk_summaries)

    # SECOND PASS — condensed full summary
    try:
        condensed = summarize_chunk_safe(joined, mode="notes", max_length=2048)
    except:
        condensed = joined[:8000]

    # BULLETS
    import re
    sentences = re.split(r"(?<=[\.\?\!])\s+", condensed)
    bullets = [s.strip() for s in sentences if len(s.strip()) > 40][:12]

    # SHORT SUMMARY
    short = " ".join(sentences[:4]).strip()

    # SECTIONS — heuristic
    sections = []
    temp = []
    for s in sentences:
        if len(s) > 120:
            temp.append(s)
        if len(temp) >= 5:
            sections.append("\n".join(temp))
            temp = []
    if temp:
        sections.append("\n".join(temp))

    # Exam notes
    exam_notes = bullets[:10]

    return {
        "detailed_summary": condensed.strip(),
        "short_summary": short,
        "bullets": bullets,
        "sections": sections,
        "exam_notes": exam_notes
    }
