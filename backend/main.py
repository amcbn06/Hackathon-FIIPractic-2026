"""
South API — one recommendation, not fifty.

Run locally:
    uvicorn backend.main:app --reload --port 8000

Interactive docs at http://localhost:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db
from backend.routers import (
    auth,
    gamification,
    itinerary,
    places,
    social,
    spots,
)

app = FastAPI(
    title="South API",
    description="One recommendation, not fifty.",
    version="1.0.0",
)

# Make sure tables exist for the seed script, tests, and `--reload`.
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"service": "South API", "status": "ok", "version": app.version}


@app.get("/health")
def health():
    return {"status": "healthy"}


for r in (auth, places, social, gamification, itinerary, spots):
    app.include_router(r.router)
