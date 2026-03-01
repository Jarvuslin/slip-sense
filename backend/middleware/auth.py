"""Supabase JWT authentication dependency for FastAPI."""

from __future__ import annotations

import logging
import os
import uuid

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)

# Cache for the JWKS fetched from Supabase
_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    """Fetch and cache the JSON Web Key Set from Supabase."""
    global _jwks_cache
    if _jwks_cache is None:
        supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
        async with httpx.AsyncClient() as client:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            _jwks_cache = resp.json()
        logger.info("Fetched JWKS from %s", jwks_url)
    return _jwks_cache


def _find_jwk(jwks: dict, kid: str) -> dict:
    """Find a key in the JWKS by its key ID."""
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    raise JWTError(f"No matching key found for kid={kid}")


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> uuid.UUID:
    """Validate the Supabase JWT and return the user's UUID.

    The token is expected in the Authorization header as ``Bearer <token>``.
    The ``sub`` claim contains the Supabase user id.

    Supports both HS256 (shared secret) and ES256 (ECDSA public key via JWKS).
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    token = credentials.credentials

    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")

        if alg == "HS256":
            # Symmetric: verify with the shared JWT secret
            key = os.getenv("SUPABASE_JWT_SECRET", "")
            algorithms = ["HS256"]
        else:
            # Asymmetric (ES256, RS256, etc.): verify with JWKS public key
            kid = header.get("kid")
            if not kid:
                raise JWTError("Token header missing 'kid' for asymmetric algorithm")
            jwks = await _get_jwks()
            key = _find_jwk(jwks, kid)
            algorithms = [alg]

        payload = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        )

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )

    try:
        user_id = uuid.UUID(sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user id in token",
        )

    request.state.user_id = user_id
    return user_id
