# backend/routes/summarizer_routes.py
import re
import os
import uuid
import datetime
import logging
from flask import Blueprint, request, jsonify, send_file
from utils.file_ops import safe_save_file, find_file_by_uid
from utils.pdf_utils import extract_text_from_pdf
from utils.meta_store import upsert, load_meta, delete
from utils.summarizer import summarize_text, try_load_summarizer, led_generate
from utils.embeddings import embed_texts, save_index, load_index, try_load_embedder
from utils.tts import generate_tts
from config import UPLOADS_DIR
from utils.save_manager import (
    create_save, list_saves, load_meta as load_save_meta,
    upsert_save_entry, save_file_to_save, find_file_in_save
)

logger = logging.getLogger("summarizer_routes")
summarizer_bp = Blueprint("summarizer", __name__)

# -------- pollution cleaner helpers --------
INSTRUCTION_PATTERNS = [
    r"answer the student's question using only the notes below[:.]?",
    r"answer the student's question using only the notes below\.",
    r"answer the student's question using only the notes below.*?(?:\n|$)",
    r"use only the notes below.*?(?:\n|$)",
    r"you are a helpful study assistant.*?(?:\n|$)",
    r"if the answer is not present.*?(?:\n|$)",
    r"i'm not completely sure based on these notes.*?(?:\n|$)",
    r"suggest what part of the pdf they should re-?read.*?(?:\n|$)",
]

def strip_instruction_noise(text: str) -> str:
    if not text:
        return ""
    cleaned = text
    for pat in INSTRUCTION_PATTERNS:
        cleaned = re.sub(pat, " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned

def clean_user_question(q: str) -> str:
    return strip_instruction_noise(q or "")

# Helper: get optional save_id from query params
def _get_save_id() -> str:
    return request.args.get("save_id") or request.form.get("save_id")

# POST /api/save  -> create a new save
@summarizer_bp.route("/save", methods=["POST"])
def create_save_route():
    data = request.get_json() or {}
    name = data.get("name")
    meta = create_save(name)
    return jsonify({"status": "ok", "save": meta}), 200

# GET /api/saves -> list saves
@summarizer_bp.route("/saves", methods=["GET"])
def list_saves_route():
    return jsonify({"saves": list_saves()}), 200

# POST /api/upload  (optionally ?save_id=...)
@summarizer_bp.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "Invalid file"}), 400

    uid = str(uuid.uuid4())
    save_id = _get_save_id()

    if save_id:
        saved_name = save_file_to_save(save_id, file, uid, file.filename)
        saved_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "saves",
            save_id,
            "uploads",
            saved_name,
        )
    else:
        saved_name = safe_save_file(file, uid)
        saved_path = os.path.join(UPLOADS_DIR, saved_name)

    extracted = extract_text_from_pdf(saved_path)
    preview = extracted[:2000] + ("..." if len(extracted) > 2000 else "")
    createdAt = datetime.datetime.utcnow().isoformat() + "Z"

    meta_entry = {
        "id": uid,
        "name": file.filename,
        "filename": saved_name,
        "createdAt": createdAt,
        "summary": "",
        "short": "",
        "bullets": [],
        "sections": [],
        "exam_notes": [],
        "mode": "partial",
        "flashcardsCount": 0,
        "quizCount": 0,
        "mindmapsCount": 0,
        "studyHours": 0,
        "search_indexed": False,
        "tts_available": False,
    }

    # persist meta (global or per-save)
    try:
        if save_id:
            upsert_save_entry(save_id, meta_entry)
        else:
            upsert(meta_entry)
    except Exception:
        logger.exception("Failed to write initial meta")

    if not extracted:
        meta_entry["mode"] = "error"
        if save_id:
            upsert_save_entry(save_id, meta_entry)
        else:
            upsert(meta_entry)
        return jsonify({"status": "error", "message": "No text"}), 400

    # Summarize + CLEAN
    summary_pack = summarize_text(extracted)

    detailed_summary = strip_instruction_noise(
        summary_pack.get("detailed_summary", "")
    )
    short_summary = strip_instruction_noise(
        summary_pack.get("short_summary", "")
    )
    bullets = summary_pack.get("bullets") or []
    exam_notes = summary_pack.get("exam_notes") or []

    meta_entry["summary"] = detailed_summary
    meta_entry["short"] = short_summary
    meta_entry["bullets"] = [strip_instruction_noise(b) for b in bullets]
    meta_entry["sections"] = summary_pack.get("sections") or []
    meta_entry["exam_notes"] = [strip_instruction_noise(n) for n in exam_notes]
    meta_entry["mode"] = "chapter"

    if save_id:
        upsert_save_entry(save_id, meta_entry)
    else:
        upsert(meta_entry)

    return jsonify(
        {
            "status": "ok",
            "upload": meta_entry,
            "text_preview": preview,
            "summary": meta_entry["summary"],
        }
    ), 200


# GET /api/uploads
@summarizer_bp.route("/uploads", methods=["GET"])
def uploads_list():
    save_id = _get_save_id()
    if save_id:
        try:
            meta = load_save_meta(save_id)
            return jsonify({"uploads": meta.get("uploads", [])}), 200
        except Exception:
            return jsonify({"uploads": []}), 200
    entries = load_meta()
    return jsonify({"uploads": entries}), 200


# Helper to find file path either in save or global
def _find_file_by_uid_with_save(uid: str, save_id: str = None) -> str:
    if save_id:
        f = find_file_in_save(save_id, uid)
        if f:
            return f
        # fallthrough to global
    return find_file_by_uid(uid)


# GET /api/upload/<id>/download
@summarizer_bp.route("/upload/<upload_id>/download", methods=["GET"])
def download(upload_id):
    save_id = _get_save_id()
    file_path = _find_file_by_uid_with_save(upload_id, save_id)
    if not file_path:
        return jsonify({"status": "error", "message": "Not found"}), 404
    return send_file(file_path, as_attachment=True)


# GET /api/upload/<id>/status
@summarizer_bp.route("/upload/<upload_id>/status", methods=["GET"])
def status(upload_id):
    save_id = _get_save_id()
    if save_id:
        try:
            meta = load_save_meta(save_id)
            entry = next(
                (e for e in meta.get("uploads", []) if e.get("id") == upload_id),
                None,
            )
            if not entry:
                return jsonify({"status": "error", "message": "Not found"}), 404
            return (
                jsonify(
                    {
                        "id": upload_id,
                        "mode": entry.get("mode"),
                        "summary_ready": bool(entry.get("summary")),
                        "summary_length": len(entry.get("summary", "") or ""),
                    }
                ),
                200,
            )
        except Exception:
            return jsonify({"status": "error", "message": "Save not found"}), 404

    entries = load_meta()
    e = next((x for x in entries if x.get("id") == upload_id), None)
    if not e:
        return jsonify({"status": "error", "message": "Upload not found"}), 404
    ready = bool(e.get("summary"))
    return (
        jsonify(
            {
                "id": upload_id,
                "mode": e.get("mode"),
                "summary_ready": ready,
                "summary_length": len(e.get("summary", "") or ""),
            }
        ),
        200,
    )


# DELETE /api/upload/<id>
@summarizer_bp.route("/upload/<upload_id>", methods=["DELETE"])
def delete_upload(upload_id):
    save_id = _get_save_id()
    if save_id:
        fpath = find_file_in_save(save_id, upload_id)
        if fpath and os.path.exists(fpath):
            os.remove(fpath)
        # remove meta entry from save meta
        try:
            meta = load_save_meta(save_id)
            uploads = [
                u for u in meta.get("uploads", []) if u.get("id") != upload_id
            ]
            meta["uploads"] = uploads
            # write back
            from utils.save_manager import _write_meta as _sm_write_meta

            _sm_write_meta(save_id, meta)
        except Exception:
            logger.exception("Failed to update save meta on delete")
    else:
        file_path = find_file_by_uid(upload_id)
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        deleted = delete(upload_id)
        if not deleted:
            return jsonify({"status": "error", "message": "Not found"}), 404
        return jsonify({"status": "ok"}), 200

    return jsonify({"status": "ok"}), 200


# GET /api/upload/<id>/summary/download?format=txt|md
@summarizer_bp.route("/upload/<upload_id>/summary/download", methods=["GET"])
def download_summary(upload_id):
    fmt = request.args.get("format", "txt")
    save_id = _get_save_id()
    entry = None
    if save_id:
        try:
            meta = load_save_meta(save_id)
            entry = next(
                (e for e in meta.get("uploads", []) if e.get("id") == upload_id),
                None,
            )
        except Exception:
            entry = None
    else:
        entries = load_meta()
        entry = next((x for x in entries if x.get("id") == upload_id), None)

    if not entry:
        return jsonify({"status": "error", "message": "Upload not found"}), 404

    content = entry.get("summary", "") or entry.get("short", "")
    if not content:
        return jsonify({"status": "error", "message": "No summary available"}), 400

    from tempfile import NamedTemporaryFile

    ext = "md" if fmt == "md" else "txt"
    tmp = NamedTemporaryFile(delete=False, suffix=f".{ext}")
    tmp.write(content.encode("utf-8"))
    tmp.flush()
    tmp.close()
    return send_file(
        tmp.name, as_attachment=True, download_name=f"{upload_id}_summary.{ext}"
    )


# POST /api/upload/<id>/index  (build embedding index)
@summarizer_bp.route("/upload/<upload_id>/index", methods=["POST"])
def build_index(upload_id):
    save_id = _get_save_id()
    file_path = _find_file_by_uid_with_save(upload_id, save_id)
    if not file_path:
        return jsonify({"status": "error", "message": "File not found"}), 404

    # load entry meta (so we can update search_indexed flag)
    entry = None
    if save_id:
        meta = load_save_meta(save_id)
        entry = next((e for e in meta.get("uploads", []) if e.get("id") == upload_id), None)
    else:
        entries = load_meta()
        entry = next((x for x in entries if x.get("id") == upload_id), None)

    extracted = extract_text_from_pdf(file_path)
    if not extracted:
        return jsonify({"status": "error", "message": "No text extracted"}), 400

    model, tok, _ = try_load_summarizer()
    from utils.chunking import tokenize_and_chunk

    chunks = tokenize_and_chunk(extracted, tok, chunk_tokens=1024, overlap=128)

    try:
        emb = embed_texts(chunks)
        out_dir = os.path.join(os.path.dirname(file_path), "indexes")
        save_index(upload_id, chunks, emb, out_dir)
        if entry is not None:
            entry["search_indexed"] = True
            if save_id:
                upsert_save_entry(save_id, entry)
            else:
                upsert(entry)
        return jsonify({"status": "ok", "chunks": len(chunks)}), 200
    except Exception:
        logger.exception("Indexing failed")
        return jsonify({"status": "error", "message": "Indexing failed"}), 500

@summarizer_bp.route("/upload/<upload_id>/smart", methods=["POST"])
def smart(upload_id):
    data = request.get_json() or {}
    raw_question = (data.get("question") or "").strip()
    history = data.get("history") or []

    if not raw_question:
        return jsonify({"status": "error", "message": "No question"}), 400

    def clean_user_question(q: str) -> str:
        if not q:
            return ""
        q = q.strip()

        # cut off any appended background/instructions
        q = re.split(r"here'?s? some background from", q, flags=re.IGNORECASE)[0]
        q = re.split(r"here is some background from", q, flags=re.IGNORECASE)[0]
        q = re.split(r"here is some background", q, flags=re.IGNORECASE)[0]
        q = re.split(r"answer the question using only the study notes below", q,
                     flags=re.IGNORECASE)[0]

        # only keep the first line (the actual user question)
        q = q.splitlines()[0]

        patterns = [
            r"^answer the student's question.*",
            r"^answer the question using only the notes below.*",
            r"^answer the question using only the study notes below.*",
            r"^you are a helpful (ai )?(study )?assistant.*",
            r"^use only the notes below.*",
            r"^use only the study notes below.*",
        ]
        for p in patterns:
            q = re.sub(p, "", q, flags=re.IGNORECASE)

        q = " ".join(q.split()).strip()
        return q

    question = clean_user_question(raw_question)
    if not question:
        return jsonify({
            "status": "error",
            "message": "Please type only your question."
        }), 400

    save_id = _get_save_id()
    entry = None

    if save_id:
        try:
            meta = load_save_meta(save_id)
            entry = next((e for e in meta.get("uploads", []) if e.get("id") == upload_id), None)
        except Exception:
            entry = None
    else:
        entries = load_meta()
        entry = next((x for x in entries if x.get("id") == upload_id), None)

    if not entry:
        return jsonify({"status": "error", "message": "Upload not found"}), 404

    summary = (entry.get("summary") or entry.get("short") or "").strip()
    bullets = entry.get("bullets") or []
    exam_notes = entry.get("exam_notes") or []

    parts = []
    if exam_notes:
        parts.append("Exam notes:")
        parts.extend(exam_notes[:8])
    if bullets:
        parts.append("Key points:")
        parts.extend(bullets[:12])
    if summary:
        parts.append("Summary:")
        parts.append(summary[:2500])

    context_text = "\n".join(parts).strip()

    model, tokenizer, _ = try_load_summarizer()

    prompt_parts = []
    prompt_parts.append("Answer the student's question clearly.")
    if context_text:
        prompt_parts.append("Background from the PDF (use only if helpful):")
        prompt_parts.append(context_text)
    prompt_parts.append(f"Question: {question}")
    prompt_parts.append("Answer in 2–4 simple sentences.")

    if isinstance(history, list) and history:
        hist_lines = []
        for turn in history[-6:]:
            r = (turn.get("role") or "user").lower()
            c = (turn.get("content") or turn.get("text") or "").strip()
            if c:
                hist_lines.append(f"{r}: {c}")
        if hist_lines:
            prompt_parts.append("Conversation so far:")
            prompt_parts.append("\n".join(hist_lines))

    prompt = "\n\n".join(prompt_parts)

    try:
        raw_answer = led_generate(model, tokenizer, prompt, max_out=320).strip()
    except Exception:
        logger.exception("Smart search generation failed")
        return jsonify({"status": "error", "message": "Answer generation failed"}), 500

    def clean_model_answer(ans: str) -> str:
        if not ans:
            return ""
        ans = ans.strip()

        ans = re.sub(
            r"^you are a helpful ai (study )?assistant[.!?\s]*",
            "",
            ans,
            flags=re.IGNORECASE,
        )
        ans = re.sub(
            r"^answer clearly and helpfully[.!?\s]*",
            "",
            ans,
            flags=re.IGNORECASE,
        )
        ans = re.sub(
            r"^answer the student's question clearly[.!?\s]*",
            "",
            ans,
            flags=re.IGNORECASE,
        )

        ans = ans.strip()

        # keep only first 2–3 sentences so it can’t dump the whole context
        sentences = re.split(r'(?<=[.!?])\s+', ans)
        sentences = [s for s in sentences if s.strip()]
        if len(sentences) > 3:
            ans = " ".join(sentences[:3])
        return ans.strip()

    answer_text = clean_model_answer(raw_answer) or raw_answer

    return jsonify({
        "status": "ok",
        "answer": answer_text,
        "mode": "ai_chat",
    }), 200
