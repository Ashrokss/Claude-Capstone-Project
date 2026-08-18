"""
HTTP middleware for VeriClaim AI MVP.

Assigns each request a correlation id, records an access log entry, and makes
the id available to error handlers so a user-facing failure can be traced back
to a specific log line.
"""

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.access")

REQUEST_ID_HEADER = "X-Request-ID"

# Readable from anywhere in the request's task, including exception handlers.
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id() -> Optional[str]:
    """Return the correlation id for the request being handled, if any."""
    return _request_id.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Attach a correlation id to each request and log its outcome.

    An inbound `X-Request-ID` is honoured so a trace started at the frontend or
    a proxy carries through; otherwise one is generated. The id is echoed on the
    response and included in error bodies.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        token = _request_id.set(request_id)
        request.state.request_id = request_id

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # The exception handlers build the client response; this records
            # the access-log side before re-raising.
            duration_ms = (time.perf_counter() - started) * 1000
            logger.exception(
                "%s %s -> unhandled exception in %.1fms",
                request.method,
                request.url.path,
                duration_ms,
                extra={
                    "extra_fields": {
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": round(duration_ms, 1),
                    }
                },
            )
            raise
        finally:
            _request_id.reset(token)

        duration_ms = (time.perf_counter() - started) * 1000
        response.headers[REQUEST_ID_HEADER] = request_id

        logger.info(
            "%s %s -> %s in %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 1),
                }
            },
        )
        return response
