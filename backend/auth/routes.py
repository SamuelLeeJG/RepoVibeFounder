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
from backend.db.models import AccessRequest, AllowedInvite, PasswordResetToken, User

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


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str  # UUID string
    new_password: str


class AccessRequestCreate(BaseModel):
    email: str
    display_name: str
    reason: str = ""


class AccessRequestReview(BaseModel):
    request_id: str  # UUID string
    action: str  # "approve" or "deny"


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    role: str | None = None


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


# ── Password Reset ──


@auth_router.post("/password-reset/request")
async def request_password_reset(req: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """Request a password reset token (sent to email in production)."""
    result = await db.execute(select(User).where(User.email == req.email.lower()))
    user = result.scalar_one_or_none()
    if user is None:
        # Don't reveal whether email exists
        return {"message": "If this email is registered, a reset link has been sent."}

    # Create reset token (expires in 1 hour)
    reset = PasswordResetToken(
        user_id=user.id,
        expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1),
    )
    db.add(reset)
    await db.flush()

    # In production: send email with reset link containing reset.token
    return {
        "message": "If this email is registered, a reset link has been sent.",
        "reset_token": str(reset.token),  # Only exposed in dev/sandbox
    }


@auth_router.post("/password-reset/confirm")
async def confirm_password_reset(req: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    """Reset password using a valid reset token."""
    try:
        token_uuid = uuid.UUID(req.token)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid token format")

    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token == token_uuid,
            PasswordResetToken.used == False,
        )
    )
    reset = result.scalar_one_or_none()
    if reset is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if reset.expires_at < dt.datetime.now(dt.timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired")

    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Update user password
    user_result = await db.execute(select(User).where(User.id == reset.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=400, detail="User not found")

    user.hashed_password = pwd_context.hash(req.new_password)
    reset.used = True
    await db.flush()

    return {"message": "Password reset successfully"}


# ── Request Access (non-invite flow) ──


@auth_router.post("/request-access")
async def request_access(req: AccessRequestCreate, db: AsyncSession = Depends(get_db)):
    """Request access to the platform (non-invite flow — requires admin approval)."""
    # Check if already registered
    existing = await db.execute(select(User).where(User.email == req.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Check if already requested
    existing_req = await db.execute(
        select(AccessRequest).where(
            AccessRequest.email == req.email.lower(),
            AccessRequest.status == "pending",
        )
    )
    if existing_req.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Access request already pending")

    access_req = AccessRequest(
        email=req.email.lower(),
        display_name=req.display_name,
        reason=req.reason,
    )
    db.add(access_req)
    await db.flush()

    return {"message": "Access request submitted. You will be notified when approved.", "request_id": str(access_req.id)}


# ── Admin: Manage Access Requests ──


@auth_router.get("/admin/access-requests")
async def list_access_requests(
    status_filter: str = "pending",
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: list access requests."""
    query = select(AccessRequest).order_by(AccessRequest.created_at.desc())
    if status_filter != "all":
        query = query.where(AccessRequest.status == status_filter)
    result = await db.execute(query)
    requests = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "email": r.email,
            "display_name": r.display_name,
            "reason": r.reason,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in requests
    ]


@auth_router.post("/admin/access-requests/review")
async def review_access_request(
    req: AccessRequestReview,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: approve or deny an access request."""
    try:
        req_id = uuid.UUID(req.request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request ID")

    result = await db.execute(select(AccessRequest).where(AccessRequest.id == req_id))
    access_req = result.scalar_one_or_none()
    if access_req is None:
        raise HTTPException(status_code=404, detail="Access request not found")

    if access_req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request already {access_req.status}")

    if req.action == "approve":
        access_req.status = "approved"
        access_req.reviewed_by = admin.id
        access_req.reviewed_at = dt.datetime.now(dt.timezone.utc)
        # Create an invite for the approved user
        invite = AllowedInvite(email=access_req.email, invited_by=admin.id)
        db.add(invite)
        await db.flush()
        return {
            "message": f"Approved. Invite code generated for {access_req.email}",
            "invite_code": str(invite.invite_code),
        }
    elif req.action == "deny":
        access_req.status = "denied"
        access_req.reviewed_by = admin.id
        access_req.reviewed_at = dt.datetime.now(dt.timezone.utc)
        await db.flush()
        return {"message": f"Denied access for {access_req.email}"}
    else:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'deny'")


# ── Admin: User Management ──


@auth_router.get("/admin/users")
async def list_users(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """Admin-only: list all users."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "display_name": u.display_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@auth_router.put("/admin/users/{user_id}")
async def update_user(
    user_id: str,
    req: AdminUserUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: update a user's status or role."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if req.is_active is not None:
        user.is_active = req.is_active
    if req.role is not None and req.role in ("admin", "member"):
        user.role = req.role

    await db.flush()
    return {"message": f"Updated user {user.email}", "is_active": user.is_active, "role": user.role}
