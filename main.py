import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chats, messages, users
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.database.session import Base, engine
from app import models  # noqa: F401 — registers all 3 models

Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="LLM Chat Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(chats.router)
app.include_router(messages.router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}