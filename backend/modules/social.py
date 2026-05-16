"""
Friends + groups.

Owner: Role 3.

Endpoints:
    GET  /friends                       -> list of accepted friends
    POST /friends/accept                -> accept by invite_code
    POST /groups                        -> create a group
    GET  /groups                        -> list groups I'm in
    POST /groups/{id}/pick              -> one rec for the whole group
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import User, Friendship, Group, GroupMember, get_db
from backend.modules import places as places_module

router = APIRouter(tags=["social"])


# ----- Schemas --------------------------------------------------------------

class AcceptInviteRequest(BaseModel):
    invite_code: str


class FriendOut(BaseModel):
    user_id: int
    display_name: str
    email: str


class CreateGroupRequest(BaseModel):
    name: str
    member_ids: List[int] = []


class GroupOut(BaseModel):
    group_id: int
    name: str
    member_ids: List[int]


class GroupPickRequest(BaseModel):
    category: str
    city: str


# ----- Friends --------------------------------------------------------------

@router.get("/friends", response_model=List[FriendOut])
def list_friends(user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    rows = db.query(Friendship).filter(
        ((Friendship.user_a_id == user.id) | (Friendship.user_b_id == user.id)),
        Friendship.status == "accepted",
    ).all()
    friend_ids = [
        r.user_b_id if r.user_a_id == user.id else r.user_a_id for r in rows
    ]
    friends = db.query(User).filter(User.id.in_(friend_ids)).all() if friend_ids else []
    return [FriendOut(user_id=f.id, display_name=f.display_name or "",
                      email=f.email) for f in friends]


@router.post("/friends/accept", response_model=FriendOut)
def accept_invite(body: AcceptInviteRequest,
                  user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    other = db.query(User).filter(User.invite_code == body.invite_code.upper()).first()
    if not other or other.id == user.id:
        raise HTTPException(status_code=404, detail="Invalid invite code")
    a, b = sorted([user.id, other.id])
    existing = db.query(Friendship).filter(
        Friendship.user_a_id == a, Friendship.user_b_id == b
    ).first()
    if not existing:
        db.add(Friendship(user_a_id=a, user_b_id=b, status="accepted"))
        db.commit()
    return FriendOut(user_id=other.id, display_name=other.display_name or "",
                     email=other.email)


# ----- Groups ---------------------------------------------------------------

@router.post("/groups", response_model=GroupOut)
def create_group(body: CreateGroupRequest,
                 user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    g = Group(name=body.name, owner_id=user.id)
    db.add(g)
    db.flush()
    member_ids = list({user.id, *body.member_ids})
    for uid in member_ids:
        db.add(GroupMember(group_id=g.id, user_id=uid))
    db.commit()
    return GroupOut(group_id=g.id, name=g.name, member_ids=member_ids)


@router.get("/groups", response_model=List[GroupOut])
def list_groups(user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    rows = db.query(GroupMember).filter(GroupMember.user_id == user.id).all()
    out = []
    for r in rows:
        g = r.group
        if not g:
            continue
        member_ids = [m.user_id for m in g.members]
        out.append(GroupOut(group_id=g.id, name=g.name, member_ids=member_ids))
    return out


@router.post("/groups/{group_id}/pick")
def group_pick(group_id: int, body: GroupPickRequest,
               user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    membership = db.query(GroupMember).filter(
        GroupMember.group_id == group_id, GroupMember.user_id == user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this group")

    # Delegate to the places module so we don't duplicate scoring logic
    req = places_module.PickRequest(category=body.category, city=body.city,
                                    group_id=group_id)
    return places_module.pick(req, user=user, db=db)
