from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime

# Importăm baza de date și funcțiile de autentificare din proiectul tău
from backend.db import get_db, User, CustomLocation
from backend.auth import get_current_user

# Creăm un router dedicat doar pentru acest feature
router = APIRouter(prefix="/custom_locations", tags=["Custom Locations"])

class CustomLocationRequest(BaseModel):
    name: str
    description: str
    interval: str
    rating: int

@router.post("/add")
def add_custom_location(data: CustomLocationRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_loc = CustomLocation(
        user_id=user.id,
        name=data.name,
        description=data.description,
        interval=data.interval,
        rating=data.rating
    )
    db.add(new_loc)
    db.commit()
    return {"detail": "Custom location added"}

@router.get("/me")
def get_my_custom_locations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    locs = db.query(CustomLocation).filter(CustomLocation.user_id == user.id).order_by(CustomLocation.created_at.desc()).all()
    return [
        {
            "id": l.id, 
            "name": l.name, 
            "description": l.description, 
            "interval": l.interval, 
            "rating": l.rating,
            "created_at": l.created_at.strftime("%d %b %Y") if l.created_at else "Recent"
        } 
        for l in locs
    ]