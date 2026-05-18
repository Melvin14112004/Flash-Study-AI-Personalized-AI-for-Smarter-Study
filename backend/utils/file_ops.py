# backend/utils/file_ops.py
import os
import tempfile
import shutil
from werkzeug.utils import secure_filename
from config import UPLOADS_DIR

def safe_save_file(file_storage, uid: str) -> str:
    """
    Save werkzeug FileStorage to uploads with uuid prefix.
    Returns filename (not full path).
    """
    orig = secure_filename(file_storage.filename)
    fname = f"{uid}__{orig}"
    out_path = os.path.join(UPLOADS_DIR, fname)
    file_storage.save(out_path)
    return fname

def find_file_by_uid(uid: str):
    for f in os.listdir(UPLOADS_DIR):
        if f.startswith(f"{uid}__"):
            return os.path.join(UPLOADS_DIR, f)
    return None

def atomic_write_json(path: str, data_str: str):
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="tmp", suffix=".json", dir=os.path.dirname(path))
    os.close(tmp_fd)
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(data_str)
    os.replace(tmp_path, path)
