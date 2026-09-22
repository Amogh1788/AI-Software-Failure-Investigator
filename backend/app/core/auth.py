import logging
from typing import Optional
import jwt
from fastapi import Request, HTTPException, status, Depends
from pydantic import BaseModel
from app.core.config import settings
from app.core.database import get_supabase_client

logger = logging.getLogger("ai_investigator.auth")


class AuthenticatedUser(BaseModel):
    """Verified identity from Supabase Auth JWT."""
    id: str
    email: Optional[str] = None
    role: str = "authenticated"


async def get_current_user(request: Request) -> AuthenticatedUser:
    """
    FastAPI dependency that enforces Supabase JWT authentication.
    1. Extracts 'Authorization: Bearer <token>'.
    2. Cryptographically validates the JWT (via SUPABASE_JWT_SECRET or Supabase Auth API).
    3. Rejects missing, malformed, or expired tokens with HTTP 401.
    4. Sets request.state.user_id for access logging and rate limiting.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = auth_header.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. Primary: If SUPABASE_JWT_SECRET is configured, perform offline signature verification
    if settings.SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256", "ES256"],
                options={"verify_signature": True, "require": ["sub", "exp"]},
            )
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token claims: missing subject.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            user = AuthenticatedUser(
                id=str(user_id),
                email=payload.get("email"),
                role=payload.get("role", "authenticated"),
            )
            request.state.user_id = user.id
            return user
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication token: {exc}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 2. Secondary: Verify token against Supabase Auth API
    client = get_supabase_client()
    if client:
        try:
            user_res = client.auth.get_user(token)
            if user_res and getattr(user_res, "user", None):
                u = user_res.user
                user = AuthenticatedUser(
                    id=str(u.id),
                    email=getattr(u, "email", None),
                    role=getattr(u, "role", "authenticated") or "authenticated",
                )
                request.state.user_id = user.id
                return user
        except Exception as exc:
            logger.warning(f"Supabase auth token verification rejected: {exc}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Fallback if no verification method is available
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to verify authentication token: authentication service unavailable.",
        headers={"WWW-Authenticate": "Bearer"},
    )
