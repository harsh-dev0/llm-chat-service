from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.database.session import SessionLocal
from app.models.chat import Chat
from app.models.message import Message as MessageRow
from app.services import llm_service, tool_service
from app.services.llm_service import Message as LLMMessage

logger = logging.getLogger(__name__)


def _save(db: Session, chat_id: int, role: str, content: str) -> MessageRow:
    row = MessageRow(chat_id=chat_id, role=role, content=content)
    db.add(row)          # brand-new object → add() required
    db.commit()
    db.refresh(row)      # pull back DB-generated id + created_at
    return row


def _load_history(db: Session, chat_id: int) -> list[LLMMessage]:
    """The LLM is stateless. This table IS the memory."""
    rows = list(
        db.execute(
            select(MessageRow)
            .where(MessageRow.chat_id == chat_id)
            .order_by(MessageRow.id.desc())          # id, not created_at — same-second inserts tie
            .limit(settings.MAX_HISTORY_MESSAGES)    # DESC + LIMIT = the NEWEST N
        ).scalars()
    )
    rows.reverse()                                   # back to chronological for the model
    while rows and rows[0].role != "user":           # trimming can strand a leading assistant turn
        rows.pop(0)
    return [{"role": r.role, "content": r.content} for r in rows]


async def send_message(
    db: Session, *, chat: Chat, content: str, model: str | None = None
) -> tuple[MessageRow, MessageRow]:
    """Non-streaming turn, with tools. Returns (user_row, assistant_row)."""
    # run_in_threadpool: these are blocking, and we are on the event loop.
    user_row = await run_in_threadpool(_save, db, chat.id, "user", content)
    history = await run_in_threadpool(_load_history, db, chat.id)

    reply = await tool_service.run_tool_loop(history, model=model)   # LLMError → global handler

    assistant_row = await run_in_threadpool(_save, db, chat.id, "assistant", reply)
    return user_row, assistant_row


async def stream_message(
    *, chat_id: int, content: str, model: str | None = None
) -> AsyncIterator[str]:
    """Yields raw text deltas. No SSE formatting — that's the route's job."""
    # Own session. On FastAPI < 0.118 the route's get_db session is ALREADY CLOSED
    # by the time this generator's first line executes.
    db = SessionLocal()
    try:
        await run_in_threadpool(_save, db, chat_id, "user", content)
        history = await run_in_threadpool(_load_history, db, chat_id)

        buffer: list[str] = []
        try:
            async for delta in llm_service.stream(history, model=model):
                buffer.append(delta)      # accumulate to persist
                yield delta               # hand out to transmit
        finally:
            # Runs on clean finish AND on client disconnect (GeneratorExit).
            # Deliberately sync: awaiting during generator close is fragile. ~2ms vs a 30s stream.
            text = "".join(buffer)
            if text:
                _save(db, chat_id, "assistant", text)   # persist the partial reply
            else:
                logger.warning("empty_stream", extra={"chat_id": chat_id})
    finally:
        db.close()