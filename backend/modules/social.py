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

from datetime import date, datetime
from typing import List, Optional
from backend.db import Pick

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import User, Friendship, Group, GroupMember, get_db, Place, Pick, GroupInvite
from backend.modules import places as places_module
import random

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

class GroupMemberDetail(BaseModel):
    user_id: int
    display_name: str
    invite_code: str

class GroupOut(BaseModel):
    group_id: int
    name: str
    owner_id: int
    member_ids: List[int]
    members: List[GroupMemberDetail] = []

class GroupPickRequest(BaseModel):
    category: str
    city: str
    
class GroupInviteOut(BaseModel):
    invite_id: int
    group_id: int
    group_name: str
    sender_name: str


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
@router.get("/friends", response_model=List[FriendOut])
def list_friends(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Listează toți prietenii cu care utilizatorul are o relație acceptată."""
    accepted_friendships = db.query(Friendship).filter(
        Friendship.status == "accepted",
        ((Friendship.user_a_id == user.id) | (Friendship.user_b_id == user.id))
    ).all()

    friend_ids = []
    for f in accepted_friendships:
        if f.user_a_id == user.id:
            friend_ids.append(f.user_b_id)
        else:
            friend_ids.append(f.user_a_id)

    if not friend_ids:
        return []

    friends_users = db.query(User).filter(User.id.in_(friend_ids)).all()
    return [
        FriendOut(user_id=u.id, display_name=u.display_name or "", email=u.email)
        for u in friends_users
    ]


@router.get("/friends/{friend_id}/history")
def get_friend_history(friend_id: int, 
                       user: User = Depends(get_current_user), 
                       db: Session = Depends(get_db)):
    """Întoarce istoricul de locații al unui prieten, dacă cei doi sunt prieteni."""
    a, b = sorted([user.id, friend_id])
    is_friend = db.query(Friendship).filter_by(user_a_id=a, user_b_id=b, status="accepted").first()
    if not is_friend:
        raise HTTPException(status_code=403, detail="Nu poți vedea istoricul cuiva care nu îți este prieten.")

    picks = db.query(Pick).filter(Pick.user_id == friend_id).order_by(Pick.created_at.desc()).limit(5).all()

    return [
        {
            "place_name": p.place_name,
            "category": p.category,
            "city": p.city,
            "created_at": p.created_at.strftime("%d %b %Y, %H:%M") if p.created_at else "Recent"
        }
        for p in picks
    ]

@router.delete("/friends/{friend_id}")
def remove_friend(friend_id: int, 
                  user: User = Depends(get_current_user), 
                  db: Session = Depends(get_db)):
    """Șterge o relație de prietenie existentă."""
    a, b = sorted([user.id, friend_id])
    friendship = db.query(Friendship).filter_by(user_a_id=a, user_b_id=b).first()
    
    if not friendship:
        raise HTTPException(status_code=404, detail="Prietenia nu a fost găsită.")
        
    db.delete(friendship)
    db.commit()
    return {"detail": "Friend removed successfully"}

@router.post("/friends/{friend_id}/block")
def block_friend(friend_id: int, 
                 user: User = Depends(get_current_user), 
                 db: Session = Depends(get_db)):
    """Schimbă statusul relației în 'blocked' și salvează cine a dat block."""
    a, b = sorted([user.id, friend_id])
    friendship = db.query(Friendship).filter_by(user_a_id=a, user_b_id=b).first()
    
    if not friendship:
        friendship = Friendship(user_a_id=a, user_b_id=b)
        db.add(friendship)
        
    friendship.status = "blocked"
    friendship.requester_id = user.id  
    db.commit()
    return {"detail": "User blocked successfully"}
@router.get("/friends/blocked", response_model=List[FriendOut])
def list_blocked_users(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Aduce lista utilizatorilor pe care EU i-am blocat."""
    blocked_friendships = db.query(Friendship).filter(
        Friendship.status == "blocked",
        Friendship.requester_id == user.id, # Verificăm ca eu să fiu cel care a inițiat blocarea
        ((Friendship.user_a_id == user.id) | (Friendship.user_b_id == user.id))
    ).all()
    
    blocked_ids = []
    for f in blocked_friendships:
        blocked_ids.append(f.user_b_id if f.user_a_id == user.id else f.user_a_id)
        
    if not blocked_ids:
        return []
        
    blocked_users_list = db.query(User).filter(User.id.in_(blocked_ids)).all()
    return [FriendOut(user_id=u.id, display_name=u.display_name or "Anonim", email=u.email) for u in blocked_users_list]


@router.post("/friends/{friend_id}/unblock")
def unblock_user(friend_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Șterge blocajul pentru un utilizator."""
    a, b = sorted([user.id, friend_id])
    friendship = db.query(Friendship).filter_by(user_a_id=a, user_b_id=b, status="blocked").first()
    
    if not friendship:
        raise HTTPException(status_code=404, detail="Utilizatorul nu este blocat.")
    
    # Prin ștergerea rândului, cei doi devin iar străini și își pot trimite friend requests
    db.delete(friendship)
    db.commit()
    return {"detail": "User unblocked successfully"}

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
    
    users = db.query(User).filter(User.id.in_(member_ids)).all()
    members_detail = [GroupMemberDetail(user_id=u.id, display_name=u.display_name or "Anonim", invite_code=u.invite_code) for u in users]
    return GroupOut(group_id=g.id, name=g.name, owner_id=g.owner_id, member_ids=member_ids, members=members_detail)


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
        users = db.query(User).filter(User.id.in_(member_ids)).all()
        members_detail = [GroupMemberDetail(user_id=u.id, display_name=u.display_name or "Anonim", invite_code=u.invite_code) for u in users]
        out.append(GroupOut(group_id=g.id, name=g.name, owner_id=g.owner_id, member_ids=member_ids, members=members_detail))       
        return out
import random  # asigură-te că ai 'import random' sus în social.py dacă nu e deja

@router.post("/groups/{group_id}/pick")
def group_pick(group_id: int, 
               body: GroupPickRequest, 
               user: User = Depends(get_current_user), 
               db: Session = Depends(get_db)):
    # 1. Verificăm dacă user-ul chiar face parte din acest grup
    membership = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user.id).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this group")

    # 2. Hack-ul de sincro (funcțional): dacă s-a ales deja azi ceva pentru grup, dăm aceeași variantă
    today_start = datetime.combine(date.today(), datetime.min.time())
    existing_pick = db.query(Pick).filter(Pick.group_id == group_id, Pick.created_at >= today_start).order_by(Pick.created_at.desc()).first()

    if existing_pick:
        # Căutăm locația originală din DB ca să trimitem coordonatele și adresa ei reale
        locatie_salvata = db.query(Place).filter(Place.id == existing_pick.place_id).first()
        return places_module.PickResponse(
            pick_id=existing_pick.id,
            place_id=str(existing_pick.place_id),
            name=existing_pick.place_name,
            why=existing_pick.why or "Alegerea grupului de astăzi!",
            lat=locatie_salvata.lat if locatie_salvata else 47.1585,
            lon=locatie_salvata.lon if locatie_salvata else 27.6014,
            address=locatie_salvata.address if locatie_salvata else "Iași",
            rating=4.5
        )

    # 3. LOGICA NOUĂ: Căutăm STRICT în tabelul local 'Place' (doar ce ați adăugat voi în DB)
    places = db.query(Place).filter(
        Place.category == body.category,
        Place.city == body.city,
        Place.status.in_(("admin", "approved")) # ia doar locațiile valide
    ).all()

    # Fallback dacă nu găsește fix în acel oraș, caută doar după categorie
    if not places:
        places = db.query(Place).filter(Place.category == body.category, Place.status.in_(("admin", "approved"))).all()

    # Dacă tabelul vostru nu are nimic pe această categorie, dăm eroare curată
    if not places:
        raise HTTPException(status_code=404, detail=f"Nu există nicio locație în baza de date pentru categoria '{body.category}' în {body.city}.")

    # 4. Extragem aleatoriu o locație introdusă de voi
    chosen_place = random.choice(places)
    descriere_locatie = chosen_place.description or f"O locație excelentă de tip {body.category} din {body.city}."

    # 5. Salvăm alegerea în tabelul de istorice 'Pick' (fără să adăugăm nimic în tabelul de locații!)
    p = Pick(
        user_id=user.id,
        group_id=group_id,
        place_id=str(chosen_place.id),
        place_name=chosen_place.name,
        category=body.category,
        city=body.city,
        why=descriere_locatie,
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    # 6. Returnăm răspunsul perfect formatat pentru Frontend
    return places_module.PickResponse(
        pick_id=p.id,
        place_id=str(chosen_place.id),
        name=chosen_place.name,
        address=chosen_place.address or "",
        lat=chosen_place.lat,
        lon=chosen_place.lon,
        why=descriere_locatie,
        rating=getattr(chosen_place, "vote_count", 0.0), # folosim voturile pe post de rating local
        photo_url=chosen_place.photo_url,
        hours=chosen_place.hours
    )
    
@router.post("/groups/{group_id}/invite")
def invite_to_group(group_id: int, user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Trimite o invitație unui prieten pentru a intra în grup."""
    # Verifică dacă prietenul e deja în grup
    existing_member = db.query(GroupMember).filter_by(group_id=group_id, user_id=user_id).first()
    if existing_member:
        raise HTTPException(400, "Utilizatorul este deja în grup.")
        
    # Verifică dacă are deja o invitație pending
    existing_invite = db.query(GroupInvite).filter_by(group_id=group_id, receiver_id=user_id, status="pending").first()
    if existing_invite:
        raise HTTPException(400, "I-ai trimis deja o invitație.")
        
    invite = GroupInvite(group_id=group_id, sender_id=user.id, receiver_id=user_id)
    db.add(invite)
    db.commit()
    return {"detail": "Invite sent"}

@router.get("/groups/invites/pending", response_model=List[GroupInviteOut])
def get_group_invites(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Aduce toate invitațiile de grup pe care le-am primit."""
    invites = db.query(GroupInvite).filter_by(receiver_id=user.id, status="pending").all()
    out = []
    for inv in invites:
        sender = db.query(User).filter_by(id=inv.sender_id).first()
        group = db.query(Group).filter_by(id=inv.group_id).first()
        if sender and group:
            out.append(GroupInviteOut(
                invite_id=inv.id, group_id=group.id,
                group_name=group.name, sender_name=sender.display_name or "Un prieten"
            ))
    return out

@router.post("/groups/invites/{invite_id}/accept")
def accept_group_invite(invite_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    inv = db.query(GroupInvite).filter_by(id=invite_id, receiver_id=user.id, status="pending").first()
    if not inv:
        raise HTTPException(404, "Invitația nu există.")
        
    inv.status = "accepted"
    # Îl adăugăm oficial în grup
    if not db.query(GroupMember).filter_by(group_id=inv.group_id, user_id=user.id).first():
        db.add(GroupMember(group_id=inv.group_id, user_id=user.id))
    db.commit()
    return {"detail": "Joined group"}

@router.post("/groups/invites/{invite_id}/decline")
def decline_group_invite(invite_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    inv = db.query(GroupInvite).filter_by(id=invite_id, receiver_id=user.id, status="pending").first()
    if inv:
        inv.status = "declined"
        db.commit()
    return {"detail": "Invite declined"}

@router.delete("/groups/{group_id}")
def delete_group(group_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Șterge grupul (doar adminul poate face asta)."""
    g = db.query(Group).filter_by(id=group_id).first()
    if not g:
        raise HTTPException(404, "Grupul nu a fost găsit.")
    if g.owner_id != user.id:
        raise HTTPException(403, "Doar adminul poate șterge grupul!")
    
    # Ștergem membrii și invitațiile ca să nu crape baza de date
    db.query(GroupMember).filter_by(group_id=group_id).delete()
    db.query(GroupInvite).filter_by(group_id=group_id).delete()
    db.delete(g)
    db.commit()
    return {"detail": "Group deleted"}

@router.delete("/groups/{group_id}/members/{user_id}")
def kick_member(group_id: int, user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Dă afară un membru din grup (doar adminul/owner-ul grupului poate)."""
    g = db.query(Group).filter_by(id=group_id).first()
    if not g:
        raise HTTPException(404, "Grupul nu a fost găsit.")
    if g.owner_id != user.id:
        raise HTTPException(403, "Doar adminul poate da afară membri!")
    if user_id == user.id:
        raise HTTPException(400, "Nu te poți da afară singur. Șterge grupul în schimb.")
        
    membership = db.query(GroupMember).filter_by(group_id=group_id, user_id=user_id).first()
    if membership:
        db.delete(membership)
        db.commit()
    return {"detail": "Member kicked"}