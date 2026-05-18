import json
import os
import logging
from config import META_PATH

logger = logging.getLogger("meta_store")

def load_meta():
    """Safe JSON loader — auto-heals corrupted uploads_meta.json."""
    if not os.path.exists(META_PATH):
        save_meta([])
        return []

    try:
        with open(META_PATH, "r", encoding="utf8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            else:
                logger.error("META FILE HAS INVALID FORMAT — RESETTING")
                save_meta([])
                return []

    except Exception:
        logger.error("META FILE CORRUPTED — RESETTING uploads_meta.json")
        save_meta([])
        return []


def save_meta(data):
    """Safe JSON writer that never corrupts the file."""
    try:
        with open(META_PATH, "w", encoding="utf8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Saved meta entries: %d", len(data))
    except Exception:
        logger.exception("Failed writing meta file")


def upsert(entry):
    """Insert or update a record."""
    entries = load_meta()
    found = False

    for i, e in enumerate(entries):
        if e.get("id") == entry.get("id"):
            entries[i] = entry
            found = True
            break

    if not found:
        entries.append(entry)

    save_meta(entries)


def delete(entry_id: str) -> bool:
    """Delete record by ID."""
    entries = load_meta()
    new = [e for e in entries if e.get("id") != entry_id]

    if len(new) == len(entries):
        return False

    save_meta(new)
    return True
