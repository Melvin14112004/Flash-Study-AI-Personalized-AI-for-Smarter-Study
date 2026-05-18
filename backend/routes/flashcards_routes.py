# backend/routes/flashcards_routes.py
import os
import json
from flask import Blueprint, request, jsonify
from config import SAVES_DIR

flashcards_bp = Blueprint("flashcards", __name__)

@flashcards_bp.route("/save/<save_name>/<pdf_id>/flashcards", methods=["POST"])
def generate_flashcards(save_name, pdf_id):
    """
    Flashcard generation — Mode C1:
    ▶ one flashcard per bullet
    """
    save_path = os.path.join(SAVES_DIR, save_name)
    meta_path = os.path.join(save_path, "meta.json")

    # Check save exists
    if not os.path.exists(meta_path):
        return jsonify({"status": "error", "message": "Save not found"}), 404

    # Load meta.json
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # Find PDF entry
    entry = next((x for x in meta["pdfs"] if x["id"] == pdf_id), None)
    if not entry:
        return jsonify({"status": "error", "message": "PDF not found"}), 404

    bullets = entry.get("bullets", [])
    if not bullets:
        return jsonify({"status": "error", "message": "No content for flashcards"}), 400

    # ----------------------------
    # Generate Flashcards (C1)
    # ----------------------------
    flashcards = []
    for i, bullet in enumerate(bullets, start=1):
        flashcards.append({
            "id": f"{pdf_id}_{i}",
            "question": f"What does this mean?\n\n\"{bullet}\"",
            "answer": bullet
        })

    # Save flashcards JSON
    out_path = os.path.join(save_path, "flashcards", f"{pdf_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(flashcards, f, indent=4)

    return jsonify({
        "status": "ok",
        "count": len(flashcards),
        "flashcards_file": f"{pdf_id}.json",
        "path": out_path
    }), 200
