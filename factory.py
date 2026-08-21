"""
The actual Flask app factory, kept separate from app.py so scripts like
init_db.py can build an app instance (e.g. with load_ai=False) without
triggering app.py's module-level `app = create_app()` — that line exists only
so WSGI servers (gunicorn `app:app`, `flask run`) have something to import.
"""

import os

from flask import Flask, jsonify, request, send_from_directory
from PIL import Image

from auth import bp as auth_bp
from config import Config
from db import db
from hazard_model import classify_frame, load_model
from incidents import bp as incidents_bp


def create_app(load_ai=True):
    app = Flask(__name__, static_folder="static", static_url_path="")
    app.config.from_object(Config)
    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    app.register_blueprint(auth_bp)
    app.register_blueprint(incidents_bp)

    if load_ai:
        # Load the CLIP model once at startup, not on the first request, so
        # the first browser request isn't slow.
        load_model()

    @app.route("/")
    def index():
        # No caching for the single-page app shell: this file changes
        # often during development, and a stale cached copy in the browser
        # means clicks on newly-added buttons (like "Use webcam") silently
        # do nothing because the old JS in memory doesn't define them yet.
        resp = send_from_directory(app.static_folder, "index.html")
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return resp

    @app.route("/analyze", methods=["POST"])
    def analyze():
        if "image" not in request.files:
            return jsonify({"error": "no 'image' file in request"}), 400

        file = request.files["image"]
        try:
            pil_image = Image.open(file.stream).convert("RGB")
        except Exception as exc:  # noqa: BLE001 - report any decode failure to the client
            return jsonify({"error": f"could not read image: {exc}"}), 400

        label, confidence, tag = classify_frame(pil_image)

        return jsonify(
            {
                "label": label,
                "confidence": confidence,
                "hazard": tag,  # e.g. "FIRE", "POTHOLE", or null if nothing hazardous
                "is_hazard": tag is not None,
            }
        )

    return app
