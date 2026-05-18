# backend/routes/mindmap_routes.py
import os
import json
from flask import Blueprint, request, jsonify
from config import SAVES_DIR

mindmap_bp = Blueprint("mindmap", __name__)

# NEW — avoid route conflict
@mindmap_bp.route("/mindmap/<save_name>/<pdf_id>", methods=["POST"])
def generate_mindmap(save_name, pdf_id):
    save_path = os.path.join(SAVES_DIR, save_name)
    meta_path = os.path.join(save_path, "meta.json")

    if not os.path.exists(meta_path):
        return jsonify({"status": "error", "message": "Save not found"}), 404

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    entry = next((x for x in meta["pdfs"] if x["id"] == pdf_id), None)
    if not entry:
        return jsonify({"status":"error","message":"PDF not found"}), 404

    summary = entry.get("summary", "")
    if not summary:
        return jsonify({"status":"error","message":"Summary missing"}), 400

    mindmap_text = (
        f"ROOT: {entry['name']}\n\n" +
        "\n".join(f"- {b}" for b in entry["bullets"][:10])
    )

    out_path = os.path.join(save_path, "mindmaps", f"{pdf_id}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(mindmap_text)

    return jsonify({
        "status": "ok",
        "mindmap": f"{pdf_id}.txt",
        "path": out_path
    }), 200
