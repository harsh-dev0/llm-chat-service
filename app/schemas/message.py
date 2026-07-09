from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class MessageCreate(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_id: int
    role: str
    content: str
    created_at: datetime