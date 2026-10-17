from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
from app.core.config import settings
from app.core.auth import (
    AuthenticatedUser,
    create_access_token,
    get_current_user
)
from app.services.database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

class TokenRequest(BaseModel):
    role: str = Field(default="citizen", description="Role to assume: citizen, coordinator, or responder")
    uid: Optional[str] = Field(default=None, description="User UID or persona identifier")
    name: Optional[str] = Field(default=None, description="Display name")
    email: Optional[str] = Field(default=None, description="User email")
    pin: Optional[str] = Field(default=None, description="Authorization PIN for privileged roles in production")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    uid: str
    name: str
    email: Optional[str] = None
    is_demo_auth: bool
    expires_in: int = 86400

@router.post("/token", response_model=TokenResponse)
async def request_token(payload: TokenRequest):
    """
    Issues a cryptographically signed HMAC-SHA256 JWT access token.

    SECURITY POLICY:
    - 'citizen' tokens can be issued to any resident or evaluator.
    - 'coordinator' and 'responder' tokens require either:
      1. DEMO_MODE enabled on the backend (flagged in token as is_demo_auth=true).
      2. Valid authorization PIN provided in production mode.
    """
    target_role = payload.role.lower().strip()
    if target_role not in ["citizen", "coordinator", "responder"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role requested: '{payload.role}'. Must be citizen, coordinator, or responder."
        )

    is_demo_auth = False

    # Enforce strict authorization for privileged roles
    if target_role in ["coordinator", "responder"]:
        if settings.DEMO_MODE:
            is_demo_auth = True
            print(f"[DEMO AUTH NOTICE] Evaluator demo session granted '{target_role}' role (DEMO_MODE=True).")
        else:
            # Strict production: verify PIN
            if target_role == "coordinator" and payload.pin != settings.COORDINATOR_PIN:
                raise HTTPException(
                    status_code=403,
                    detail="Forbidden: Coordinator PIN required to mint coordinator tokens in production mode."
                )
            if target_role == "responder" and payload.pin != settings.RESPONDER_PIN:
                raise HTTPException(
                    status_code=403,
                    detail="Forbidden: Responder PIN required to mint responder tokens in production mode."
                )

    # Establish clean persona identifiers
    now_iso = datetime.now(timezone.utc).isoformat()
    if not payload.uid:
        if target_role == "coordinator":
            uid = "coord-ops-lead"
            display_name = payload.name or "Marcus Vance (Operations Coordinator)"
        elif target_role == "responder":
            uid = "resp-unit-alpha"
            display_name = payload.name or "Sarah Jenkins (Field Unit Alpha)"
        else:
            uid = f"citizen-{int(datetime.now(timezone.utc).timestamp())}"
            display_name = payload.name or "Alex Morgan (Community Resident)"
    else:
        uid = payload.uid
        display_name = payload.name or uid

    # Upsert into SQLite users table for auditing
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (uid, role, name, email, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(uid) DO UPDATE SET
                    role=excluded.role,
                    name=excluded.name,
                    updated_at=excluded.updated_at;
            """, (uid, target_role, display_name, payload.email, now_iso, now_iso))
            conn.commit()
    except Exception as e:
        print(f"[Auth Error] Failed to persist user audit record in SQLite: {e}")

    token = create_access_token(
        uid=uid,
        role=target_role,
        name=display_name,
        email=payload.email,
        expires_delta_hours=24,
        is_demo_auth=is_demo_auth
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=target_role,
        uid=uid,
        name=display_name,
        email=payload.email,
        is_demo_auth=is_demo_auth,
        expires_in=86400
    )

@router.get("/me", response_model=AuthenticatedUser)
async def get_me(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Returns the cryptographically verified user identity and role."""
    return current_user
