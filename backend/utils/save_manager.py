# backend/utils/save_manager.py
import os
import json
import uuid
from typing import Optional, Dict, Any, List

from config import SAVES_DIR

os.makedirs(SAVES_DIR, exist_ok=True)

def _save_root() -> str:
    return SAVES_DIR

def _save_path(save_id: str) -> str:
    return os.path.join(_save_root(), save_id)

def _save_meta_path(save_id: str) -> str:
    return os.path.join(_save_path(save_id), "meta.json")

def _uploads_path(save_id: str) -> str:
    return os.path.join(_save_path(save_id), "uploads")

def _indexes_path(save_id: str) -> str:
    return os.path.join(_save_path(save_id), "indexes")

def _tts_path(save_id: str) -> str:
    return os.path.join(_save_path(save_id), "tts")

def list_saves() -> List[Dict[str, Any]]:
    """Return list of saves (basic info)."""
    out = []
    for name in os.listdir(_save_root()):
        p = os.path.join(_save_root(), name)
        if os.path.isdir(p):
            meta_file = _save_meta_path(name)
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {"id": name}
            else:
                data = {"id": name}
            out.append(data)
    return out

def create_save(name: Optional[str] = None) -> Dict[str, Any]:
    save_id = str(uuid.uuid4())
    p = _save_path(save_id)
    os.makedirs(p, exist_ok=True)
    os.makedirs(_uploads_path(save_id), exist_ok=True)
    os.makedirs(_indexes_path(save_id), exist_ok=True)
    os.makedirs(_tts_path(save_id), exist_ok=True)
    meta = {
        "id": save_id,
        "name": name or f"save-{save_id[:8]}",
        "createdAt": None,
        "uploads": []
    }
    _write_meta(save_id, meta)
    return meta

def _write_meta(save_id: str, meta: Dict[str, Any]):
    with open(_save_meta_path(save_id), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

def load_meta(save_id: str) -> Dict[str, Any]:
    mp = _save_meta_path(save_id)
    if not os.path.exists(mp):
        raise FileNotFoundError("Save not found")
    with open(mp, "r", encoding="utf-8") as f:
        return json.load(f)

def upsert_save_entry(save_id: str, entry: Dict[str, Any]):
    meta = load_meta(save_id)
    uploads = meta.get("uploads", [])
    found = False
    for i, e in enumerate(uploads):
        if e.get("id") == entry.get("id"):
            uploads[i] = entry
            found = True
            break
    if not found:
        uploads.append(entry)
    meta["uploads"] = uploads
    _write_meta(save_id, meta)

def save_file_to_save(save_id: str, file_obj, uid: str, filename: str) -> str:
    """Save Flask file object into saves/<save_id>/uploads and return saved filename."""
    up = _uploads_path(save_id)
    os.makedirs(up, exist_ok=True)
    # saved name: {uid}__{original}
    safe_name = f"{uid}__{filename}"
    dest = os.path.join(up, safe_name)
    # file_obj may be Werkzeug FileStorage with .save()
    try:
        file_obj.save(dest)
    except Exception:
        # fallback: read/write
        with open(dest, "wb") as out:
            file_obj.stream.seek(0)
            out.write(file_obj.stream.read())
    return safe_name

def find_file_in_save(save_id: str, uid: str) -> Optional[str]:
    up = _uploads_path(save_id)
    if not os.path.isdir(up):
        return None
    for fn in os.listdir(up):
        if fn.startswith(f"{uid}__"):
            return os.path.join(up, fn)
    return None
