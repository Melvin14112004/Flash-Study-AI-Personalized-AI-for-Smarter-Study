# backend/routes/quizgen_routes.py
import os
import json
from flask import Blueprint, request, jsonify
from config import SAVES_DIR
from utils.quizgen import generate_quiz   # or utils.mindmap if that's where you put it

quizgen_bp = Blueprint("quizgen", __name__)


@quizgen_bp.route("/upload/<upload_id>/generate_quiz", methods=["POST"])
def api_generate_quiz(upload_id):
    save_id = request.args.get("save_id")
    difficulty = (request.args.get("difficulty") or "easy").lower()

    if not save_id:
        return jsonify({"message": "save_id is required"}), 400

    if difficulty not in ("easy", "medium", "hard"):
        return jsonify({"message": "Invalid difficulty"}), 400

    save_path = os.path.join(SAVES_DIR, save_id)
    pdf_path = os.path.join(save_path, "uploads", f"{upload_id}.pdf")

    result = generate_quiz(
        pdf_path,
        save_path=save_path,
        upload_id=upload_id,
        difficulty=difficulty,
    )

    return jsonify({"status": "ok", **result}), 200


@quizgen_bp.route("/upload/<upload_id>/quiz", methods=["GET"])
def api_get_quiz(upload_id):
    save_id = request.args.get("save_id")
    if not save_id:
        return jsonify({"message": "save_id is required"}), 400

    quiz_path = os.path.join(SAVES_DIR, save_id, "quiz", f"{upload_id}.json")
    if not os.path.exists(quiz_path):
        return jsonify({"difficulty": None, "questions": []}), 200

    try:
        with open(quiz_path, "r", encoding="utf-8") as f:
            quiz = json.load(f)
    except Exception:
        return jsonify({"difficulty": None, "questions": []}), 200

    return jsonify(quiz), 200
