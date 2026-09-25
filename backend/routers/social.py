"""Friends and groups."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import (
    Friendship,
    Group,
    GroupInvite,
    GroupMember,
    Pick,
    Place,
    User,
)
from backend.schemas import (
    CreateGroupRequest,
    FriendOut,
    GroupInviteOut,
    GroupMemberDetail,
    GroupOut,
    GroupPickRequest,
    InviteCodeRequest,
    PickResponse,
)
from backend.services import recommend

router = APIRouter(tags=["social"])


def _pair(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


# --- Friends --------------------------------------------------------------


@router.post("/friends/request")
def send_friend_request(
    body: InviteCodeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    other = (
        db.query(User).filter(User.invite_code == body.invite_code.upper()).first()
    )
    if not other or other.id == user.id:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    a, b = _pair(user.id, other.id)
    if db.query(Friendship).filter_by(user_a_id=a, user_b_id=b).first():
        raise HTTPException(status_code=400, detail="Already requested or friends")

    db.add(
        Friendship(user_a_id=a, user_b_id=b, requester_id=user.id, status="pending")
    )
    db.commit()
    return {"detail": "Friend request sent"}


@router.post("/friends/accept", response_model=FriendOut)
def accept_friend_request(
    requester_id: int = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a, b = _pair(user.id, requester_id)
    friendship = (
        db.query(Friendship)
        .filter_by(user_a_id=a, user_b_id=b, status="pending")
        .first()
    )
    if not friendship:
        raise HTTPException(status_code=404, detail="No pending request found")
    if friendship.requester_id == user.id:
        raise HTTPException(status_code=403, detail="Cannot accept your own request")

    friendship.status = "accepted"
    db.commit()
    requester = db.query(User).filter(User.id == requester_id).first()
    return FriendOut(
        user_id=requester.id,
        display_name=requester.display_name or "",
        email=requester.email,
    )


@router.post("/friends/decline")
def decline_friend_request(
    requester_id: int = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a, b = _pair(user.id, requester_id)
    friendship = (
        db.query(Friendship)
        .filter_by(user_a_id=a, user_b_id=b, status="pending")
        .first()
    )
    if not friendship:
        raise HTTPException(status_code=404, detail="No pending request found")
    db.delete(friendship)
    db.commit()
    return {"detail": "Request declined"}


@router.get("/friends/pending", response_model=list[FriendOut])
def pending_requests(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pending = (
        db.query(Friendship)
        .filter(
            Friendship.status == "pending",
            Friendship.requester_id != user.id,
            (Friendship.user_a_id == user.id) | (Friendship.user_b_id == user.id),
        )
        .all()
    )
    ids = [f.requester_id for f in pending]
    users = db.query(User).filter(User.id.in_(ids)).all() if ids else []
    return [
        FriendOut(user_id=u.id, display_name=u.display_name or "", email=u.email)
        for u in users
    ]


@router.get("/friends", response_model=list[FriendOut])
def list_friends(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friendships = (
        db.query(Friendship)
        .filter(
            Friendship.status == "accepted",
            (Friendship.user_a_id == user.id) | (Friendship.user_b_id == user.id),
        )
        .all()
    )
    friend_ids = [
        f.user_b_id if f.user_a_id == user.id else f.user_a_id for f in friendships
    ]
    if not friend_ids:
        return []
    users = db.query(User).filter(User.id.in_(friend_ids)).all()
    return [
        FriendOut(user_id=u.id, display_name=u.display_name or "", email=u.email)
        for u in users
    ]


@router.get("/friends/blocked", response_model=list[FriendOut])
def blocked_users(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    blocked = (
        db.query(Friendship)
        .filter(
            Friendship.status == "blocked",
            Friendship.requester_id == user.id,
            (Friendship.user_a_id == user.id) | (Friendship.user_b_id == user.id),
        )
        .all()
    )
    ids = [
        f.user_b_id if f.user_a_id == user.id else f.user_a_id for f in blocked
    ]
    if not ids:
        return []
    users = db.query(User).filter(User.id.in_(ids)).all()
    return [
        FriendOut(user_id=u.id, display_name=u.display_name or "", email=u.email)
        for u in users
    ]


@router.get("/friends/{friend_id}/history")
def friend_history(
    friend_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a, b = _pair(user.id, friend_id)
    if (
        not db.query(Friendship)
        .filter_by(user_a_id=a, user_b_id=b, status="accepted")
        .first()
    ):
        raise HTTPException(status_code=403, detail="Not friends")

    picks = (
        db.query(Pick)
        .filter(Pick.user_id == friend_id)
        .order_by(Pick.created_at.desc())
        .limit(5)
        .all()
    )
    return [
        {
            "place_name": p.place_name,
            "category": p.category,
            "city": p.city,
            "created_at": p.created_at.strftime("%d %b %Y, %H:%M")
            if p.created_at
            else "Recent",
        }
        for p in picks
    ]


@router.delete("/friends/{friend_id}")
def remove_friend(
    friend_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a, b = _pair(user.id, friend_id)
    friendship = db.query(Friendship).filter_by(user_a_id=a, user_b_id=b).first()
    if not friendship:
        raise HTTPException(status_code=404, detail="Friendship not found")
    db.delete(friendship)
    db.commit()
    return {"detail": "Friend removed"}


@router.post("/friends/{friend_id}/block")
def block_friend(
    friend_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a, b = _pair(user.id, friend_id)
    friendship = db.query(Friendship).filter_by(user_a_id=a, user_b_id=b).first()
    if not friendship:
        friendship = Friendship(user_a_id=a, user_b_id=b)
        db.add(friendship)
    friendship.status = "blocked"
    friendship.requester_id = user.id
    db.commit()
    return {"detail": "User blocked"}


@router.post("/friends/{friend_id}/unblock")
def unblock_user(
    friend_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a, b = _pair(user.id, friend_id)
    friendship = (
        db.query(Friendship)
        .filter_by(user_a_id=a, user_b_id=b, status="blocked")
        .first()
    )
    if not friendship:
        raise HTTPException(status_code=404, detail="User is not blocked")
    db.delete(friendship)
    db.commit()
    return {"detail": "User unblocked"}


# --- Groups ---------------------------------------------------------------


def _group_out(db: Session, g: Group) -> GroupOut:
    member_ids = [m.user_id for m in g.members]
    users = db.query(User).filter(User.id.in_(member_ids)).all() if member_ids else []
    members = [
        GroupMemberDetail(
            user_id=u.id, display_name=u.display_name or "", invite_code=u.invite_code
        )
        for u in users
    ]
    return GroupOut(
        group_id=g.id,
        name=g.name,
        owner_id=g.owner_id,
        member_ids=member_ids,
        members=members,
    )


@router.post("/groups", response_model=GroupOut)
def create_group(
    body: CreateGroupRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    g = Group(name=body.name, owner_id=user.id)
    db.add(g)
    db.flush()
    for uid in {user.id, *body.member_ids}:
        db.add(GroupMember(group_id=g.id, user_id=uid))
    db.commit()
    db.refresh(g)
    return _group_out(db, g)


@router.get("/groups", response_model=list[GroupOut])
def list_groups(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(GroupMember).filter(GroupMember.user_id == user.id).all()
    return [_group_out(db, r.group) for r in rows if r.group]


@router.post("/groups/{group_id}/pick", response_model=PickResponse)
def group_pick(
    group_id: int,
    body: GroupPickRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id, GroupMember.user_id == user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this group")

    # One shared pick per group per day: if one exists, everyone sees the same.
    today = datetime.combine(date.today(), datetime.min.time())
    existing = (
        db.query(Pick)
        .filter(Pick.group_id == group_id, Pick.created_at >= today)
        .order_by(Pick.created_at.desc())
        .first()
    )
    if existing:
        place = db.query(Place).filter(Place.id == int(existing.place_id)).first()
        return PickResponse(
            pick_id=existing.id,
            place_id=str(existing.place_id),
            name=existing.place_name,
            address=place.address if place else "",
            lat=place.lat if place else 47.1585,
            lon=place.lon if place else 27.6014,
            category=existing.category,
            city=existing.city,
            why=existing.why or "Today's group pick.",
            rating=float(place.vote_count) if place else 0.0,
            photo_url=place.photo_url if place else None,
            hours=place.hours if place else None,
            visited=existing.visited_at is not None,
        )

    place = recommend.choose_place(db, user.id, body.category, body.city)
    if not place:
        raise HTTPException(
            status_code=404,
            detail=f"No place found for {body.category} in {body.city}.",
        )
    pick = Pick(
        user_id=user.id,
        group_id=group_id,
        place_id=str(place.id),
        place_name=place.name,
        category=body.category,
        city=body.city,
        why=place.description or f"A great {body.category} for the group.",
    )
    db.add(pick)
    db.commit()
    db.refresh(pick)
    return PickResponse(
        pick_id=pick.id,
        place_id=str(place.id),
        name=place.name,
        address=place.address or "",
        lat=place.lat,
        lon=place.lon,
        category=place.category,
        city=place.city,
        why=pick.why,
        rating=float(place.vote_count or 0),
        photo_url=place.photo_url,
        hours=place.hours,
        visited=False,
    )


@router.post("/groups/{group_id}/invite")
def invite_to_group(
    group_id: int,
    user_id: int = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if db.query(GroupMember).filter_by(group_id=group_id, user_id=user_id).first():
        raise HTTPException(status_code=400, detail="Already in the group")
    if (
        db.query(GroupInvite)
        .filter_by(group_id=group_id, receiver_id=user_id, status="pending")
        .first()
    ):
        raise HTTPException(status_code=400, detail="Invite already sent")
    db.add(GroupInvite(group_id=group_id, sender_id=user.id, receiver_id=user_id))
    db.commit()
    return {"detail": "Invite sent"}


@router.get("/groups/invites/pending", response_model=list[GroupInviteOut])
def pending_group_invites(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invites = (
        db.query(GroupInvite)
        .filter_by(receiver_id=user.id, status="pending")
        .all()
    )
    out = []
    for inv in invites:
        sender = db.query(User).filter_by(id=inv.sender_id).first()
        group = db.query(Group).filter_by(id=inv.group_id).first()
        if sender and group:
            out.append(
                GroupInviteOut(
                    invite_id=inv.id,
                    group_id=group.id,
                    group_name=group.name,
                    sender_name=sender.display_name or "A friend",
                )
            )
    return out


@router.post("/groups/invites/{invite_id}/accept")
def accept_group_invite(
    invite_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    inv = (
        db.query(GroupInvite)
        .filter_by(id=invite_id, receiver_id=user.id, status="pending")
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Invite not found")
    inv.status = "accepted"
    if not db.query(GroupMember).filter_by(group_id=inv.group_id, user_id=user.id).first():
        db.add(GroupMember(group_id=inv.group_id, user_id=user.id))
    db.commit()
    return {"detail": "Joined group"}


@router.post("/groups/invites/{invite_id}/decline")
def decline_group_invite(
    invite_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    inv = (
        db.query(GroupInvite)
        .filter_by(id=invite_id, receiver_id=user.id, status="pending")
        .first()
    )
    if inv:
        inv.status = "declined"
        db.commit()
    return {"detail": "Invite declined"}


@router.delete("/groups/{group_id}")
def delete_group(
    group_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    g = db.query(Group).filter_by(id=group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    if g.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the owner can delete")
    db.query(GroupMember).filter_by(group_id=group_id).delete()
    db.query(GroupInvite).filter_by(group_id=group_id).delete()
    db.delete(g)
    db.commit()
    return {"detail": "Group deleted"}


@router.delete("/groups/{group_id}/members/{user_id}")
def kick_member(
    group_id: int,
    user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    g = db.query(Group).filter_by(id=group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    if g.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the owner can remove members")
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Delete the group instead")
    membership = db.query(GroupMember).filter_by(group_id=group_id, user_id=user_id).first()
    if membership:
        db.delete(membership)
        db.commit()
    return {"detail": "Member removed"}
