# Built for Hugging Face Spaces (Docker SDK), which expects the app to
# listen on port 7860 — but this also works on Render, Railway, Fly.io,
# or any other Docker-based host. Requires DATABASE_URL and SECRET_KEY to
# be set as environment variables / secrets at runtime (see README.md).

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so Docker can cache this layer across rebuilds
# (only re-runs when requirements.txt actually changes).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then copy the actual app code.
COPY *.py ./
COPY static ./static

# Pre-download the CLIP model weights at build time instead of on first
# request, so the deployed app responds immediately instead of stalling
# on its first visitor. This only touches hazard_model.py (no DB import),
# so it doesn't need DATABASE_URL to be available at build time.
RUN python -c "from hazard_model import load_model; load_model()"

ENV PORT=7860
EXPOSE 7860

# init_db.py is idempotent (checks before seeding), so it's safe to run on
# every container start — creates tables on Neon if they don't exist yet,
# and seeds the demo authority account + demo incidents once.
CMD ["sh", "-c", "python init_db.py && python app.py"]
