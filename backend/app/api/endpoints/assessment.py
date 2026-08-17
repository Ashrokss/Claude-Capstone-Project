"""Triggering AI analysis and retrieving its results."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import CurrentUserDep, assert_can_access_claim
from app.schemas.assessment_schemas import AssessmentRead
from app.schemas.detail_schemas import AnalysisStatusResponse, AssessmentStatusResponse
from app.schemas.enums import AssessmentStatus, ClaimStatus
from app.services import claim_service
from app.services.job_queue import analysis_queue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claims/{claim_id}", tags=["Assessment"])

DbSession = Annotated[AsyncSession, Depends(get_async_session)]

# Shown to the UI while a run is in flight, so progress is legible.
PIPELINE_STEPS = [
    "Extracting incident details",
    "Reading supporting documents",
    "Assessing vehicle damage",
    "Checking policy coverage",
    "Evaluating fraud risk",
    "Preparing the summary",
]


@router.post(
    "/analyze",
    response_model=AnalysisStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue a claim for AI analysis",
)
async def trigger_analysis(claim_id: UUID, db: DbSession, user: CurrentUserDep):
    """
    Queue analysis for a claim.

    Returns immediately: the work runs in the background and takes tens of
    seconds. Re-queueing a claim already awaiting analysis is a no-op.
    """
    claim = await claim_service.get_claim(db, claim_id)
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    assert_can_access_claim(user, claim.created_by_user_id)

    queued = await analysis_queue.enqueue_analysis(claim.id)
    return AnalysisStatusResponse(
        claim_id=str(claim.id),
        status="QUEUED" if queued else "PROCESSING",
        message=(
            "Analysis has been queued."
            if queued
            else "This claim is already being analysed."
        ),
        queue_depth=analysis_queue.depth(),
    )


@router.get(
    "/assessment",
    response_model=AssessmentRead | AssessmentStatusResponse,
    summary="Get the AI assessment or its progress",
)
async def get_assessment(claim_id: UUID, db: DbSession, user: CurrentUserDep):
    """
    Return the completed assessment, or the current progress if it is still running.

    A caller polling this endpoint gets a status payload until the run finishes,
    then the assessment itself.
    """
    claim = await claim_service.get_claim(db, claim_id)
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    assert_can_access_claim(user, claim.created_by_user_id)

    assessment = await claim_service.latest_assessment(db, claim_id)

    if assessment is None:
        return AssessmentStatusResponse(
            claim_id=str(claim_id),
            assessment_status=AssessmentStatus.PENDING,
            message=(
                "Analysis is queued and has not started yet."
                if claim.status == ClaimStatus.PROCESSING.value
                else "No analysis has been run for this claim yet."
            ),
            steps=PIPELINE_STEPS,
        )

    if assessment.assessment_status == AssessmentStatus.PENDING.value:
        return AssessmentStatusResponse(
            claim_id=str(claim_id),
            assessment_status=AssessmentStatus.PENDING,
            message="Analysis is in progress.",
            steps=PIPELINE_STEPS,
        )

    if assessment.assessment_status == AssessmentStatus.FAILED.value:
        return AssessmentStatusResponse(
            claim_id=str(claim_id),
            assessment_status=AssessmentStatus.FAILED,
            message="Analysis could not be completed. You can retry it, or review the claim manually.",
            steps=[],
        )

    return AssessmentRead.model_validate(assessment)
