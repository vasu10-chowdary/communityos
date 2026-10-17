from typing import Optional, List
from pydantic import BaseModel
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import auth
from app.services.firebase_service import get_db

class AuthenticatedUser(BaseModel):
    uid: str
    role: str = "citizen"
    email: Optional[str] = None
    name: Optional[str] = None
    is_anonymous: bool = False

http_bearer = HTTPBearer(auto_error=False)

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)) -> AuthenticatedUser:
    """
    Verifies Firebase ID token from Authorization: Bearer <token>.
    Resolves role from:
    1. Custom claims (token['role'])
    2. Firestore users/{uid} document
    3. Default to 'citizen'
    
    SECURITY: Never trust client-supplied headers or body fields for role verification.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required: Missing or invalid Bearer token in Authorization header."
        )

    token = credentials.credentials.strip()

    try:
        # Verify the ID token using the official Firebase Admin SDK
        decoded_token = auth.verify_id_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid or expired authentication token: {str(e)}"
        )

    uid = decoded_token.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid token: missing subject UID.")

    # 1. Check custom claims
    role = decoded_token.get("role")

    # 2. If no custom claim, lookup Firestore users/{uid} document
    if not role:
        db = get_db()
        if db:
            try:
                user_doc = db.collection("users").document(uid).get()
                if user_doc.exists:
                    doc_data = user_doc.to_dict() or {}
                    role = doc_data.get("role")
            except Exception as e:
                print(f"[Auth Warning] Error fetching user document for role check: {e}")

    # 3. Default fallback role is citizen
    if not role:
        role = "citizen"

    # Normalize role to lowercase
    role = str(role).lower().strip()

    is_anon = decoded_token.get("firebase", {}).get("sign_in_provider") == "anonymous"

    return AuthenticatedUser(
        uid=uid,
        role=role,
        email=decoded_token.get("email"),
        name=decoded_token.get("name"),
        is_anonymous=is_anon
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
