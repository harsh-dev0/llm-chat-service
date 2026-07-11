from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(subject: int, expires_delta: timedelta, token_type: str) -> str:
    payload = {
        "sub": str(subject),                                  # who
        "exp": datetime.now(timezone.utc) + expires_delta,    # until when
        "type": token_type,                                   # access vs refresh
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: int) -> str:
    return _create_token(user_id, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def create_refresh_token(user_id: int) -> str:
    return _create_token(user_id, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), "refresh")

def create_reset_token(user_id: int) -> str:
    return _create_token(user_id, timedelta(minutes=30), "reset")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])  # raises if expired/tampered