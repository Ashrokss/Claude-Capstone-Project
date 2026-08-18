"""Claim submission, listing, retrieval, and status updates."""

import logging
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import CurrentUserDep, assert_can_access_claim, require_staff
from app.schemas.assessment_schemas import AssessmentRead
from app.schemas.decision_schemas import DecisionRead
from app.schemas.claim_schemas import (
    ClaimCreate,
    ClaimListItem,
    ClaimListResponse,
    ClaimRead,
    ClaimUpdate,
)
from app.schemas.common import PaginationMeta
from app.schemas.detail_schemas import ClaimCreatedResponse, ClaimDetail
from app.schemas.enums import ClaimPriority, ClaimStatus, FraudRiskLevel
from app.services import claim_service
from app.services.job_queue import analysis_queue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claims", tags=["Claims"])

DbSession = Annotated[AsyncSession, Depends(get_async_session)]


@router.post(
    "",
    response_model=ClaimCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new claim",
)
async def create_claim(payload: ClaimCreate, db: DbSession, user: CurrentUserDep):
    """
    Register a claim and queue it for AI analysis.

    Analysis runs in the background; poll the assessment endpoint for progress.
    """
    claim = await claim_service.create_claim(db, payload, created_by=user.id)
    await db.commit()

    # Queued after the commit so the worker cannot read a claim that is not yet
    # visible to another session.
    queued = await analysis_queue.enqueue_analysis(claim.id)

    return ClaimCreatedResponse(
        id=str(claim.id),
        claim_number=claim.claim_number,
        status=claim.status,
        analysis_queued=queued,
    )


@router.get(
    "",
    response_model=ClaimListResponse,
    summary="List claims",
)
async def list_claims(
    db: DbSession,
    user: CurrentUserDep,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[ClaimStatus] = Query(None, alias="status"),
    fraud_risk: Optional[FraudRiskLevel] = Query(None),
    priority: Optional[ClaimPriority] = Query(None),
    search: Optional[str] = Query(None, max_length=200),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
):
    """
    Page through claims with filtering, search, and sorting.

    Staff see every claim; a customer sees only their own.
    """
    if sort_by not in claim_service.SORTABLE_COLUMNS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot sort by {sort_by!r}. "
            f"Valid options: {', '.join(sorted(claim_service.SORTABLE_COLUMNS))}",
        )

    rows, total = await claim_service.list_claims(
        db,
        page=page,
        page_size=limit,
        status=status_filter.value if status_filter else None,
        fraud_risk=fraud_risk.value if fraud_risk else None,
        priority=priority.value if priority else None,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        # Scoping happens in the query, not by filtering after the fact, so
        # pagination counts stay correct for the caller.
        owner_id=None if user.is_staff else user.id,
    )

    return ClaimListResponse(
        items=[ClaimListItem.model_validate(row) for row in rows],
        pagination=PaginationMeta.build(total=total, page=page, page_size=limit),
    )


@router.get(
    "/{claim_id}",
    response_model=ClaimDetail,
    summary="Get a claim with all related records",
)
async def get_claim(claim_id: UUID, db: DbSession, user: CurrentUserDep):
    """Return a claim with its documents, images, latest assessment, and decision."""
    claim = await claim_service.get_claim_detail(db, claim_id)
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    assert_can_access_claim(user, claim.created_by_user_id)

    detail = ClaimDetail.model_validate(claim)
    # Both relationships are ordered newest-first, so the head is the current one.
    detail.assessment = (
        AssessmentRead.model_validate(claim.assessments[0]) if claim.assessments else None
    )
    detail.decision = (
        DecisionRead.model_validate(claim.decisions[0]) if claim.decisions else None
    )
    return detail


@router.patch(
    "/{claim_id}",
    response_model=ClaimRead,
    dependencies=[Depends(require_staff())],
    summary="Update a claim",
)
async def update_claim(
    claim_id: UUID, payload: ClaimUpdate, db: DbSession, user: CurrentUserDep
):
    """
    Apply a partial update to a claim.

    Restricted to staff: status drives routing and the customer-facing view.
    """
    claim = await claim_service.get_claim(db, claim_id)
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields supplied to update",
        )

    new_status = changes.pop("status", None)
    for field, value in changes.items():
        setattr(claim, field, value)

    if new_status is not None:
        await claim_service.update_claim_status(
            db, claim, ClaimStatus(new_status), actor=str(user.id)
        )

    await db.commit()
    await db.refresh(claim)
    return ClaimRead.model_validate(claim)
