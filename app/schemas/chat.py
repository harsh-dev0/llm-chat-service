from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatCreate(BaseModel):
    title: str = "New chat"


class ChatUpdate(BaseModel):
    title: str | None = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    created_at: datetime