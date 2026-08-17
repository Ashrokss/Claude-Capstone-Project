"""
Error response schemas.

A single response shape across the API means the frontend has one error path to
handle rather than one per endpoint.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class FieldError(BaseModel):
    """A single field-level validation failure."""

    field: str = Field(..., description="Dotted path to the offending field")
    message: str = Field(..., description="What is wrong with it")
    type: Optional[str] = Field(None, description="Pydantic error type identifier")


class ErrorResponse(BaseModel):
    """
    Standard error envelope.

    `message` is safe to show a user; `detail` carries developer-facing context
    and is omitted in production responses for unexpected errors.
    """

    error: str = Field(..., description="Machine-readable error code, e.g. NOT_FOUND")
    message: str = Field(..., description="Human-readable message safe for display")
    detail: Optional[Any] = Field(None, description="Additional developer context")
    request_id: Optional[str] = Field(None, description="Correlates with server logs")


class ValidationErrorResponse(ErrorResponse):
    """Error envelope for request validation failures."""

    errors: list[FieldError] = Field(default_factory=list)
