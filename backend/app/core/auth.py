import jwt
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.services.database import get_db

try:
    import firebase_admin
    from firebase_admin import auth as fb_auth
except ImportError:
    firebase_admin = None
    fb_auth = None

class AuthenticatedUser(BaseModel):
    uid: str
    role: str = "citizen"
    email: Optional[str] = None
    name: Optional[str] = None
    is_anonymous: bool = False
    is_demo_auth: bool = False

http_bearer = HTTPBearer(auto_error=False)

def create_access_token(
    uid: str,
    role: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    expires_delta_hours: int = 24,
    is_demo_auth: bool = False
) -> str:
    """
    Creates a cryptographically signed HMAC-SHA256 JWT access token.
    Tamper-proof role and user claim binding.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": uid,
        "uid": uid,
        "role": role.lower().strip(),
        "name": name or uid,
        "email": email,
        "is_demo_auth": is_demo_auth,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=expires_delta_hours)).timestamp())
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)) -> AuthenticatedUser:
    """
    Verifies Bearer token from Authorization header.
    Resolves role from:
    1. Cryptographically verified JWT claims ('role')
    2. SQLite users table (users.role)
    3. Strict default to 'citizen'
    
    SECURITY: Never trust client-supplied headers or body fields for role verification.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required: Missing or invalid Bearer token in Authorization header."
        )

    token = credentials.credentials.strip()

    uid = None
    role = None
    email = None
    name = None
    is_anon = False
    is_demo_auth = False

    try:
        # Verify and decode signed JWT using server secret
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        uid = payload.get("sub") or payload.get("uid")
        role = payload.get("role")
        email = payload.get("email")
        name = payload.get("name")
        is_demo_auth = bool(payload.get("is_demo_auth", False))
        is_anon = is_demo_auth
    except jwt.PyJWTError:
        # Fallback to Firebase verify_id_token if firebase auth is available
        if fb_auth:
            try:
                decoded_token = fb_auth.verify_id_token(token)
                uid = decoded_token.get("uid")
                role = decoded_token.get("role")
                email = decoded_token.get("email")
                name = decoded_token.get("name")
                is_anon = decoded_token.get("firebase", {}).get("sign_in_provider") == "anonymous"
            except Exception as e:
                raise HTTPException(
                    status_code=401,
                    detail=f"Invalid or expired authentication token: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired authentication token: signature verification failed."
            )

    if not uid:
        raise HTTPException(status_code=401, detail="Invalid token: missing subject UID.")

    # If role not embedded in signed token, query SQLite users table
    if not role or role == "citizen":
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT role, name, email FROM users WHERE uid = ?", (uid,))
                row = cursor.fetchone()
                if row and row[0]:
                    role = row[0]
                    if not name and row[1]:
                        name = row[1]
                    if not email and row[2]:
                        email = row[2]
        except Exception as e:
            print(f"[Auth Warning] SQLite user document lookup failed: {e}")

    if not role:
        role = "citizen"

    role = str(role).lower().strip()

    return AuthenticatedUser(
        uid=uid,
        role=role,
        email=email,
        name=name,
        is_anonymous=is_anon,
        is_demo_auth=is_demo_auth
    )

def require_role(allowed_roles: List[str]):
    """
    Dependency factory to enforce role-based access control (RBAC).
    """
    allowed_normalized = [r.lower().strip() for r in allowed_roles]

    async def role_checker(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if current_user.role not in allowed_normalized:
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden: Action requires one of {allowed_roles} role, but your role is '{current_user.role}'."
            )
        return current_user

    return role_checker

# Predefined role dependencies
require_coordinator = require_role(["coordinator", "admin"])
require_responder = require_role(["responder", "coordinator", "admin"])
require_citizen = require_role(["citizen", "coordinator", "responder", "admin"])
