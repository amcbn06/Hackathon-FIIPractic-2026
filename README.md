# South — Hackathon FII Practic 2026

> **Stop choosing. Start going.** One recommendation, not fifty.

You tell South a vibe (café, park, museum, bar, viewpoint…) and a city — it hands
you **exactly one** place, with a reason to go. No endless lists, no decision
paralysis. Visit it to grow a streak, roll with friends and groups, chain vibes
into an itinerary, crowdsource new spots, and stash your own secret finds.

This repo is a full rewrite of the original Streamlit prototype:

| Layer | Before | Now |
|---|---|---|
| **Frontend** | Streamlit (Python) | **React + Vite + Tailwind** SPA (JavaScript) |
| **Backend** | FastAPI (single-file routers) | **FastAPI**, cleanly layered (config / models / schemas / services / routers) |
| **Data** | SQLite | SQLite (same 44 curated Iași places) |

---

## Architecture

```
.
├── backend/                 # FastAPI application
│   ├── config.py            # Settings from env (graceful defaults)
│   ├── database.py          # Engine, session, init_db
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic request/response models
│   ├── auth.py              # JWT + password hashing + dependencies
│   ├── services/            # Business logic
│   │   ├── recommend.py     #   the "one pick" weighted sampling
│   │   ├── gamification.py  #   streak rules
│   │   └── ai.py            #   optional Claude reasons + fallbacks
│   ├── routers/             # HTTP endpoints, one file per domain
│   │   ├── auth.py  places.py  social.py
│   │   ├── gamification.py  itinerary.py  spots.py
│   ├── data/seed_places.json
│   ├── seed.py              # Demo accounts + places
│   └── main.py              # App entry, CORS, router mounting
│
├── web/                     # React + Vite + Tailwind frontend
│   ├── src/
│   │   ├── lib/api.js        # Typed-ish API client (token in localStorage)
│   │   ├── context/          # Auth context
│   │   ├── components/       # Layout, UI primitives, toasts
│   │   └── pages/            # Discover, Result, Itinerary, Friends,
│   │                         #   Streak, Tracker, Spots, Login
│   ├── vite.config.js        # Dev proxy: /api -> backend
│   └── package.json
│
├── requirements.txt
└── .env.example
```

---

## Quickstart

### 1. Backend

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # set JWT_SECRET at minimum
python -m backend.seed --reset     # demo accounts + curated places

uvicorn backend.main:app --reload --port 8000
```

Interactive API docs: <http://localhost:8000/docs>

### 2. Frontend

```bash
cd web
npm install
npm run dev
```

Open <http://localhost:5173>. In dev, the frontend proxies `/api` to the backend
on port 8000 — no CORS setup needed.

### 3. Demo login

```
demo@onepick.app / demo1234     (admin — can approve/reject community places)
ana@onepick.app  / demo1234
```

---

## Features

- **One pick, not fifty** — weighted random sampling over crowdsourced quality,
  novelty (skips places you saw recently), whether it's open now, and a little jitter.
- **Reroll / Visited / Thumbs** — up to 3 rerolls a day; visiting feeds your streak.
- **Streaks** — daily-visit streak with a 35-day heatmap.
- **Friends & groups** — add by invite code, send/accept requests, block, form
  groups, invite members, and get one shared **group pick** per day.
- **Itineraries** — pick several vibes, get a nearest-neighbour ordered route,
  save it, and tick off stops in the tracker.
- **Tracker** — everything split into *to-do* vs *visited* across solo picks,
  group picks, and itineraries.
- **Community places** — suggest a place, upvote pending ones; auto-promotes at a
  vote threshold. Admins can approve / reject / delete.
- **Secret spots** — private personal finds, with optional AI-written descriptions.

---

## Environment variables

Everything is optional except `JWT_SECRET`. See [`.env.example`](.env.example)
for the full annotated list. Highlights:

| Variable | Default | Notes |
|---|---|---|
| `JWT_SECRET` | dev fallback | Set a real random string for anything real |
| `ADMIN_EMAILS` | `demo@onepick.app` | Comma-separated admin allowlist |
| `USE_ANTHROPIC` | `false` | Turn on Claude "why this pick" reasons |
| `DAILY_REROLL_LIMIT` | `3` | Rerolls per user per day |
| `PLACE_PROMOTION_VOTES` | `3` | Votes to promote a pending place |
| `CORS_ORIGINS` | `*` | Allowed origins for the API |

Frontend build points at the API via `web/.env` → `VITE_API_URL` (defaults to the
dev proxy). See [`web/.env.example`](web/.env.example).

---

## Deploy

- **Backend** — any host that runs `uvicorn backend.main:app` (Render, Fly, Railway).
  Set env vars in the dashboard; run `python -m backend.seed` once.
- **Frontend** — `npm run build` produces static files in `web/dist/` for Vercel,
  Netlify, or any static host. Set `VITE_API_URL` to the deployed backend URL.

---

## License

See [LICENSE](LICENSE).
