"""
auth.py — FastAPI dependencies for user tier resolution
--------------------------------------------------------
Routes call get_user_tier() to find out if the requester is
"free" or "pro". The tier is stored in user_profiles.tier
and set by the Stripe webhook when a subscription is created
or cancelled.

For now, tier is read from the Supabase JWT passed in the
Authorization header. Unauthenticated requests are treated
as "free" — no hard block, just reduced data.
"""

from fastapi import Depends, Header
from typing import Optional
from app.database import get_client


async def get_user_tier(authorization: Optional[str] = Header(default=None)) -> str:
    """
    Resolve the requesting user's tier: "free" or "pro".

    - No Authorization header → "free"
    - Valid JWT but no pro subscription → "free"
    - Valid JWT with pro subscription → "pro"
    """
    if not authorization or not authorization.startswith("Bearer "):
        return "free"

    token = authorization.removeprefix("Bearer ").strip()

    try:
        client = get_client()
        # Verify the JWT and get the user id
        user_resp = client.auth.get_user(token)
        if not user_resp or not user_resp.user:
            return "free"

        user_id = user_resp.user.id

        # Look up their tier in user_profiles
        profile = (
            client.table("user_profiles")
            .select("tier")
            .eq("id", user_id)
            .single()
            .execute()
        )

        if profile.data and profile.data.get("tier") == "pro":
            return "pro"

    except Exception:
        # Any error (expired token, network) → treat as free
        pass

    return "free"


# Convenience dependency that raises 402 if user is not pro
from fastapi import HTTPException

async def require_pro(tier: str = Depends(get_user_tier)):
    if tier != "pro":
        raise HTTPException(
            status_code=402,
            detail={
                "error": "pro_required",
                "message": "This feature requires a PantherGrades Pro subscription.",
                "upgrade_url": "/subscribe",
            },
        )
    return tier