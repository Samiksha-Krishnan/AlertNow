"""
Auth endpoints: register (citizen self-signup), login (citizen or authority),
logout, and a `me` check used by the frontend on load to restore a session.

Sessions are Flask's built-in signed-cookie session (server-side state is just
the DB row) — no extra auth library needed for this app's scope.
"""

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from db import db
from models import User

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    password = data.get("password") or ""

    if not name or not email or not phone or len(password) < 6:
        return jsonify({"error": "All fields are required and password must be at least 6 characters."}), 400

    exists = User.query.filter((User.email == email) | (User.phone == phone)).first()
    if exists:
        return jsonify({"error": "An account with this email or phone already exists."}), 409

    user = User(
        name=name,
        email=email,
        phone=phone,
        password_hash=generate_password_hash(password),
        role="citizen",
    )
    db.session.add(user)
    db.session.commit()

    session.clear()
    session["user_id"] = user.id
    session["role"] = user.role

    return jsonify({"user": user.to_public()}), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    role = data.get("role") if data.get("role") in ("citizen", "authority") else "citizen"
    identifier = (data.get("identifier") or "").strip().lower()
    password = data.get("password") or ""

    if not identifier or len(password) < 6:
        return jsonify({"error": "Enter valid sign-in details."}), 400

    user = User.query.filter(
        User.role == role,
        db.or_(User.email == identifier, User.phone == identifier),
    ).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Account not found or password is incorrect."}), 401

    session.clear()
    session["user_id"] = user.id
    session["role"] = user.role

    return jsonify({"user": user.to_public()})


@bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@bp.get("/me")
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"user": None})
    user = db.session.get(User, user_id)
    if not user:
        session.clear()
        return jsonify({"user": None})
    return jsonify({"user": user.to_public()})
