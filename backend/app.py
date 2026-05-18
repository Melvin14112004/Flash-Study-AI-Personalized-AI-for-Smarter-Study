# backend/app.py
import os
import logging
import sys
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

# Import config values
from config import (
    FRONTEND_DIST,
    ALLOWED_ORIGINS,
    UPLOADS_DIR,
    SAVES_DIR,
    DATA_DIR,
)

# ---------------------------------------
# Ensure required folders exist
# ---------------------------------------
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(SAVES_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------------------
# Logging setup
# ---------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("flash-study-backend")

# ---------------------------------------
# Flask initialization
# ---------------------------------------
app = Flask(__name__, static_folder=FRONTEND_DIST, static_url_path="/")

from flask_cors import CORS

CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# ---------------------------------------
# 🔥 IMPORTANT — Load routes package FIRST
# ---------------------------------------
from routes import summarizer_routes, flashcards_routes, mindmap_routes, quizgen_routes, save_routes    
# Import route blueprints
# ---------------------------------------
from routes.summarizer_routes import summarizer_bp
from routes.flashcards_routes import flashcards_bp
from routes.mindmap_routes import mindmap_bp
from routes.quizgen_routes import quizgen_bp
from routes.save_routes import save_bp


# ---------------------------------------
# Register blueprints
# ---------------------------------------
app.register_blueprint(summarizer_bp, url_prefix="/api")
app.register_blueprint(flashcards_bp, url_prefix="/api")
app.register_blueprint(mindmap_bp, url_prefix="/api")
app.register_blueprint(quizgen_bp, url_prefix="/api")
app.register_blueprint(save_bp)

# ---------------------------------------
# Serve frontend (if built)
# ---------------------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if os.path.exists(FRONTEND_DIST) and os.path.isdir(FRONTEND_DIST):
        full_path = os.path.join(FRONTEND_DIST, path)
        if path and os.path.exists(full_path):
            return send_from_directory(FRONTEND_DIST, path)
        return send_from_directory(FRONTEND_DIST, "index.html")

    return jsonify({"status": "ok", "message": "Flash Study AI backend running"}), 200


if __name__ == "__main__":
    logger.info("Starting Flash Study AI backend (dev) on 0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)

# near the bottom of your main app file (where app exists)
def _print_routes():
    print("=== Flask URL map ===")
    for rule in app.url_map.iter_rules():
        methods = ",".join(sorted(rule.methods))
        print(f"{rule.endpoint:40s} {rule.rule:40s} [{methods}]")
    print("=====================")

_print_routes()
