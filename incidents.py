"""
Incident report endpoints: list, create (citizen, with photo upload), and
status updates (authority). Also serves uploaded photos back out.
"""

import os
import random
import uuid

from flask import Blueprint, current_app, jsonify, request, send_from_directory, session

from db import db
from models import Incident, User

bp = Blueprint("incidents", __name__)

# Mirrors the category -> responsible desk mapping from the original
# client-only version, now enforced server-side.
DEPT_FOR_CATEGORY = {
    "Fire": "FIRE DEPT.",
    "Water Leak": "PUBLIC WORKS",
    "Fight / Assault": "POLICE",
    "Road Accident": "POLICE / TRAFFIC",
    "Medical Emergency": "MEDICAL / EMS",
    "Pothole": "PUBLIC WORKS",
    "Traffic Signal Fault": "TRAFFIC CONTROL",
    "Streetlight Outage": "MUNICIPAL SERVICES",
    "Fallen Tree": "MUNICIPAL SERVICES",
    "Illegal Dumping": "MUNICIPAL SERVICES",
}
VALID_STATUSES = {"Submitted", "Under Review", "Assigned", "In Progress", "Resolved", "Closed"}
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp", "gif"}


def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None


def require_login():
    user = current_user()
    if not user:
        return None, (jsonify({"error": "Sign in required."}), 401)
    return user, None


@bp.get("/api/incidents")
def list_incidents():
    user, err = require_login()
    if err:
        return err
    items = [i.to_public() for i in Incident.query.order_by(Incident.created_at.desc()).all()]
    return jsonify({"incidents": items})


@bp.post("/api/incidents")
def create_incident():
    user, err = require_login()
    if err:
        return err
    if user.role != "citizen":
        return jsonify({"error": "Only citizen accounts can submit reports."}), 403

    itype = (request.form.get("type") or "").strip() or "Pothole"
    severity = (request.form.get("severity") or "Medium").strip().upper()
    if severity not in ("LOW", "MEDIUM", "HIGH"):
        severity = "MEDIUM"
    description = (request.form.get("description") or "").strip() or "No description provided."
    location_detail = (request.form.get("locationDetail") or "").strip()
    ai_label = (request.form.get("aiLabel") or "").strip() or None
    ai_hazard = (request.form.get("aiHazard") or "").strip() or None
    ai_confidence_raw = request.form.get("aiConfidence")
    try:
        ai_confidence = float(ai_confidence_raw) if ai_confidence_raw else None
    except ValueError:
        ai_confidence = None

    photo_path = None
    file = request.files.get("photo")
    if not file or not file.filename:
        return jsonify({"error": "A photo is required to submit a report."}), 400

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXT:
        return jsonify({"error": "Unsupported image type."}), 400
    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(current_app.config["UPLOAD_DIR"], filename))
    photo_path = filename

    incident = Incident(
        type=itype,
        description=description,
        severity=severity,
        status="Submitted",
        dept=DEPT_FOR_CATEGORY.get(itype, "MUNICIPAL SERVICES"),
        location_text="Reported location",
        location_detail=location_detail,
        map_x=25 + random.random() * 55,
        map_y=25 + random.random() * 50,
        photo_path=photo_path,
        ai_label=ai_label,
        ai_hazard=ai_hazard,
        ai_confidence=ai_confidence,
        reported_by_id=user.id,
        reporter_name=user.name,
        source="citizen",
    )
    db.session.add(incident)
    db.session.commit()

    return jsonify({"incident": incident.to_public()}), 201


@bp.patch("/api/incidents/<int:incident_id>")
def update_incident(incident_id):
    user, err = require_login()
    if err:
        return err
    if user.role != "authority":
        return jsonify({"error": "Only authority accounts can update incidents."}), 403

    incident = db.session.get(Incident, incident_id)
    if not incident:
        return jsonify({"error": "Incident not found."}), 404

    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in VALID_STATUSES:
        return jsonify({"error": "Invalid status."}), 400

    incident.status = status
    db.session.commit()

    return jsonify({"incident": incident.to_public()})


@bp.get("/uploads/<path:filename>")
def get_upload(filename):
    return send_from_directory(current_app.config["UPLOAD_DIR"], filename)
