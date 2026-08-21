"""
Database models for Alert Now.

Two tables: `users` (citizen + authority accounts) and `incidents` (civic
reports). Kept deliberately close to the shape the original localStorage
version used, so the frontend's rendering code barely has to change.
"""

from datetime import datetime, timezone

from db import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=True)
    phone = db.Column(db.String(40), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="citizen")  # citizen | authority
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    incidents = db.relationship("Incident", back_populates="reported_by", lazy="dynamic")

    def to_public(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
        }


class Incident(db.Model):
    __tablename__ = "incidents"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(60), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    severity = db.Column(db.String(10), nullable=False, default="MEDIUM")  # LOW | MEDIUM | HIGH
    status = db.Column(db.String(20), nullable=False, default="Submitted")
    dept = db.Column(db.String(60), nullable=False, default="MUNICIPAL SERVICES")

    location_text = db.Column(db.String(160), default="Reported location")
    location_detail = db.Column(db.String(160), default="")
    map_x = db.Column(db.Float, default=50.0)
    map_y = db.Column(db.Float, default=50.0)

    photo_path = db.Column(db.String(255), nullable=True)

    # AI hazard-detection result captured at submit time, kept for audit/analytics.
    ai_label = db.Column(db.String(255), nullable=True)
    ai_hazard = db.Column(db.String(30), nullable=True)
    ai_confidence = db.Column(db.Float, nullable=True)

    reported_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reporter_name = db.Column(db.String(120), default="Citizen")
    source = db.Column(db.String(20), default="citizen")  # citizen | system

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reported_by = db.relationship("User", back_populates="incidents")

    def to_public(self):
        return {
            "id": self.id,
            "type": self.type,
            "location": self.location_text,
            "locationDetail": self.location_detail,
            "description": self.description,
            "severity": self.severity,
            "dept": self.dept,
            "status": self.status,
            # created_at is a naive datetime but always stored in UTC (datetime.utcnow());
            # attach tzinfo before .timestamp() or Python treats it as local time and
            # every "time ago" on the frontend is off by the server's UTC offset.
            "timestamp": (
                int(self.created_at.replace(tzinfo=timezone.utc).timestamp() * 1000)
                if self.created_at
                else None
            ),
            "mapX": self.map_x,
            "mapY": self.map_y,
            "reportedBy": self.reporter_name,
            "reportedById": self.reported_by_id,
            "source": self.source,
            "photo": f"/uploads/{self.photo_path}" if self.photo_path else None,
            "ai": (
                {"label": self.ai_label, "hazard": self.ai_hazard, "confidence": self.ai_confidence}
                if self.ai_hazard
                else None
            ),
        }
