import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")  # reads "Authorization: Bearer <token>"

credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_token_payload(token: str, expected_type: str) -> dict:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise credentials_error
    if payload.get("type") != expected_type:
        raise credentials_error
    return payload


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),      # dependency chain: FastAPI resolves both
) -> User:
    payload = get_token_payload(token, "access")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise credentials_error
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:  # role-based auth
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user