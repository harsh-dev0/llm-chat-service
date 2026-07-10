from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal["user", "assistant"]


class MessageCreate(BaseModel):
    """What the client sends. Role is NOT here — the server decides who is speaking."""

    content: str = Field(min_length=1, max_length=8000)   # cost + context-window guard
    model: str | None = None                              # validated against ALLOWED_MODELS in the service

    @field_validator("content")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:                                          # "   " passes min_length=1, but is empty
            raise ValueError("content cannot be blank")
        return v


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_id: int
    role: Role
    content: str
    created_at: datetime


class ChatTurnResponse(BaseModel):
    """One POST now produces two rows. Return both so the client needn't re-fetch."""

    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse