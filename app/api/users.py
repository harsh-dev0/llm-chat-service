from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.database.session import get_db
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


def _get_user_or_404(user_id: int, db: Session) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _authorize(user_id: int, current_user: User) -> None:
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not enough permissions")


# READ ALL — admin only
@router.get("/", response_model=list[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return db.scalars(select(User).offset(skip).limit(limit)).all()


# READ ONE
@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _authorize(user_id, current_user)
    return _get_user_or_404(user_id, db)


# UPDATE
@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _authorize(user_id, current_user)
    user = _get_user_or_404(user_id, db)

    updates = data.model_dump(exclude_unset=True)   # only fields the client actually sent

    if "email" in updates:
        clash = db.scalar(select(User).where(User.email == updates["email"], User.id != user_id))
        if clash:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")

    for field, value in updates.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


# DELETE
@router.delete("/{user_id}", response_model=MessageResponse)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _authorize(user_id, current_user)
    user = _get_user_or_404(user_id, db)
    db.delete(user)
    db.commit()
    return MessageResponse(message="User deleted successfully")