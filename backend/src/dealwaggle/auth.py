from functools import lru_cache

import jwt
from dealwaggle_db.models import Membership, User
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from dealwaggle.config import get_settings
from dealwaggle.db import get_session


@lru_cache
def jwks_client(url: str):
    return jwt.PyJWKClient(url, cache_keys=True, lifespan=300, timeout=5)


def current_user(request: Request, session: Session = Depends(get_session)) -> User:
    settings = get_settings()
    if settings.demo_mode:
        subject = "demo:" + request.headers.get("x-demo-user", "alice")
    else:
        authorization = request.headers.get("authorization", "")
        if not authorization.startswith("Bearer ") or not settings.jwt_jwks_url:
            raise HTTPException(
                401, "Sign in to DealWaggle", headers={"WWW-Authenticate": "Bearer"}
            )
        token = authorization[7:]
        try:
            key = jwks_client(settings.jwt_jwks_url).get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                key.key,
                algorithms=["RS256"],
                audience=settings.jwt_audience,
                issuer=settings.jwt_issuer,
                options={"require": ["exp", "iat", "sub"]},
            )
            subject = claims["sub"]
        except (jwt.PyJWTError, ValueError):
            raise HTTPException(401, "Invalid or expired session") from None
    user = session.scalar(select(User).where(User.auth_subject == subject))
    if not user:
        raise HTTPException(403, "Your account has not been provisioned")
    return user


def require_member(session: Session, user_id: str, organisation_id: str, owner: bool = False):
    membership = session.get(Membership, (user_id, organisation_id))
    if not membership or (owner and membership.role != "owner"):
        raise HTTPException(403, "Organisation access denied")
    return membership
