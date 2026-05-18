# backend/utils/flashcards.py
import json
import os
import re
import uuid
from .summarizer import summarize_text  # optional, may be None

"""
Improved flashcard generator:
- FRONT = concise question
- BACK  = full explanatory sentence / phrase
- Heuristics split sentences on common cue verbs and produce meaningful Q/A
"""

def clean_sentence(s):
    return re.sub(r"\s+", " ", s).strip()

# Shorten a phrase to a readable topic (no trailing punctuation)
def short_topic(phrase, max_words=6):
    phrase = re.sub(r"[^\w\s]", "", phrase).strip()
    parts = phrase.split()
    if not parts:
        return phrase
    return " ".join(parts[:max_words])

# Heuristic rules to convert sentence -> (question, answer)
def derive_question_answer(sentence):
    s = clean_sentence(sentence)
    if not s:
        return None, None

    # common cue verbs / connectors and patterns to split on
    patterns = [
        r"\bis all about\b\s*(.+)$",
        r"\bis primarily about\b\s*(.+)$",
        r"\b(what is|this chapter is about|this section is about|this lesson is about)\b\s*(.+)$",
        r"\b(?:is|are|means|refers to|includes|consists of|involves|describes|explains|covers)\b\s*(.+)$",
        r"^(.+?)\s*:\s*(.+)$",  # "Topic: explanation"
        r"^For example[, ]+(.*)$",
        r"^Example[: ]+(.*)$",
    ]

    # Try explicit pattern matches first (so we can extract concise answer)
    for pat in patterns:
        m = re.search(pat, s, flags=re.IGNORECASE)
        if m:
            # prefer group 1 or last captured group as the explanatory part
            groups = [g for g in m.groups() if g]
            if groups:
                answer_candidate = groups[-1].strip()
                # build a question using words before the connector when possible
                prefix = s[:m.start()].strip()
                # if prefix is short, ask "What is <prefix>?" otherwise generic
                if prefix and len(prefix.split()) <= 6:
                    q = f"What is {short_topic(prefix)}?"
                else:
                    # try to form a more natural question from the captured phrase
                    topic = short_topic(answer_candidate)
                    q = f"What is {topic}?"
                return q, answer_candidate

    # Next: try splitting at a main verb 'is' or 'are' to extract subject and predicate
    m = re.search(r"^(.{3,120}?)\s+(is|are|was|were)\s+(.+)$", s, flags=re.IGNORECASE)
    if m:
        subj = clean_sentence(m.group(1))
        pred = clean_sentence(m.group(3))
        # Build question from subject
        subj_short = short_topic(subj, max_words=5)
        if subj_short:
            q = f"What is {subj_short}?"
        else:
            q = f"Explain {short_topic(pred, max_words=5)}."
        return q, s

    # If sentence looks like "X — Y" or "X - Y", try splitting
    m = re.split(r"\s[—–-]\s", s)
    if len(m) >= 2:
        left = m[0].strip()
        right = " ".join(m[1:]).strip()
        q = f"What is {short_topic(left)}?"
        return q, right or s

    # If sentence is long and contains comma-separated clauses, pick the first clause as question topic
    if "," in s:
        first = s.split(",", 1)[0].strip()
        if len(first.split()) <= 10 and len(s) > 60:
            q = f"What is {short_topic(first)}?"
            return q, s

    # Fallback: try to extract a noun-like phrase (simple heuristic: longest capitalized chunk or first 2 words)
    caps = re.findall(r"[A-Z][a-zA-Z0-9]{2,}(?:\s+[A-Z][a-zA-Z0-9]{2,})*", s)
    if caps:
        topic = short_topic(caps[0])
        q = f"What is {topic}?"
        return q, s

    # Last resort: produce an "explain" style question using the first 4–8 words
    words = s.split()
    topic = " ".join(words[:4]) if len(words) >= 4 else " ".join(words[:len(words)])
    topic = short_topic(topic)
    q = f"Explain: {topic}"
    return q, s

def generate_flashcards(pdf_path, save_path, upload_id):
    """
    Produces up to 12 meaningful question/answer flashcards.
    Output stored in: <save_path>/flashcards/<upload_id>.json
    Returns metadata dict.
    """
    # Import extraction util locally to avoid import-time failures
    try:
        from .pdf_utils import extract_text_from_pdf
    except Exception:
        extract_text_from_pdf = None

    # Step 1: extract text
    text = ""
    if extract_text_from_pdf:
        try:
            text = extract_text_from_pdf(pdf_path) or ""
        except Exception:
            text = ""
    if not text:
        raise ValueError("Could not extract text from PDF")

    # Step 2: try summarizer for bullet/keypoints if available (prefer concise items)
    bullets = []
    try:
        pack = summarize_text(text)
        bullets = pack.get("bullets", []) or []
    except Exception:
        bullets = []

    # Use bullets first (if many and long enough), else fall back to sentence-splitting
    candidates = []
    if bullets:
        # pick reasonable bullets (length filter)
        for b in bullets:
            b_clean = clean_sentence(b)
            if len(b_clean) >= 30:
                candidates.append(b_clean)
    if not candidates:
        # split into sentences; keep sentences that look explanatory
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for s in sentences:
            s_clean = clean_sentence(s)
            if len(s_clean) >= 40:
                candidates.append(s_clean)

    flashcards = []
    idx = 1
    for s in candidates:
        if len(flashcards) >= 12:
            break
        q, a = derive_question_answer(s)
        if not q or not a:
            continue

        # ensure front != back; if they are too similar, modify front
        if a.strip() == q.strip() or a.strip().lower().startswith(q.strip().lower()):
            # make front a compact "What is X?" using first few words of answer
            short = short_topic(a, max_words=5)
            q = f"What is {short}?"
            # if still same, prefix with "Explain"
            if a.strip().lower().startswith(short.lower()):
                q = f"Explain: {short}"

        card = {
            "id": f"fc_{idx}",
            "front": q,
            "back": a
        }
        flashcards.append(card)
        idx += 1

    # If we ended up with zero cards, create a defensive single card
    if not flashcards:
        snippet = clean_sentence(text)[:120]
        flashcards = [{
            "id": "fc_1",
            "front": "Summarize the following:",
            "back": snippet
        }]

    # Save output
    out_dir = os.path.join(save_path, "flashcards")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{upload_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"flashcards": flashcards}, f, indent=4, ensure_ascii=False)

    return {
        "flashcards_count": len(flashcards),
        "path": out_path
    }
