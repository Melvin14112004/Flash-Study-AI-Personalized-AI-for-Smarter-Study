# backend/utils/mindmap.py
import os
import json
import re
from collections import Counter

try:
    import PyPDF2
except Exception:
    PyPDF2 = None

_STOPWORDS = {
    "the","and","for","that","with","this","from","which","have","has","were","been","their",
    "there","about","into","than","then","also","such","each","these","those","where","when",
    "what","who","whom","why","how","are","but","not","you","your","they","its","it's","its",
    "a","an","in","on","of","to","is","as","be","by","or","at","we","can","may","it"
}

_BORING_TOKENS = {
    "chapter","chapters","section","sections","paper","book","figure","fig",
    "table","tables","page","pages",
    "part","parts","include","includes","including",
    "category","categories","example","examples",
    "role","roles","sentence","sentences","word","words"
}

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _read_summary(save_path, upload_id):
    meta_path = os.path.join(save_path, "meta.json")
    if not os.path.exists(meta_path):
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        for arr in ("pdfs", "uploads"):
            for e in meta.get(arr, []):
                if e.get("id") == upload_id:
                    return e.get("summary") or e.get("short") or ""
    except Exception:
        pass
    return None


def _extract_text_from_pdf(pdf_path):
    if PyPDF2 is None:
        return ""
    try:
        text_parts = []
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for p in reader.pages:
                text_parts.append(p.extract_text() or "")
        return "\n".join(text_parts)
    except Exception:
        return ""


def _looks_like_verb(word, prev=None):
    if not word:
        return False
    lw = word.lower()
    if lw.endswith("ing") or lw.endswith("ed") or lw.endswith("ize") or lw.endswith("ise"):
        return True
    if prev and prev.lower() == "to":
        return True
    return False


def _candidate_single_words(text):
    if not text:
        return []

    tokens = re.findall(r"\b[A-Za-z][A-Za-z'-]*\b", text)
    candidates = []
    for i, t in enumerate(tokens):
        lw = t.lower().strip("'-")
        if len(lw) < 4:
            continue
        if lw in _STOPWORDS or lw in _BORING_TOKENS:
            continue
        if lw.isdigit():
            continue
        prev = tokens[i - 1] if i > 0 else None
        if _looks_like_verb(t, prev=prev):
            continue
        candidates.append(lw)
    return candidates


def _extract_list_keywords(text):
    if not text:
        return []

    patterns = [
        r"\binclude[s]?\s+([^.!?]+)",
        r"\bsuch as\s+([^.!?]+)",
        r"\bfor example,?\s+([^.!?]+)",
        r"\bfor instance,?\s+([^.!?]+)",
    ]
    found = []
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            segment = m.group(1)
            parts = re.split(r",| and ", segment)
            for part in parts:
                w_match = re.search(r"\b[A-Za-z][A-Za-z'-]*\b", part)
                if not w_match:
                    continue
                token = w_match.group(0).lower().strip("'-")
                if len(token) < 4:
                    continue
                if token in _STOPWORDS or token in _BORING_TOKENS:
                    continue
                if _looks_like_verb(token):
                    continue
                found.append(token)
    unique = []
    for t in found:
        if t not in unique:
            unique.append(t)
    return unique


def _short_root_label(text, max_words=8):
    if not text:
        return "Document"
    words = re.findall(r"\b[A-Za-z0-9']+\b", text)
    if not words:
        return "Document"
    return " ".join(words[:max_words])


def generate_mindmap(pdf_path, save_path=None, upload_id=None, max_nodes=None):
    text = ""
    if save_path and upload_id:
        text = _read_summary(save_path, upload_id) or ""
    if not text and pdf_path:
        text = _extract_text_from_pdf(pdf_path) or ""

    if not text:
        root = (
            os.path.splitext(os.path.basename(pdf_path))[0]
            if pdf_path
            else (upload_id or "document")
        )
        mindmap = {"root": root, "sections": []}
        if save_path and upload_id:
            os.makedirs(os.path.join(save_path, "mindmaps"), exist_ok=True)
            out_file = os.path.join(save_path, "mindmaps", f"{upload_id}.json")
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(mindmap, f, indent=2)
            return {"path": out_file, "sections": 0}
        return {"path": None, "sections": 0}

    text_clean = re.sub(r"\s+", " ", text).strip()
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text_clean) if s.strip()]
    lc_text = " ".join(sentences).lower()

    if max_nodes is None:
        s_count = len(sentences)
        if s_count <= 2:
            max_nodes = 3
        elif s_count <= 5:
            max_nodes = 5
        elif s_count <= 12:
            max_nodes = 6
        else:
            max_nodes = 8
    else:
        try:
            max_nodes = max(1, int(max_nodes))
        except Exception:
            max_nodes = 6

    base_candidates = _candidate_single_words(text_clean)
    list_candidates = _extract_list_keywords(text_clean)

    if not base_candidates and not list_candidates:
        caps = []
        for s in sentences:
            caps.extend(re.findall(r"\b[A-Z][a-z]{2,}\b", s))
        base_candidates = [c.lower() for c in caps]

    if not base_candidates and sentences:
        first_words = re.findall(r"\b[A-Za-z0-9']+\b", sentences[0])
        base_candidates = [w.lower() for w in first_words if len(w) > 2]

    freq = Counter(base_candidates)
    for t in list_candidates:
        freq[t] += 3

    all_candidates = base_candidates + list_candidates
    seen = set()
    scored = []
    for token in all_candidates:
        if token in seen:
            continue
        seen.add(token)
        fscore = freq.get(token, 1)
        pos = lc_text.find(token)
        pos_bonus = (len(lc_text) - pos) if pos >= 0 else 0
        score = fscore * 3 + (pos_bonus // 1000)
        scored.append((token, score, pos if pos >= 0 else 1e9))
    scored.sort(key=lambda x: (-x[1], x[2]))

    sections = []
    used_labels = set()

    # take high-priority list items first
    for token in list_candidates:
        if len(sections) >= max_nodes:
            break
        lw = token.strip().lower()
        if not lw or lw in _STOPWORDS or lw in _BORING_TOKENS:
            continue
        label = lw.capitalize()
        if label in used_labels:
            continue
        used_labels.add(label)
        sections.append(
            {
                "id": f"s{len(sections)+1}",
                "title": label,
                "content": label,
                "order": 0,
            }
        )

    # fill remaining slots from scored tokens
    for token, _s, _p in scored:
        if len(sections) >= max_nodes:
            break
        lw = token.strip().lower()
        if not lw or lw in _STOPWORDS or lw in _BORING_TOKENS:
            continue
        label = lw.capitalize()
        if label in used_labels:
            continue
        used_labels.add(label)
        sections.append(
            {
                "id": f"s{len(sections)+1}",
                "title": label,
                "content": label,
                "order": 0,
            }
        )

    if len(sections) < max_nodes:
        for s_idx, s in enumerate(sentences):
            if len(sections) >= max_nodes:
                break
            words = re.findall(r"\b[A-Za-z0-9']+\b", s)
            for w in words:
                lw = w.lower()
                if lw in _STOPWORDS or lw in _BORING_TOKENS:
                    continue
                if _looks_like_verb(w):
                    continue
                if len(lw) <= 2:
                    continue
                label = w.capitalize()
                if label in used_labels:
                    continue
                used_labels.add(label)
                sections.append(
                    {
                        "id": f"s{len(sections)+1}",
                        "title": label,
                        "content": label,
                        "order": s_idx,
                    }
                )
                break

    root_candidate = ""
    if save_path and upload_id:
        root_candidate = _read_summary(save_path, upload_id) or ""
    if not root_candidate and sentences:
        root_candidate = sentences[0]
    if not root_candidate:
        root_candidate = (
            os.path.splitext(os.path.basename(pdf_path))[0]
            if pdf_path
            else (upload_id or "Document")
        )
    root_label = _short_root_label(root_candidate, max_words=8)

    mindmap = {"root": root_label, "sections": sections[:max_nodes]}

    if save_path and upload_id:
        os.makedirs(os.path.join(save_path, "mindmaps"), exist_ok=True)
        out_file = os.path.join(save_path, "mindmaps", f"{upload_id}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(mindmap, f, indent=2)
        return {"path": out_file, "sections": len(mindmap["sections"])}

    return {"path": None, "sections": len(mindmap["sections"])}
