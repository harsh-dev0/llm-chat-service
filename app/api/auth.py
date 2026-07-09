from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (create_access_token, create_refresh_token,
                               create_reset_token, hash_password, verify_password)
from app.api.deps import get_current_user, get_token_payload, credentials_error
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import (ChangePasswordRequest, ForgotPasswordRequest,
                              LoginRequest, ResetPasswordRequest, TokenResponse, RefreshRequest)
from app.schemas.common import MessageResponse
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Routes

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)       # stage
    db.commit()        # write
    db.refresh(user)   # pull back id, role, created_at
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email))
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        token_type="bearer",
    )

@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    payload = get_token_payload(data.refresh_token, "refresh")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise credentials_error
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        token_type="bearer",
    )


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email))
    if user:
        token = create_reset_token(user.id)
        print(f"[DEV] reset link: /auth/reset-password?token={token}")  # Day 3: email it
    return MessageResponse(message="If that email exists, a reset link has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    payload = get_token_payload(data.token, "reset")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise credentials_error
    user.hashed_password = hash_password(data.new_password)
    db.commit()                                    # UPDATE — no db.add() needed, user is tracked
    return MessageResponse(message="Password reset successfully")


@router.patch("/change-password", response_model=MessageResponse)
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return MessageResponse(message="Password changed successfully")

@router.get("/me", response_model=UserResponse)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/logout", response_model=MessageResponse)
def logout(current_user: User = Depends(get_current_user)):
    return MessageResponse(message="Logged out successfully")  # client deletes the token