"""
Creates tables (if they don't already exist on Neon) and seeds:
  - one demo authority account: authority@alertnow.gov / authority123
  - three demo "system" incidents, matching the original showcase data

Run once, after DATABASE_URL is set in .env:
    python init_db.py
"""

from werkzeug.security import generate_password_hash

from factory import create_app
from db import db
from models import Incident, User

app = create_app(load_ai=False)  # no need to load the CLIP model just to touch the DB

with app.app_context():
    db.create_all()

    if not User.query.filter_by(role="authority").first():
        db.session.add(
            User(
                name="Ops Desk",
                email="authority@alertnow.gov",
                phone="0000000000",
                password_hash=generate_password_hash("authority123"),
                role="authority",
            )
        )
        print("Seeded demo authority account -> authority@alertnow.gov / authority123")
    else:
        print("Authority account already exists, skipping seed.")

    if Incident.query.count() == 0:
        demo = [
            dict(
                type="Traffic Signal Fault",
                location_text="Central Bus Depot",
                location_detail="Ward 14 · Junction 3",
                description="Signal is stuck on red and traffic is backing up across the junction.",
                severity="HIGH",
                dept="TRAFFIC CONTROL",
                status="In Progress",
                map_x=63,
                map_y=38,
                reporter_name="A. Kumar",
                source="system",
            ),
            dict(
                type="Water Leak",
                location_text="Harbor View Road",
                location_detail="Near community clinic",
                description="Water is pooling along the curb and entering the pedestrian path.",
                severity="MEDIUM",
                dept="PUBLIC WORKS",
                status="Assigned",
                map_x=36,
                map_y=57,
                reporter_name="R. Das",
                source="system",
            ),
            dict(
                type="Streetlight Outage",
                location_text="North Gate Avenue",
                location_detail="Block C",
                description="Three streetlights are out near the evening bus stop.",
                severity="LOW",
                dept="MUNICIPAL SERVICES",
                status="Under Review",
                map_x=75,
                map_y=66,
                reporter_name="S. Rao",
                source="system",
            ),
        ]
        for d in demo:
            db.session.add(Incident(**d))
        print("Seeded 3 demo incidents.")
    else:
        print("Incidents already exist, skipping seed.")

    db.session.commit()
    print("Database ready.")
