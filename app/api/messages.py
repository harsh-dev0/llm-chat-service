from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.chat import Chat
from app.models.message import Message
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.message import ChatMessageResponse, MessageCreate

router = APIRouter(prefix="/chats/{chat_id}/messages", tags=["Messages"])  # nested: messages live inside a chat


def _get_owned_chat(chat_id: int, db: Session, current_user: User) -> Chat:
    chat = db.get(Chat, chat_id)
    if chat is None or chat.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return chat


# CREATE
@router.post("/", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
def create_message(
    chat_id: int,
    data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = _get_owned_chat(chat_id, db, current_user)

    message = Message(chat_id=chat.id, role=data.role, content=data.content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


# LIST — oldest first, that's chat order
@router.get("/", response_model=list[ChatMessageResponse])
def list_messages(
    chat_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_chat(chat_id, db, current_user)   # authorize first

    stmt = (
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at)
        .offset(skip)
        .limit(limit)
    )
    return db.scalars(stmt).all()


# READ ONE
@router.get("/{message_id}", response_model=ChatMessageResponse)
def get_message(
    chat_id: int,
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_chat(chat_id, db, current_user)

    message = db.get(Message, message_id)
    if message is None or message.chat_id != chat_id:   # guard against /chats/1/messages/99 belonging to chat 2
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found")
    return message


# DELETE
@router.delete("/{message_id}", response_model=MessageResponse)
def delete_message(
    chat_id: int,
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_chat(chat_id, db, current_user)

    message = db.get(Message, message_id)
    if message is None or message.chat_id != chat_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found")

    db.delete(message)
    db.commit()
    return MessageResponse(message="Message deleted successfully")