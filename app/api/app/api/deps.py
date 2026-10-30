import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from app.core.config import Settings, get_settings

DEMO_BUYER_EMAIL = "buyer@demo.local"
DEMO_APPROVER_EMAIL = "approver@demo.local"


def _bearer_matches(supplied: str, token: str) -> bool:
    expected = f"Bearer {token}"
    if len(supplied) != len(expected):
        return False
    return hmac.compare_digest(supplied, expected)


def _demo_ready(settings: Settings) -> None:
    if settings.app_env != "local" or not settings.demo_mode:
        raise HTTPException(status_code=401, detail="Authentication is not configured.")


def require_demo_auth(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Buyer stand-in for the Phase 1 routes. Refuses to run outside local demo mode."""
    _demo_ready(settings)
    if not _bearer_matches(authorization or "", settings.demo_auth_token):
        raise HTTPException(status_code=401, detail="Authentication is required.")
    return DEMO_BUYER_EMAIL


def require_actor(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Buyer or approver stand-in. The role is resolved from the seeded user, not the body."""
    _demo_ready(settings)
    supplied = authorization or ""
    if _bearer_matches(supplied, settings.demo_auth_token):
        return DEMO_BUYER_EMAIL
    if _bearer_matches(supplied, settings.demo_approver_token):
        return DEMO_APPROVER_EMAIL
    raise HTTPException(status_code=401, detail="Authentication is required.")
