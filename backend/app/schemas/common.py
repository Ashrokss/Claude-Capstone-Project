"""
Shared base classes and pagination helpers for VeriClaim AI MVP schemas.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class APIModel(BaseModel):
    """
    Base for request schemas.

    Rejects unknown keys so a typo in a client payload surfaces as a 422 rather
    than being silently dropped, and strips incidental whitespace.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class ORMModel(BaseModel):
    """
    Base for response schemas built from SQLAlchemy instances.

    `from_attributes` lets `Model.model_validate(orm_obj)` read attributes
    directly instead of requiring a dict.
    """

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
    )


class PaginationMeta(BaseModel):
    """Pagination envelope returned alongside list responses."""

    total: int = Field(..., ge=0, description="Total rows matching the query")
    page: int = Field(..., ge=1, description="Current page, 1-indexed")
    page_size: int = Field(..., ge=1, description="Rows per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")

    @classmethod
    def build(cls, total: int, page: int, page_size: int) -> "PaginationMeta":
        """
        Construct pagination metadata from a row count and page window.

        Args:
            total: Total rows matching the query.
            page: Current page, 1-indexed.
            page_size: Rows per page.

        Returns:
            Populated `PaginationMeta`.
        """
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        return cls(total=total, page=page, page_size=page_size, total_pages=total_pages)


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list response."""

    items: list[T] = Field(default_factory=list)
    pagination: PaginationMeta
