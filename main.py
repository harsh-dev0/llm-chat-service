from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chats, messages, users
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import RequestContextMiddleware, setup_logging
from app.database.session import Base, engine
from app.services import llm_service

setup_logging()   # before FastAPI() so startup logs are formatted too


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)   # no Alembic yet — creates missing tables only
    yield
    await llm_service.aclose()              # return the httpx pool


app = FastAPI(title="AI Chat Backend", lifespan=lifespan)

app.add_middleware(RequestContextMiddleware)   # added LAST = runs FIRST (outermost)
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
def health() -> dict[str, str]:
    return {"status": "ok"}