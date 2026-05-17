"""
FastAPI entry point.

Run locally:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

Auto-generated docs at: http://localhost:8000/docs
"""

from dotenv import load_dotenv
load_dotenv()   # must run before importing modules that read env vars

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import init_db
from backend import auth
from backend.modules import places, social, gamification,custom_spots, ai_service

app = FastAPI(
    title="OnePick API",
    description="One recommendation, not fifty.",
    version="0.1.0",
)

# Ensure tables exist at import time so the seed script, TestClient, and
# `uvicorn --reload` all see a ready schema without relying on startup events.
init_db()

# CORS — wide open for hackathon; tighten before any real deploy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"service": "OnePick API", "status": "ok"}


# Mount routers (each role owns one)
app.include_router(auth.router)
app.include_router(places.router)
app.include_router(social.router)
app.include_router(gamification.router)
app.include_router(custom_spots.router)
app.include_router(ai_service.router)