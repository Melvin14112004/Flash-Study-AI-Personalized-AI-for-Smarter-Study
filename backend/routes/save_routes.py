# backend/routes/save_routes.py
import os
import json
import uuid
import shutil
import time
import logging
from flask import Blueprint, request, jsonify, current_app, send_file, send_from_directory, abort
from werkzeug.utils import secure_filename

from config import SAVES_DIR

# Optional heavy utils — if absent during testing, we gracefully degrade.
try:
    from utils.pdf_utils import extract_text_from_pdf
    from utils.summarizer import summarize_text, try_load_summarizer, led_generate
    from utils.embeddings import embed_texts, save_index, load_index, try_load_embedder
    from utils.tts import generate_tts
    from utils.chunking import tokenize_and_chunk
    from utils.flashcards import generate_flashcards as backend_generate_flashcards
    from utils.mindmap import generate_mindmap as backend_generate_mindmap
    from utils.quizgen import generate_quiz as backend_generate_quiz
except Exception:
    extract_text_from_pdf = None
    summarize_text = None
    try_load_summarizer = None
    embed_texts = None
    save_index = None
    generate_tts = None
    tokenize_and_chunk = None
    backend_generate_flashcards = None
    backend_generate_mindmap = None
    backend_generate_quiz = None

save_bp = Blueprint("save", __name__)

# Ensure saves directory exists
os.makedirs(SAVES_DIR, exist_ok=True)

# -------------------------
# Helper utilities
# -------------------------
def _meta_path_for(folder):
    return os.path.join(folder, "meta.json")

def _read_meta(save_folder):
    meta_path = _meta_path_for(save_folder)
    if not os.path.exists(meta_path):
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logging.exception("Failed to read meta for %s", save_folder)
        return None

def _write_meta(save_folder, meta):
    meta_path = _meta_path_for(save_folder)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=4)

def _safe_target_for(save_id):
    safe_name = secure_filename(str(save_id))
    saves_root = os.path.abspath(SAVES_DIR)
    target = os.path.abspath(os.path.join(saves_root, safe_name))
    # Ensure target is inside saves_root
    if not (target == saves_root or target.startswith(saves_root + os.sep)):
        return None
    return target

def _ensure_save_dirs(save_path):
    os.makedirs(os.path.join(save_path, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(save_path, "indexes"), exist_ok=True)
    os.makedirs(os.path.join(save_path, "tts"), exist_ok=True)
    os.makedirs(os.path.join(save_path, "flashcards"), exist_ok=True)
    os.makedirs(os.path.join(save_path, "mindmaps"), exist_ok=True)
    os.makedirs(os.path.join(save_path, "quiz"), exist_ok=True)

# ---------------------------------------------------------
# CREATE NEW SAVE
# Accept both legacy (/save/new) and API (/api/save/new)
# ---------------------------------------------------------
@save_bp.route("/save/new", methods=["POST"])
@save_bp.route("/api/save/new", methods=["POST"])
def create_save():
    data = request.get_json(silent=True) or {}
    # fallback to form data
    if not data:
        data = request.form.to_dict() or {}

    name = (data.get("name") if isinstance(data.get("name"), str) else "") or ""
    name = name.strip()

    if not name:
        return jsonify({"status": "error", "message": "Missing save name"}), 400

    safe_name = secure_filename(name.lower().replace(" ", "_"))
    save_path = os.path.join(SAVES_DIR, safe_name)

    if os.path.exists(save_path):
        return jsonify({"status": "error", "message": "Save already exists"}), 400

    try:
        _ensure_save_dirs(save_path)

        meta = {
            "name": name,
            "pdfs": [],
            "uploads": [],
            "created_at": int(time.time())
        }
        _write_meta(save_path, meta)
        logging.info("Created save: %s", safe_name)
    except Exception as exc:
        logging.exception("Error creating save %s: %s", safe_name, exc)
        return jsonify({"status": "error", "message": str(exc)}), 500

    return jsonify({"status": "ok", "save": safe_name, "message": "Save created"}), 200

# ---------------------------------------------------------
# LIST SAVES (API)
# GET /api/saves or /saves
# ---------------------------------------------------------
@save_bp.route("/api/saves", methods=["GET"])
@save_bp.route("/saves", methods=["GET"])
def list_saves():
    saves = []
    try:
        if not os.path.exists(SAVES_DIR):
            return jsonify({"saves": []}), 200

        for folder in os.listdir(SAVES_DIR):
            save_path = os.path.join(SAVES_DIR, folder)
            meta_path = os.path.join(save_path, "meta.json")

            if not os.path.isdir(save_path):
                continue

            created_at = None
            name = folder

            # try to read meta.json if exists
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    name = meta.get("name", folder)
                    created_at = meta.get("created_at")
                except Exception:
                    created_at = None

            if not created_at:
                try:
                    created_at = int(os.path.getmtime(save_path))
                except Exception:
                    created_at = 0

            saves.append({
                "id": folder,
                "name": name,
                "created_at": int(created_at)
            })
    except Exception as exc:
        logging.exception("list_saves error: %s", exc)
        return jsonify({"saves": []}), 200

    saves.sort(key=lambda x: x.get("created_at", 0))
    return jsonify({"saves": saves}), 200

# ---------------------------------------------------------
# UPLOAD PDF INTO SAVE (legacy route kept)
# POST /save/<save_name>/upload (multipart/form-data file=...)
# Also provide API alias POST /api/upload?save_id=<save>
# ---------------------------------------------------------
@save_bp.route("/save/<save_name>/upload", methods=["POST"])
def upload_to_save(save_name):
    save_path = os.path.join(SAVES_DIR, save_name)

    if not os.path.exists(save_path):
        return jsonify({"status": "error", "message": "Save not found"}), 404

    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file provided"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"status": "error", "message": "Empty filename"}), 400

    try:
        pdf_id = str(uuid.uuid4())
        pdf_filename = f"{pdf_id}.pdf"
        upload_path = os.path.join(save_path, "uploads", pdf_filename)
        file.save(upload_path)

        meta = _read_meta(save_path) or {"name": save_name, "pdfs": [], "uploads": [] , "created_at": int(time.time())}
        # maintain both old "pdfs" structure and new "uploads" if desired
        entry = {
            "id": pdf_id,
            "name": file.filename,
            "file": pdf_filename,
            "filename": pdf_filename,  # compatibility
            "summary": "",
            "short": "",
            "bullets": [],
            "sections": [],
            "exam_notes": [],
            "tts": False,
            "tts_available": False,
            "indexed": False,
            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        # append to uploads and pdfs for compatibility
        if "uploads" not in meta:
            meta["uploads"] = []
        meta["uploads"].append({
            "id": pdf_id,
            "name": file.filename,
            "filename": pdf_filename,
            "summary": ""
        })
        if "pdfs" not in meta:
            meta["pdfs"] = []
        meta["pdfs"].append(entry)

        _write_meta(save_path, meta)
        logging.info("Uploaded PDF %s to save %s", pdf_filename, save_name)
    except Exception as exc:
        logging.exception("upload error: %s", exc)
        return jsonify({"status": "error", "message": str(exc)}), 500

    return jsonify({"status": "ok", "pdf_id": pdf_id, "filename": pdf_filename}), 200

# API alias for upload (convenience)
@save_bp.route("/api/upload", methods=["POST"])
def api_upload_alias():
    save_id = request.args.get("save_id") or (request.get_json(silent=True) or {}).get("save_id") or request.form.get("save_id")
    if not save_id:
        return jsonify({"status": "error", "message": "Missing save_id"}), 400
    return upload_to_save(save_id)

# ---------------------------------------------------------
# GET uploads metadata for a save
# GET /api/uploads?save_id=<save_name>
# ---------------------------------------------------------
@save_bp.route("/api/uploads", methods=["GET"])
def api_list_uploads():
    save_id = request.args.get("save_id") or request.args.get("save")
    if not save_id:
        return jsonify({"uploads": []}), 200
    save_path = os.path.join(SAVES_DIR, secure_filename(save_id))
    meta = _read_meta(save_path)
    if meta is None:
        return jsonify({"uploads": []}), 200
    # prefer meta.uploads or meta.pdfs
    uploads = meta.get("uploads") or meta.get("pdfs") or []
    return jsonify({"uploads": uploads}), 200

# ---------------------------------------------------------
# SUMMARIZE PDF (legacy route)
# POST /save/<save_name>/<pdf_id>/summarize
# ---------------------------------------------------------
@save_bp.route("/save/<save_name>/<pdf_id>/summarize", methods=["POST"])
def summarize_pdf(save_name, pdf_id):
    if extract_text_from_pdf is None or summarize_text is None:
        return jsonify({"status": "error", "message": "Summarizer not available"}), 500

    save_path = os.path.join(SAVES_DIR, save_name)
    meta_path = os.path.join(save_path, "meta.json")

    if not os.path.exists(meta_path):
        return jsonify({"status": "error", "message": "Save not found"}), 404

    meta = _read_meta(save_path)
    entry = next((x for x in meta.get("pdfs", []) if x["id"] == pdf_id), None)
    if not entry:
        return jsonify({"status": "error", "message": "PDF not found"}), 404

    pdf_path = os.path.join(save_path, "uploads", entry["file"])
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return jsonify({"status": "error", "message": "Text extraction failed"}), 400

    pack = summarize_text(text)
    entry["summary"] = pack.get("detailed_summary", "")
    entry["short"] = pack.get("short_summary", "")
    entry["bullets"] = pack.get("bullets", [])
    entry["sections"] = pack.get("sections", [])
    entry["exam_notes"] = pack.get("exam_notes", [])

    _write_meta(save_path, meta)
    logging.info("Summarized PDF %s in save %s", pdf_id, save_name)
    return jsonify({"status": "ok", "summary_ready": True}), 200

# ---------------------------------------------------------
# INDEX PDF (legacy)
# POST /save/<save_name>/<pdf_id>/index
# ---------------------------------------------------------
@save_bp.route("/save/<save_name>/<pdf_id>/index", methods=["POST"])
def index_pdf(save_name, pdf_id):
    if try_load_summarizer is None or embed_texts is None or save_index is None:
        return jsonify({"status": "error", "message": "Indexing utilities not available"}), 500

    save_path = os.path.join(SAVES_DIR, save_name)
    meta = _read_meta(save_path)
    if meta is None:
        return jsonify({"status": "error", "message": "Save not found"}), 404

    entry = next((x for x in meta.get("pdfs", []) if x["id"] == pdf_id), None)
    if not entry:
        return jsonify({"status": "error", "message": "PDF not found"}), 404

    pdf_path = os.path.join(save_path, "uploads", entry["file"])
    text = extract_text_from_pdf(pdf_path)

    model, tok, _ = try_load_summarizer()
    chunks = tokenize_and_chunk(text, tok, chunk_tokens=1024, overlap=128)
    emb = embed_texts(chunks)

    save_index(pdf_id, chunks, emb, os.path.join(save_path, "indexes"))
    entry["indexed"] = True
    _write_meta(save_path, meta)

    logging.info("Indexed PDF %s in save %s", pdf_id, save_name)
    return jsonify({"status": "ok"}), 200

# ---------------------------------------------------------
# SMART SEARCH (legacy)
# POST /save/<save_name>/<pdf_id>/smart
# ---------------------------------------------------------
@save_bp.route("/save/<save_name>/<pdf_id>/smart", methods=["POST"])
def smart(save_name, pdf_id):
    data = request.get_json() or {}
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"status": "error", "message": "Missing question"}), 400

    save_path = os.path.join(SAVES_DIR, save_name)
    meta = _read_meta(save_path)
    if meta is None:
        return jsonify({"status": "error", "message": "Save not found"}), 404

    entry = next((x for x in meta.get("pdfs", []) if x["id"] == pdf_id), None)
    if not entry:
        return jsonify({"status": "error", "message": "PDF not found"}), 404

    notes = entry.get("exam_notes") or entry.get("bullets") or []
    summary = entry.get("summary", "")

    qw = question.lower().split()
    scored = [(sum(1 for w in qw if w in n.lower()), n) for n in notes]
    scored.sort(reverse=True)

    best = [n for s, n in scored[:3] if s > 0]

    if not best:
        import re
        sentences = re.split(r"(?<=[.!?])\s+", summary)
        best = [s for s in sentences if sum(1 for w in qw if w in s.lower()) > 1][:3]

    if not best:
        best = ["No direct answer found."]

    return jsonify({"status": "ok", "answer": best}), 200

# ---------------------------------------------------------
# TEXT-TO-SPEECH (TTS) generator (legacy)
# POST /save/<save_name>/<pdf_id>/tts
# ---------------------------------------------------------
@save_bp.route("/save/<save_name>/<pdf_id>/tts", methods=["POST"])
def tts_pdf(save_name, pdf_id):
    if generate_tts is None:
        return jsonify({"status": "error", "message": "TTS utility not available"}), 500

    save_path = os.path.join(SAVES_DIR, save_name)
    meta = _read_meta(save_path)
    if meta is None:
        return jsonify({"status": "error", "message": "Save not found"}), 404

    # support both pdfs and uploads arrays
    entry = next((x for x in (meta.get("pdfs") or []) if x.get("id") == pdf_id), None)
    if not entry:
        entry = next((x for x in (meta.get("uploads") or []) if x.get("id") == pdf_id), None)
    if not entry:
        return jsonify({"status": "error", "message": "PDF not found"}), 404

    text = entry.get("summary") or entry.get("short")
    if not text:
        return jsonify({"status": "error", "message": "Summary not available"}), 400

    try:
        # Ensure tts dir exists
        tts_dir = os.path.join(save_path, "tts")
        os.makedirs(tts_dir, exist_ok=True)

        output_filename = f"{pdf_id}.mp3"
        output_path = os.path.join(tts_dir, output_filename)

        # generate_tts should return final path or raise error
        final_path = generate_tts(text, filename=output_path, format="mp3")

        # update meta
        # try to update the richer 'pdfs' entry first
        for arr in ("pdfs", "uploads"):
            for e in meta.get(arr, []):
                if e.get("id") == pdf_id:
                    e["tts"] = True
                    e["tts_file"] = output_filename
        _write_meta(save_path, meta)

        logging.info("Generated TTS for %s/%s -> %s", save_name, pdf_id, output_path)

        return jsonify({"status": "ok", "tts_file": output_filename, "path": final_path}), 200
    except Exception as exc:
        logging.exception("TTS generation failed for %s/%s: %s", save_name, pdf_id, exc)
        return jsonify({"status": "error", "message": str(exc)}), 500

# -----------------------------
# BACKEND: TTS alias + serve route
# -----------------------------
@save_bp.route("/api/upload/<upload_id>/generate_tts", methods=["POST"])
def api_generate_tts(upload_id):
    """
    Alias that forwards TTS generation to existing route.
    Expects JSON body or query param 'save_id' identifying the save folder.
    """
    save_id = request.args.get("save_id") or (request.get_json(silent=True) or {}).get("save_id") or request.form.get("save_id")
    if not save_id:
        return jsonify({"status": "error", "message": "Missing save_id"}), 400

    try:
        return tts_pdf(save_id, upload_id)
    except Exception as exc:
        logging.exception("api_generate_tts error: %s", exc)
        return jsonify({"status": "error", "message": str(exc)}), 500

# Serve the generated tts mp3 for a given upload id.
# GET /api/upload/<upload_id>/tts?save_id=<save_name>
@save_bp.route("/api/upload/<upload_id>/tts", methods=["GET"])
@save_bp.route("/api/upload/<upload_id>/play_tts", methods=["GET"])
def api_serve_tts(upload_id):
    save_id = request.args.get("save_id") or (request.get_json(silent=True) or {}).get("save_id")
    if not save_id:
        return jsonify({"status": "error", "message": "Missing save_id"}), 400

    safe_name = secure_filename(str(save_id))
    tts_path = os.path.join(SAVES_DIR, safe_name, "tts", f"{upload_id}.mp3")

    if not os.path.exists(tts_path):
        logging.info("TTS file not found: %s", tts_path)
        return jsonify({"status": "error", "message": "audio file not found"}), 404

    try:
        return send_file(tts_path, mimetype="audio/mpeg", as_attachment=False)
    except Exception as exc:
        logging.exception("Failed to send tts file %s: %s", tts_path, exc)
        return jsonify({"status": "error", "message": str(exc)}), 500

# For convenience, expose a filesystem-backed route for static serving:
# GET /saves/<save_id>/tts/<filename>
@save_bp.route("/saves/<save_id>/tts/<path:filename>", methods=["GET"])
def serve_tts_file(save_id, filename):
    try:
        target = _safe_target_for(save_id)
        if target is None:
            logging.warning("serve_tts_file: invalid save_id: %s", save_id)
            return jsonify({"status": "error", "message": "Invalid save id"}), 400

        tts_dir = os.path.join(target, "tts")
        full_path = os.path.abspath(os.path.join(tts_dir, filename))

        # prevent traversal
        if not (full_path.startswith(os.path.abspath(tts_dir) + os.sep) or full_path == os.path.abspath(tts_dir)):
            logging.warning("serve_tts_file: attempted traversal: %s", filename)
            return jsonify({"status": "error", "message": "Invalid filename"}), 400

        if not os.path.exists(full_path):
            logging.info("serve_tts_file: file not found: %s", full_path)
            return abort(404)

        return send_from_directory(tts_dir, filename, as_attachment=False)
    except Exception as exc:
        logging.exception("serve_tts_file error: %s", exc)
        return jsonify({"status": "error", "message": "Internal error"}), 500

# ---------------------------------------------------------
# FLASHCARDS endpoints
# - GET  /api/upload/<upload_id>/flashcards?save_id=<save>
# - POST /save/<save>/<upload_id>/generate_flashcards  (legacy)
# - POST /api/upload/<upload_id>/generate_flashcards?save_id=<save> (alias)
# ---------------------------------------------------------
@save_bp.route("/api/upload/<upload_id>/flashcards", methods=["GET"])
def api_get_flashcards(upload_id):
    save_id = request.args.get("save_id")
    if not save_id:
        return jsonify({"status": "error", "message": "Missing save_id"}), 400

    save_path = os.path.join(SAVES_DIR, secure_filename(save_id))
    meta = _read_meta(save_path)
    if meta is None:
        return jsonify({"status": "error", "message": "Save not found"}), 404

    # look for a file in flashcards dir
    fc_path = os.path.join(save_path, "flashcards", f"{upload_id}.json")
    if not os.path.exists(fc_path):
        return jsonify({"status": "error", "message": "flashcards not found"}), 404

    try:
        with open(fc_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify({"status": "ok", "flashcards": data.get("flashcards", data)}), 200
    except Exception as exc:
        logging.exception("Failed to read flashcards for %s/%s: %s", save_id, upload_id, exc)
        return jsonify({"status": "error", "message": "Failed to load flashcards"}), 500

@save_bp.route("/save/<save_id>/<upload_id>/generate_flashcards", methods=["POST","GET","OPTIONS"])
def generate_flashcards_route(save_id, upload_id):
    if backend_generate_flashcards is None:
        return jsonify({"status": "error", "message": "Flashcards generator not available"}), 500

    save_path = os.path.join(SAVES_DIR, secure_filename(save_id))
    meta = _read_meta(save_path)
    if meta is None:
        return jsonify({"status": "error", "message": "Save not found"}), 404

    entry = next((x for x in meta.get("pdfs", []) if x.get("id") == upload_id), None)
    if not entry:
        entry = next((x for x in meta.get("uploads", []) if x.get("id") == upload_id), None)
    if not entry:
        return jsonify({"status": "error", "message": "PDF not found"}), 404

    try:
        pdf_path = os.path.join(save_path, "uploads", entry.get("file") or entry.get("filename"))
        # generator should write JSON to saves/<save>/flashcards/<upload_id>.json or return data
        result = backend_generate_flashcards(pdf_path, save_path=save_path, upload_id=upload_id)
        # refresh meta maybe
        _write_meta(save_path, meta)
        return jsonify({"status": "ok", "result": result}), 200
    except Exception as exc:
        logging.exception("Failed to generate flashcards for %s/%s: %s", save_id, upload_id, exc)
        return jsonify({"status": "error", "message": str(exc)}), 500

@save_bp.route("/api/upload/<upload_id>/generate_flashcards", methods=["GET","POST","OPTIONS"])
def api_generate_flashcards(upload_id):
    save_id = request.args.get("save_id") or (request.get_json(silent=True) or {}).get("save_id")
    if not save_id:
        return jsonify({"status": "error", "message": "Missing save_id"}), 400
    return generate_flashcards_route(save_id, upload_id)

# ---------------------------------------------------------
# MINDMAP endpoints (similar pattern)
# ---------------------------------------------------------
@save_bp.route("/save/<save_id>/<upload_id>/generate_mindmap", methods=["POST","GET","OPTIONS"])
def generate_mindmap_route(save_id, upload_id):
    if backend_generate_mindmap is None:
        return jsonify({"status": "error", "message": "Mindmap generator not available"}), 500

    save_path = os.path.join(SAVES_DIR, secure_filename(save_id))
    meta = _read_meta(save_path)
    if meta is None:
        return jsonify({"status": "error", "message": "Save not found"}), 404

    entry = next((x for x in meta.get("pdfs", []) if x.get("id") == upload_id), None)
    if not entry:
        entry = next((x for x in meta.get("uploads", []) if x.get("id") == upload_id), None)
    if not entry:
        return jsonify({"status": "error", "message": "PDF not found"}), 404

    try:
        pdf_path = os.path.join(save_path, "uploads", entry.get("file") or entry.get("filename"))
        result = backend_generate_mindmap(pdf_path, save_path=save_path, upload_id=upload_id)
        _write_meta(save_path, meta)
        return jsonify({"status": "ok", "result": result}), 200
    except Exception as exc:
        logging.exception("Failed to generate mindmap for %s/%s: %s", save_id, upload_id, exc)
        return jsonify({"status": "error", "message": str(exc)}), 500

@save_bp.route("/api/upload/<upload_id>/generate_mindmap", methods=["GET","POST","OPTIONS"])
def api_generate_mindmap(upload_id):
    save_id = request.args.get("save_id") or (request.get_json(silent=True) or {}).get("save_id")
    if not save_id:
        return jsonify({"status": "error", "message": "Missing save_id"}), 400
    return generate_mindmap_route(save_id, upload_id)

@save_bp.route("/api/upload/<upload_id>/mindmap", methods=["GET","POST","OPTIONS"])
def api_get_mindmap(upload_id):
    save_id = request.args.get("save_id")
    if not save_id:
        return jsonify({"status": "error", "message": "Missing save_id"}), 400
    file_path = os.path.join(SAVES_DIR, secure_filename(save_id), "mindmaps", f"{upload_id}.json")
    if not os.path.exists(file_path):
        return jsonify({"status": "error", "message": "mindmap not found"}), 404
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify({"status": "ok", "mindmap": data}), 200
    except Exception as exc:
        logging.exception("Failed to read mindmap %s/%s: %s", save_id, upload_id, exc)
        return jsonify({"status": "error", "message": "Failed to load mindmap"}), 500

# ---------------------------------------------------------
# QUIZ endpoints (similar pattern)
# ---------------------------------------------------------
@save_bp.route("/save/<save_id>/<upload_id>/generate_quiz", methods=["POST","GET","OPTIONS"])
def generate_quiz_route(save_id, upload_id):
    if backend_generate_quiz is None:
        return jsonify({"status": "error", "message": "Quiz generator not available"}), 500

    save_path = os.path.join(SAVES_DIR, secure_filename(save_id))
    meta = _read_meta(save_path)
    if meta is None:
        return jsonify({"status": "error", "message": "Save not found"}), 404

    entry = next((x for x in meta.get("pdfs", []) if x.get("id") == upload_id), None)
    if not entry:
        entry = next((x for x in meta.get("uploads", []) if x.get("id") == upload_id), None)
    if not entry:
        return jsonify({"status": "error", "message": "PDF not found"}), 404

    try:
        pdf_path = os.path.join(save_path, "uploads", entry.get("file") or entry.get("filename"))
        result = backend_generate_quiz(pdf_path, save_path=save_path, upload_id=upload_id)
        _write_meta(save_path, meta)
        return jsonify({"status": "ok", "result": result}), 200
    except Exception as exc:
        logging.exception("Failed to generate quiz for %s/%s: %s", save_id, upload_id, exc)
        return jsonify({"status": "error", "message": str(exc)}), 500

@save_bp.route("/api/upload/<upload_id>/generate_quiz", methods=["POST","GET","OPTIONS"])
def api_generate_quiz(upload_id):
    save_id = request.args.get("save_id") or (request.get_json(silent=True) or {}).get("save_id")
    if not save_id:
        return jsonify({"status": "error", "message": "Missing save_id"}), 400
    return generate_quiz_route(save_id, upload_id)

@save_bp.route("/api/upload/<upload_id>/quiz", methods=["GET"])
def api_get_quiz(upload_id):
    save_id = request.args.get("save_id")
    if not save_id:
        return jsonify({"status": "error", "message": "Missing save_id"}), 400
    file_path = os.path.join(SAVES_DIR, secure_filename(save_id), "quiz", f"{upload_id}.json")
    if not os.path.exists(file_path):
        return jsonify({"status": "error", "message": "quiz not found"}), 404
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify({"status": "ok", "quiz": data}), 200
    except Exception as exc:
        logging.exception("Failed to read quiz %s/%s: %s", save_id, upload_id, exc)
        return jsonify({"status": "error", "message": "Failed to load quiz"}), 500

# ---------------------------------------------------------
# DELETE SAVE (compat routes)
# ---------------------------------------------------------
@save_bp.route("/api/save/<save_id>", methods=["DELETE"])
@save_bp.route("/save/<save_id>", methods=["DELETE"])
@save_bp.route("/api/save", methods=["POST"])
@save_bp.route("/save", methods=["POST"])
def delete_save(save_id=None):
    try:
        # If POST body provided and no url param, accept id from body
        if request.method == "POST" and not save_id:
            data = request.get_json(silent=True) or {}
            if not data:
                data = request.form.to_dict() or {}
            body_id = data.get("id") or data.get("_id") or data.get("save_id") or data.get("save")
            if body_id:
                save_id = body_id

        logging.info("Delete called, raw save_id: %s", repr(save_id))

        if not save_id:
            logging.warning("Delete called without a save_id")
            return jsonify({"status": "error", "message": "Missing save id"}), 400

        if isinstance(save_id, dict):
            save_id = save_id.get("id") or save_id.get("save") or str(save_id)

        save_id = str(save_id)

        safe_name = secure_filename(save_id)
        saves_root = os.path.abspath(SAVES_DIR)
        target = os.path.abspath(os.path.join(saves_root, safe_name))

        logging.info("Resolved delete target: %s", target)

        if not (target == saves_root or target.startswith(saves_root + os.sep)):
            logging.warning("Attempt to delete outside saves root: %s", target)
            return jsonify({"status": "error", "message": "Invalid save id"}), 400

        if not os.path.exists(target):
            logging.info("Delete requested but save not found: %s", safe_name)
            return jsonify({"status": "ok", "message": "Save not found (nothing to delete)"}), 200

        shutil.rmtree(target)
        logging.info("Deleted save: %s", safe_name)
        return jsonify({"status": "ok", "deleted": safe_name}), 200

    except Exception as exc:
        logging.exception("Error deleting save %s: %s", save_id, exc)
        return jsonify({"status": "error", "message": str(exc)}), 500
