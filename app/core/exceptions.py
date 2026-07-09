import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Validation failed", "errors": exc.errors()},
        )

    @app.exception_handler(SQLAlchemyError)
    async def db_handler(request: Request, exc: SQLAlchemyError):
        logger.exception("Database error on %s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Database error"})

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})