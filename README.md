# OnePick — Hackathon FII Practic 2026

> Stop choosing. Start going. One recommendation, not fifty.

Python-only stack: **FastAPI + SQLite + Streamlit + Geoapify + Claude**.

See `PROJECT_PLAN.md`, `BUSINESS_MODEL_CANVAS.md`, and `COMPETITIVE_ANALYSIS.md` for the strategy and role split.

---

## Quickstart

### 1. Setup (once)

```bash
# Clone, then:
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy env template and fill in keys
cp .env.example .env
# Edit .env — at minimum set JWT_SECRET. Other keys are optional (see below).
```

### 2. Run the backend

```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

> Why `python -m`? On Windows (especially PowerShell), the bare `uvicorn` command often isn't on PATH because `pip` installs the executable into a Scripts directory that isn't in `$Env:PATH`. `python -m uvicorn` runs it as a module and always works as long as the package is installed.

Open <http://localhost:8000/docs> to see all endpoints (FastAPI auto-generates this).

### 3. Run the frontend (in a second terminal)

```bash
python -m streamlit run frontend/app.py
```

Open <http://localhost:8501>.

### 4. Seed demo data (optional but recommended before demo)

```bash
python -m backend.tests.seed
```

Creates two demo accounts (`demo@onepick.app` and `ana@onepick.app`, password `demo1234` for both) with a friendship, a group, and pre-built streaks so the UI doesn't look empty during the demo.

---

## Environment variables

All optional except `JWT_SECRET`. The app degrades gracefully when keys are missing:

| Variable | Required? | What happens if missing |
|---|---|---|
| `JWT_SECRET` | Yes (any secret string) | Auth tokens won't be secure but app runs |
| `GEOAPIFY_API_KEY` | No | Falls back to a small mock POI dataset |
| `ANTHROPIC_API_KEY` | No | "Why this pick" uses a template string |
| `BACKEND_URL` | No | Defaults to `http://localhost:8000` |
| `MOCK_MODE` | No | Set to `true` to run the Streamlit frontend without any backend |

---

## Repo layout

```
.
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── db.py                    # SQLAlchemy models + session
│   ├── auth.py                  # JWT signup/login + get_current_user dependency
│   ├── modules/
│   │   ├── geoapify_client.py   # Wraps Geoapify Places API (Role 2)
│   │   ├── places.py            # /pick, /reroll, /visited, /thumbs, /itinerary (Role 2)
│   │   ├── social.py            # /friends, /groups, /groups/{id}/pick (Role 3)
│   │   └── gamification.py      # /me/streak, /me/history (Role 3)
│   └── tests/seed.py            # Demo data
├── frontend/
│   ├── app.py                   # Streamlit entry + auth gate
│   ├── api_client.py            # All HTTP calls, with MOCK_MODE fallback
│   ├── style.css                # Brand styling
│   └── pages/                   # Streamlit auto-discovers these
│       ├── 1_Home.py
│       ├── 2_Result.py
│       ├── 3_Itinerary.py
│       ├── 4_Friends.py
│       ├── 5_Streak.py
│       └── 6_History.py
├── PROJECT_PLAN.md
├── BUSINESS_MODEL_CANVAS.md
├── COMPETITIVE_ANALYSIS.md
├── requirements.txt
└── .env.example
```

---

## Who owns what (quick reference)

| Role | Files |
|---|---|
| **Role 1 — Tech Lead** | `backend/main.py`, `backend/db.py`, `backend/auth.py`, `frontend/api_client.py`, deploy config |
| **Role 2 — Recommendations** | `backend/modules/geoapify_client.py`, `backend/modules/places.py` |
| **Role 3 — Social & Gamification** | `backend/modules/social.py`, `backend/modules/gamification.py` |
| **Role 4 — Frontend** | `frontend/app.py`, `frontend/pages/*`, `frontend/style.css` |
| **Role 5 — Product & Pitch** | `docs/*`, deck, demo video — no code |

Full detail in `PROJECT_PLAN.md`.

---

## Deploy targets

Per the plan, deploy by **H+4** to avoid debugging hosting at 4am:

- **Backend** — [Render.com](https://render.com) free tier (auto-deploys from GitHub). Set env vars in the Render dashboard.
- **Frontend** — [Streamlit Community Cloud](https://streamlit.io/cloud) (free, GitHub-connected, gives a `your-app.streamlit.app` URL).
- **Fallback** — run locally and expose with `ngrok http 8000`.

The deployed URLs go straight in the pitch deck as a QR code judges can scan.
