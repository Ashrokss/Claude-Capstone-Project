"""Human review decisions on a claim."""

import logging
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import CurrentUserDep, assert_can_access_claim, require_staff
from app.models import HumanDecision
from app.schemas.decision_schemas import DecisionCreate, DecisionRead
from app.schemas.enums import ClaimStatus, DecisionType
from app.services import claim_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claims/{claim_id}", tags=["Decisions"])

DbSession = Annotated[AsyncSession, Depends(get_async_session)]

# Statuses from which a first decision may be taken.
DECIDABLE = {ClaimStatus.PENDING_REVIEW.value, ClaimStatus.INFORMATION_REQUIRED.value}


@router.post(
    "/decision",
    response_model=DecisionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_staff())],
    summary="Record a human review decision",
)
async def create_decision(
    claim_id: UUID, payload: DecisionCreate, db: DbSession, user: CurrentUserDep
):
    """
    Record an adjuster's decision and move the claim accordingly.

    A claim may only be decided once. The reviewer's identity is taken from the
    verified token, not the request body, so it cannot be spoofed.
    """
    claim = await claim_service.get_claim(db, claim_id)
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    existing = await claim_service.latest_decision(db, claim_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This claim was already decided ({existing.decision}) by "
                f"{existing.reviewer_name}."
            ),
        )

    if claim.status not in DECIDABLE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A claim in {claim.status} status cannot be decided. "
                "It must be awaiting review."
            ),
        )

    decision = HumanDecision(
        claim_id=claim_id,
        decision=payload.decision.value,
        # Identity comes from the JWT; the body only carries the reviewer's
        # display name as a fallback for service accounts.
        reviewer_name=payload.reviewer_name,
        reviewer_email=payload.reviewer_email or user.email,
        reviewer_id=user.id,
        decision_comments=payload.decision_comments,
        requested_information=payload.requested_information,
        investigation_notes=payload.investigation_notes,
    )
    db.add(decision)

    await claim_service.update_claim_status(
        db,
        claim,
        claim_service.DECISION_STATUS[DecisionType(payload.decision)],
        actor=str(user.id),
    )

    await db.commit()
    await db.refresh(decision)

    logger.info(
        "Claim %s decided: %s by %s",
        claim.claim_number,
        decision.decision,
        decision.reviewer_name,
        extra={"extra_fields": {"claim_id": str(claim_id), "reviewer_id": str(user.id)}},
    )
    return DecisionRead.model_validate(decision)


@router.get(
    "/decision",
    response_model=Optional[DecisionRead],
    summary="Get the decision for a claim",
)
async def get_decision(claim_id: UUID, db: DbSession, user: CurrentUserDep):
    """Return the recorded decision, or null if the claim is still undecided."""
    claim = await claim_service.get_claim(db, claim_id)
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    assert_can_access_claim(user, claim.created_by_user_id)

    decision = await claim_service.latest_decision(db, claim_id)
    return DecisionRead.model_validate(decision) if decision else None
