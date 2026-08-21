---
title: Alert Now
emoji: 🚨
colorFrom: red
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Alert Now — Civic Incident Response

A citizen-to-authority incident reporting app: citizens photograph an issue
(fire, smoke, pothole, water leak, etc.), an on-device AI model suggests the
category + severity from the photo, and authority accounts triage/route the
report through a status workflow. Persisted on **Neon (serverless Postgres)**
instead of browser storage, so reports and accounts survive across devices
and sessions.

This is a rebuild of the original localStorage-only prototype
([fire-env-detector/static/index.html](../fire-env-detector/static/index.html))
with a real backend wired in. The AI photo analysis is the *same* CLIP model
and logic from that project, reused unchanged — see
[hazard_model.py](hazard_model.py).

## Stack

- **Backend**: Flask (Python), SQLAlchemy
- **Database**: Neon Postgres (falls back to a local SQLite file if
  `DATABASE_URL` isn't set, so the app still runs before Neon is wired up)
- **AI**: OpenAI CLIP (`openai/clip-vit-base-patch32`), zero-shot image
  classification against a list of hazard/normal-scene text prompts — no
  training required. Runs locally, no API key, no per-request cost.
- **Frontend**: the original single-file vanilla JS/CSS UI, now talking to
  real API endpoints instead of `localStorage`.

## 1. Setup

```bash
python -m venv venv
```

Activate it (PowerShell):

```bash
venv\Scripts\Activate.ps1
```

Install dependencies (`requirements.txt` already points at the CPU-only
PyTorch build, so this is one command):

```bash
pip install -r requirements.txt
```

## 2. Configure Neon

1. Create a free project at [neon.tech](https://neon.tech) if you don't have
   one.
2. Copy the connection string from the project dashboard.
3. Copy `.env.example` to `.env` and paste it in:

```
DATABASE_URL=postgresql://USER:PASSWORD@YOUR-PROJECT.neon.tech/neondb?sslmode=require
SECRET_KEY=some-long-random-string
PORT=5000
```

`SECRET_KEY` signs the login session cookie — any long random string works;
`python -c "import secrets; print(secrets.token_hex(32))"` generates one.

## 3. Initialize the database

Creates the `users`/`incidents` tables on Neon and seeds a demo authority
account + 3 demo incidents:

```bash
python init_db.py
```

This prints a demo authority login:

```
authority@alertnow.gov / authority123
```

Citizen accounts are created by anyone via the app's own "Create a new
citizen account" form — there's no separate seed needed for those.

## 4. Run it

```bash
python app.py
```

Open **http://localhost:5000**. First request loads the CLIP model (~350MB
download the very first time it's ever run on this machine, cached
afterward).

## How the pieces fit together

| Concern | File |
|---|---|
| App wiring / routes for `/` and `/analyze` | [factory.py](factory.py) |
| Runner (`python app.py`) | [app.py](app.py) |
| DB models (`User`, `Incident`) | [models.py](models.py) |
| Auth endpoints (register/login/logout/me) | [auth.py](auth.py) |
| Incident endpoints (list/create/update status) | [incidents.py](incidents.py) |
| AI hazard classifier (unchanged from the original) | [hazard_model.py](hazard_model.py) |
| One-time table creation + demo seed data | [init_db.py](init_db.py) |
| Frontend (citizen + authority UI) | [static/index.html](static/index.html) |
| Uploaded incident photos | `uploads/` (git-ignored) |

### API summary

- `POST /api/auth/register` — citizen self-signup
- `POST /api/auth/login` — `{role, identifier, password}`, `role` is
  `citizen` or `authority`
- `POST /api/auth/logout`
- `GET /api/auth/me` — restores the session on page load
- `GET /api/incidents` — list all incidents (requires login)
- `POST /api/incidents` — citizen submits a report (`multipart/form-data`:
  `photo`, `type`, `severity`, `description`, `locationDetail`, plus the
  AI result fields `aiLabel`/`aiHazard`/`aiConfidence` if a photo was
  analyzed)
- `PATCH /api/incidents/<id>` — authority updates `{status}`
- `POST /analyze` — `multipart/form-data` field `image`; returns
  `{label, confidence, hazard, is_hazard}` from the CLIP classifier
- `GET /uploads/<filename>` — serves an uploaded incident photo

### AI hazard categories

Edit `LABELS`/`HAZARD_LABELS`/`CONFIDENCE_THRESHOLD` in
[hazard_model.py](hazard_model.py) to add/tune what the model looks for.
Currently: fire, smoke, flooding, potholes, fights, car accidents, injuries
— each mapped to a report category + department in
[incidents.py](incidents.py)'s `DEPT_FOR_CATEGORY`.

## Deploying (free) — Hugging Face Spaces

Vercel doesn't work for this app (serverless functions can't fit
PyTorch/Transformers, and have no persistent memory for a loaded model or
disk for uploads). Hugging Face Spaces' free Docker tier is a good fit
instead: generous free CPU/RAM, built for exactly this kind of ML demo, and
this repo already has the [Dockerfile](Dockerfile) and the Space metadata
block at the top of this README ready for it.

1. **Create the Space**: go to [huggingface.co/new-space](https://huggingface.co/new-space)
   → pick an owner + name → **SDK: Docker** → **Docker template: Blank** →
   set visibility → Create Space. This gives you an empty Space with its own
   git repo at `https://huggingface.co/spaces/<you>/<space-name>`.

2. **Push this code to it** (from this project folder):
   ```bash
   git remote add hf https://huggingface.co/spaces/<you>/<space-name>
   git push hf main
   ```
   The first push will ask for a username/password — use your HF username
   and, as the password, an **access token** from
   [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
   (needs *write* scope). Paste the token in your own terminal when
   prompted — never share it in chat or a file.

3. **Add secrets**: on the Space page → **Settings** → **Variables and
   secrets** → **New secret**, add:
   - `DATABASE_URL` — your Neon connection string (same value as your local
     `.env`)
   - `SECRET_KEY` — same value as your local `.env`, or a fresh random
     string

4. **Watch it build**: the Space's **Logs** tab shows the Docker build (CLIP
   model download happens here) and then the app starting. First build
   takes a few minutes; the model is cached in the image after that.

5. Once it says "Running", your app is live at
   `https://<you>-<space-name>.hf.space`.

**Keeping it updated**: every `git push hf main` after a code change
redeploys it. If you'd rather just push to GitHub and have it auto-sync to
the Space, add a GitHub Actions workflow that pushes to the `hf` remote
using an `HF_TOKEN` repo secret — ask if you want that set up.

**Note on uploaded photos**: Spaces' default storage is ephemeral like most
free container hosts — uploaded incident photos won't survive a Space
restart/rebuild. Fine for a demo; move to persistent storage (S3-compatible,
Cloudflare R2, etc.) before relying on this for real reports long-term.

## Known limitations

- **CLIP classifies the whole photo as one scene** — it doesn't localize
  small objects. It's reliable for things that dominate the frame (fire,
  smoke, a crash) and less so for a pothole shot from far away. See the
  original project's README §8 for more on this and how to upgrade to a
  dedicated object detector later if needed.
- **Uploaded photos are stored on local disk** (`uploads/`), not in Neon or
  object storage. Fine for local/single-instance use; move to S3/R2 (or
  similar) before deploying to a platform with an ephemeral filesystem.
- **No CSRF protection** beyond the session cookie's `SameSite=Lax` — fine
  for local/demo use; add CSRF tokens before exposing this publicly.
- **Authority accounts** aren't self-service by design (matches the original
  app's "restricted to approved operational accounts") — create more by
  inserting rows via `init_db.py`-style scripts, or add an admin CLI if
  you need several.
