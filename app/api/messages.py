from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.chat import Chat
from app.models.message import Message
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.message import ChatMessageResponse, ChatTurnResponse, MessageCreate
from app.services import chat_service, llm_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chats/{chat_id}/messages", tags=["Messages"])  # nested: messages live inside a chat


def _get_owned_chat(chat_id: int, db: Session, current_user: User) -> Chat:
    chat = db.get(Chat, chat_id)
    if chat is None or chat.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return chat


# CREATE — now a full turn: save user msg → build history → call LLM → save reply
@router.post("/", response_model=ChatTurnResponse, status_code=status.HTTP_201_CREATED)
async def send_message(                                  # async def: we await an 8s LLM call
    chat_id: int,
    data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = _get_owned_chat(chat_id, db, current_user)

    user_msg, assistant_msg = await chat_service.send_message(
        db, chat=chat, content=data.content, model=data.model
    )
    return ChatTurnResponse(user_message=user_msg, assistant_message=assistant_msg)


# STREAM — same turn, delivered as SSE deltas
@router.post("/stream")
async def stream_message(
    chat_id: int,
    data: MessageCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = _get_owned_chat(chat_id, db, current_user)
    llm_service.resolve_model(data.model)   # validate BEFORE the 200 goes out — see note below

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for delta in chat_service.stream_message(
                chat_id=chat.id, content=data.content, model=data.model   
            ):
                if await request.is_disconnected():      # tab closed → stop; finally saves the partial
                    break
                # json.dumps: a delta can contain "\n" (code blocks), which would end the SSE frame
                yield f"data: {json.dumps({'delta': delta})}\n\n"
        except llm_service.LLMError as exc:
            logger.warning("stream_failed chat_id=%s detail=%s", chat.id, exc.message)
            yield f"event: error\ndata: {json.dumps({'detail': exc.message})}\n\n"
        else:
            yield "data: [DONE]\n\n"                     # only on clean completion, hence `else`

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",                   # nginx buffers by default and eats streaming
        },
    )


# LIST — oldest first, that's chat order
@router.get("/", response_model=list[ChatMessageResponse])
def list_messages(                                       # def: one blocking SELECT → threadpool
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
        .order_by(Message.id)                    # id, not created_at — same-second inserts tie
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