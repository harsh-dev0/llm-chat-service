from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.chat import Chat
from app.models.user import User
from app.schemas.chat import ChatCreate, ChatResponse, ChatUpdate
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/chats", tags=["Chats"])


def _get_owned_chat(chat_id: int, db: Session, current_user: User) -> Chat:
    chat = db.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Chat not found")
    if chat.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Chat not found")  # 404, not 403 — don't reveal it exists
    return chat


# CREATE
@router.post("/", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
def create_chat(
    data: ChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = Chat(title=data.title, user_id=current_user.id)   # owner comes from the token, never the body
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


# LIST — only mine
@router.get("/", response_model=list[ChatResponse])
def list_chats(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Chat)
        .where(Chat.user_id == current_user.id)
        .order_by(Chat.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return db.scalars(stmt).all()


# READ ONE
@router.get("/{chat_id}", response_model=ChatResponse)
def get_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_chat(chat_id, db, current_user)


# UPDATE (rename)
@router.patch("/{chat_id}", response_model=ChatResponse)
def update_chat(
    chat_id: int,
    data: ChatUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = _get_owned_chat(chat_id, db, current_user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(chat, field, value)
    db.commit()
    db.refresh(chat)
    return chat


# DELETE — cascade wipes its messages
@router.delete("/{chat_id}", response_model=MessageResponse)
def delete_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = _get_owned_chat(chat_id, db, current_user)
    db.delete(chat)
    db.commit()
    return MessageResponse(message="Chat deleted successfully")