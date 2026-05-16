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

# Rename and repurpose this endpoint
@router.post("/friends/request")
def send_friend_request(
    body: AcceptInviteRequest,  # reuse schema, or rename it to InviteCodeRequest
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    other = db.query(User).filter(User.invite_code == body.invite_code.upper()).first()
    if not other or other.id == user.id:
        raise HTTPException(404, "Invalid invite code")

    a, b = sorted([user.id, other.id])
    existing = db.query(Friendship).filter_by(user_a_id=a, user_b_id=b).first()
    if existing:
        raise HTTPException(400, "Request already sent or already friends")

    db.add(Friendship(user_a_id=a, user_b_id=b,
                      requester_id=user.id, status="pending"))
    db.commit()
    return {"detail": "Friend request sent"}

@router.post("/friends/accept")
def accept_friend_request(
    requester_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a, b = sorted([user.id, requester_id])
    friendship = db.query(Friendship).filter_by(
        user_a_id=a, user_b_id=b, status="pending"
    ).first()
    if not friendship:
        raise HTTPException(404, "No pending request found")
    if friendship.requester_id == user.id:
        raise HTTPException(403, "Cannot accept your own request")

    friendship.status = "accepted"
    db.commit()
    requester = db.query(User).filter(User.id == requester_id).first()
    return FriendOut(user_id=requester.id,
                     display_name=requester.display_name or "",
                     email=requester.email)


@router.post("/friends/decline")
def decline_friend_request(
    requester_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a, b = sorted([user.id, requester_id])
    friendship = db.query(Friendship).filter_by(
        user_a_id=a, user_b_id=b, status="pending"
    ).first()
    if not friendship:
        raise HTTPException(404, "No pending request found")
    if friendship.requester_id == user.id:
        raise HTTPException(403, "Cannot decline your own request")

    db.delete(friendship)
    db.commit()
    return {"detail": "Request declined"}


@router.get("/friends/pending", response_model=List[FriendOut])
def list_pending_requests(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pending = db.query(Friendship).filter(
        Friendship.status == "pending",
        # only show requests where current user is the recipient
        Friendship.requester_id != user.id,
        ((Friendship.user_a_id == user.id) | (Friendship.user_b_id == user.id)),
    ).all()
    requester_ids = [f.requester_id for f in pending]
    requesters = db.query(User).filter(User.id.in_(requester_ids)).all() if requester_ids else []
    return [FriendOut(user_id=r.id, display_name=r.display_name or "",
                      email=r.email) for r in requesters]


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
