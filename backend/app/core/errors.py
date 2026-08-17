"""
Exception handlers for VeriClaim AI MVP.

Every failure leaves the API in the `ErrorResponse` shape so the frontend has a
single error path. Unexpected exceptions are logged in full but reported to the
client as a generic message: stack traces and driver errors can carry
connection strings and row contents.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.middleware import get_request_id
from app.schemas.error_schemas import ErrorResponse, FieldError, ValidationErrorResponse

logger = logging.getLogger(__name__)

# Machine-readable codes paired with the HTTP statuses the API returns.
_STATUS_CODES = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: "PAYLOAD_TOO_LARGE",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "UNSUPPORTED_MEDIA_TYPE",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
    status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
    status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
}

GENERIC_MESSAGE = "Something went wrong on our end. Please try again."


def _code_for(status_code: int) -> str:
    """Map an HTTP status onto a stable error code."""
    return _STATUS_CODES.get(status_code, "INTERNAL_ERROR")


def _render(status_code: int, body: ErrorResponse, headers: dict | None = None) -> JSONResponse:
    """Serialise an error envelope, dropping unset keys."""
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json", exclude_none=True),
        headers=headers,
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    Render deliberate HTTPExceptions raised by route and dependency code.

    Args:
        request: The active request.
        exc: The raised exception.

    Returns:
        A JSON error envelope.
    """
    return _render(
        exc.status_code,
        ErrorResponse(
            error=_code_for(exc.status_code),
            message=str(exc.detail),
            request_id=get_request_id(),
        ),
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Turn Pydantic validation failures into per-field messages.

    Args:
        request: The active request.
        exc: The validation error raised by FastAPI.

    Returns:
        A JSON error envelope listing the offending fields.
    """
    field_errors: list[FieldError] = []
    for error in exc.errors():
        # loc looks like ("body", "email"); drop the source segment.
        location = [str(part) for part in error.get("loc", ()) if part != "body"]
        field_errors.append(
            FieldError(
                field=".".join(location) or "body",
                message=error.get("msg", "Invalid value"),
                type=error.get("type"),
            )
        )

    logger.info(
        "Rejected %s %s: %d validation error(s)",
        request.method,
        request.url.path,
        len(field_errors),
        extra={"extra_fields": {"request_id": get_request_id()}},
    )

    return _render(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        ValidationErrorResponse(
            error="VALIDATION_ERROR",
            message="Some of the submitted details need attention.",
            errors=field_errors,
            request_id=get_request_id(),
        ),
    )


async def database_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """
    Handle database failures without leaking driver detail.

    Args:
        request: The active request.
        exc: The SQLAlchemy error.

    Returns:
        A 503 JSON error envelope.
    """
    logger.exception(
        "Database failure on %s %s",
        request.method,
        request.url.path,
        extra={"extra_fields": {"request_id": get_request_id()}},
    )
    return _render(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        ErrorResponse(
            error="SERVICE_UNAVAILABLE",
            message="We could not reach the claims database. Please try again shortly.",
            # Driver errors quote the failing SQL and its bound parameters, and
            # connection errors quote the DSN. Neither goes to the client; the
            # full error is in the log line above, keyed by request_id.
            request_id=get_request_id(),
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch anything not handled above.

    Args:
        request: The active request.
        exc: The unexpected exception.

    Returns:
        A 500 JSON error envelope.
    """
    logger.exception(
        "Unhandled error on %s %s",
        request.method,
        request.url.path,
        extra={"extra_fields": {"request_id": get_request_id()}},
    )
    return _render(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorResponse(
            error="INTERNAL_ERROR",
            message=GENERIC_MESSAGE,
            # No exception text here even in debug: messages routinely quote
            # credentials, tokens, and claimant data. Correlate via request_id.
            request_id=get_request_id(),
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Attach every handler to the application.

    Args:
        app: The FastAPI application.
    """
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
