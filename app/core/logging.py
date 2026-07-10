from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar
from logging.config import dictConfig

from app.core.config import settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_RESERVED = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for k, v in record.__dict__.items():          # anything passed via logger.info(..., extra={...})
            if k not in _RESERVED:
                payload[k] = v
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    fmt = "app.core.logging.JsonFormatter" if settings.LOG_JSON else "logging.Formatter"
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"default": {"()": fmt, "format": "%(levelname)s %(name)s %(message)s"}},
        "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "default"}},
        "root": {"handlers": ["console"], "level": settings.LOG_LEVEL},
        "loggers": {
            "uvicorn":        {"handlers": ["console"], "level": "INFO", "propagate": False},
            "uvicorn.error":  {"handlers": ["console"], "level": "INFO", "propagate": False},
            "uvicorn.access": {"handlers": ["console"], "level": "WARNING", "propagate": False},  # we log our own
            "httpx":          {"level": "WARNING"},   # the openai SDK logs every request at INFO
        },
    })


class RequestContextMiddleware:
    """Pure ASGI. NOT BaseHTTPMiddleware — that one buffers responses and breaks SSE."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        headers = dict(scope["headers"])
        rid = headers.get(b"x-request-id", b"").decode() or uuid.uuid4().hex[:12]
        token = request_id_var.set(rid)
        start = time.perf_counter()
        status = {"code": 0}

        async def send_wrapper(message) -> None:
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
                message["headers"] = [*message.get("headers", []), (b"x-request-id", rid.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # fires AFTER the stream drains, so duration_ms is the real end-to-end number
            logging.getLogger("app.request").info(
                "request",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status["code"],
                    "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                },
            )
            request_id_var.reset(token)