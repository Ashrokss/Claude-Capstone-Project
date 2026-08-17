"""Aggregate claim metrics for the adjuster dashboard."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import require_staff
from app.schemas.detail_schemas import AnalyticsResponse
from app.services import claim_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

DbSession = Annotated[AsyncSession, Depends(get_async_session)]


@router.get(
    "",
    response_model=AnalyticsResponse,
    dependencies=[Depends(require_staff())],
    summary="Dashboard KPI metrics",
)
async def get_analytics(db: DbSession):
    """
    Return headline claim metrics.

    Staff only: these figures aggregate across every customer's claims.
    """
    return AnalyticsResponse(**await claim_service.analytics_snapshot(db))
