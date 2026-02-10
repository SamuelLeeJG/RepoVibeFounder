"""Auth routes — invite-only registration, login, refresh, admin invite management."""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from backend.auth.jwt import JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth_dependencies import get_current_user, require_admin
from backend.auth.jwt import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from backend.db.database import get_db
from backend.db.models import AllowedInvite, User

auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Request / Response models ──


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str
    invite_code: str  # UUID string


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    role: str


class InviteRequest(BaseModel):
    email: str


class InviteResponse(BaseModel):
    invite_code: str
    email: str


class UserProfile(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    pinned_tickers: list[str]
    created_at: str


class PinnedTickersRequest(BaseModel):
    tickers: list[str]  # max 7


# ── Routes ──


@auth_router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register with a valid one-time invite code."""
    try:
        code_uuid = uuid.UUID(req.invite_code)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid invite code format")

    result = await db.execute(
        select(AllowedInvite).where(AllowedInvite.invite_code == code_uuid, AllowedInvite.used == False)
    )
    invite = result.scalar_one_or_none()
    if invite is None:
        raise HTTPException(status_code=403, detail="Invalid or already-used invite code")

    if invite.email.lower() != req.email.lower():
        raise HTTPException(status_code=403, detail="Invite code does not match this email")

    # Check if email already registered
    existing = await db.execute(select(User).where(User.email == req.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create user
    user = User(
        email=req.email.lower(),
        hashed_password=pwd_context.hash(req.password),
        display_name=req.display_name,
        role="member",
    )
    db.add(user)

    # Mark invite as used
    invite.used = True
    invite.used_at = dt.datetime.now(dt.timezone.utc)

    await db.flush()

    access = create_access_token(user.id, extra={"role": user.role})
    refresh = create_refresh_token(user.id)
    return TokenResponse(access_token=access, refresh_token=refresh, user_id=str(user.id), role=user.role)


@auth_router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email + password."""
    result = await db.execute(select(User).where(User.email == req.email.lower()))
    user = result.scalar_one_or_none()
    if user is None or not pwd_context.verify(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    access = create_access_token(user.id, extra={"role": user.role})
    refresh = create_refresh_token(user.id)
    return TokenResponse(access_token=access, refresh_token=refresh, user_id=str(user.id), role=user.role)


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a refresh token for a new access + refresh token pair."""
    try:
        user_id_str = verify_refresh_token(req.refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id_str)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or deactivated")

    access = create_access_token(user.id, extra={"role": user.role})
    refresh = create_refresh_token(user.id)
    return TokenResponse(access_token=access, refresh_token=refresh, user_id=str(user.id), role=user.role)


@auth_router.get("/me", response_model=UserProfile)
async def get_me(user: User = Depends(get_current_user)):
    """Get the current user's profile."""
    return UserProfile(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        pinned_tickers=user.pinned_tickers or [],
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


@auth_router.put("/me/pinned-tickers")
async def update_pinned_tickers(
    req: PinnedTickersRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user's pinned tickers (max 7)."""
    if len(req.tickers) > 7:
        raise HTTPException(status_code=400, detail="Maximum 7 pinned tickers allowed")
    user.pinned_tickers = [t.upper() for t in req.tickers]
    await db.flush()
    return {"pinned_tickers": user.pinned_tickers}


# ── Admin routes ──


@auth_router.post("/admin/invite", response_model=InviteResponse)
async def create_invite(
    req: InviteRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: create a one-time invite for an email."""
    invite = AllowedInvite(email=req.email.lower(), invited_by=admin.id)
    db.add(invite)
    await db.flush()
    return InviteResponse(invite_code=str(invite.invite_code), email=invite.email)


@auth_router.get("/admin/invites")
async def list_invites(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """Admin-only: list all invites."""
    result = await db.execute(select(AllowedInvite).order_by(AllowedInvite.created_at.desc()))
    invites = result.scalars().all()
    return [
        {
            "id": str(inv.id),
            "email": inv.email,
            "invite_code": str(inv.invite_code),
            "used": inv.used,
            "used_at": inv.used_at.isoformat() if inv.used_at else None,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        }
        for inv in invites
    ]
