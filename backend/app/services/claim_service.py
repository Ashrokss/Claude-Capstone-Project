"""
Claim persistence and query logic.

Endpoints stay thin: they handle HTTP concerns and delegate here, so the same
operations can be reused by background jobs and scripts.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import Select, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Assessment, Claim, HumanDecision
from app.schemas.enums import ClaimStatus, DecisionType

logger = logging.getLogger(__name__)

CLAIM_NUMBER_SEQUENCE = "claim_number_seq"

# Columns a client may sort the dashboard by. Anything else is rejected rather
# than interpolated, so the parameter cannot reach SQL as an arbitrary string.
SORTABLE_COLUMNS = {
    "created_at": Claim.created_at,
    "updated_at": Claim.updated_at,
    "claim_number": Claim.claim_number,
    "customer_name": Claim.customer_name,
    "incident_date": Claim.incident_date,
    "status": Claim.status,
}

# Which claim status each decision drives the claim to.
DECISION_STATUS = {
    DecisionType.APPROVED: ClaimStatus.APPROVED,
    DecisionType.REQUESTED_INFO: ClaimStatus.INFORMATION_REQUIRED,
    DecisionType.ESCALATED: ClaimStatus.INVESTIGATION,
}


async def generate_claim_number(db: AsyncSession, when: Optional[date] = None) -> str:
    """
    Issue the next claim number in VC-YYYY-NNNNN form.

    Args:
        db: Active database session.
        when: Date supplying the year segment; defaults to today.

    Returns:
        A claim number unique across the system.
    """
    year = (when or date.today()).year
    next_value = await db.scalar(select(func.nextval(text(f"'{CLAIM_NUMBER_SEQUENCE}'"))))
    # Wraps past 99999 rather than widening the column; the sequence keeps
    # values distinct, and the year prefix separates the reused suffixes.
    return f"VC-{year}-{int(next_value) % 100000:05d}"


async def create_claim(db: AsyncSession, payload, created_by: Optional[UUID]) -> Claim:
    """
    Persist a new claim in SUBMITTED status.

    Args:
        db: Active database session.
        payload: Validated `ClaimCreate` data.
        created_by: Supabase user id of the submitter, if known.

    Returns:
        The persisted claim.
    """
    claim = Claim(
        claim_number=await generate_claim_number(db),
        status=ClaimStatus.SUBMITTED.value,
        created_by_user_id=created_by,
        **payload.model_dump(),
    )
    db.add(claim)
    await db.flush()
    logger.info(
        "Created claim %s", claim.claim_number, extra={"extra_fields": {"claim_id": str(claim.id)}}
    )
    return claim


async def get_claim(db: AsyncSession, claim_id: UUID) -> Optional[Claim]:
    """
    Fetch a claim by id without its children.

    Args:
        db: Active database session.
        claim_id: Claim primary key.

    Returns:
        The claim, or None if it does not exist.
    """
    return await db.scalar(select(Claim).where(Claim.id == claim_id))


async def get_claim_detail(db: AsyncSession, claim_id: UUID) -> Optional[Claim]:
    """
    Fetch a claim with every related record eagerly loaded.

    Uses `selectinload` so the nested collections arrive in a fixed number of
    queries instead of one per relationship per row.

    Args:
        db: Active database session.
        claim_id: Claim primary key.

    Returns:
        The claim with documents, images, assessments and decisions, or None.
    """
    stmt = (
        select(Claim)
        .where(Claim.id == claim_id)
        .options(
            selectinload(Claim.documents),
            selectinload(Claim.images),
            selectinload(Claim.decisions),
            selectinload(Claim.assessments).selectinload(Assessment.damage_items),
            selectinload(Claim.assessments).selectinload(Assessment.fraud_indicators),
        )
    )
    return await db.scalar(stmt)


async def latest_assessment(db: AsyncSession, claim_id: UUID) -> Optional[Assessment]:
    """
    Fetch the most recent assessment for a claim.

    Args:
        db: Active database session.
        claim_id: Claim primary key.

    Returns:
        The newest assessment with its children, or None.
    """
    stmt = (
        select(Assessment)
        .where(Assessment.claim_id == claim_id)
        .order_by(Assessment.created_at.desc())
        .limit(1)
        .options(
            selectinload(Assessment.damage_items),
            selectinload(Assessment.fraud_indicators),
        )
    )
    return await db.scalar(stmt)


async def latest_decision(db: AsyncSession, claim_id: UUID) -> Optional[HumanDecision]:
    """
    Fetch the most recent human decision for a claim.

    Args:
        db: Active database session.
        claim_id: Claim primary key.

    Returns:
        The newest decision, or None if the claim is undecided.
    """
    stmt = (
        select(HumanDecision)
        .where(HumanDecision.claim_id == claim_id)
        .order_by(HumanDecision.created_at.desc())
        .limit(1)
    )
    return await db.scalar(stmt)


def _apply_filters(
    stmt: Select,
    *,
    status: Optional[str],
    fraud_risk: Optional[str],
    priority: Optional[str],
    search: Optional[str],
    owner_id: Optional[UUID],
) -> Select:
    """
    Attach dashboard filters to a claims query.

    Args:
        stmt: The base select.
        status: Claim status to match.
        fraud_risk: Fraud risk band from the latest assessment.
        priority: Routing priority from the latest assessment.
        search: Free text matched against claim number, customer, or policy.
        owner_id: Restricts results to one submitter.

    Returns:
        The filtered select.
    """
    if status:
        stmt = stmt.where(Claim.status == status)

    if owner_id is not None:
        stmt = stmt.where(Claim.created_by_user_id == owner_id)

    if search:
        # ILIKE is case-insensitive in Postgres; escape the wildcards so a
        # literal % or _ in the search box does not widen the match.
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        stmt = stmt.where(
            or_(
                Claim.claim_number.ilike(pattern),
                Claim.customer_name.ilike(pattern),
                Claim.policy_number.ilike(pattern),
            )
        )

    if fraud_risk or priority:
        # Correlate against the newest assessment only, so a claim is not
        # matched on a superseded run.
        newest = (
            select(Assessment.id)
            .where(Assessment.claim_id == Claim.id)
            .order_by(Assessment.created_at.desc())
            .limit(1)
            .correlate(Claim)
            .scalar_subquery()
        )
        conditions = []
        if fraud_risk:
            conditions.append(Assessment.fraud_risk_level == fraud_risk)
        if priority:
            conditions.append(Assessment.claim_priority == priority)
        stmt = stmt.where(
            select(Assessment.id)
            .where(Assessment.id == newest, *conditions)
            .exists()
        )

    return stmt


async def list_claims(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    fraud_risk: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    owner_id: Optional[UUID] = None,
) -> tuple[Sequence[Claim], int]:
    """
    Page through claims with filtering and sorting.

    Args:
        db: Active database session.
        page: 1-indexed page number.
        page_size: Rows per page.
        status: Claim status filter.
        fraud_risk: Fraud risk filter from the latest assessment.
        priority: Priority filter from the latest assessment.
        search: Free-text search term.
        sort_by: Column key from `SORTABLE_COLUMNS`.
        sort_order: "asc" or "desc".
        owner_id: Restricts results to a single submitter.

    Returns:
        A tuple of (rows for this page, total matching rows).
    """
    column = SORTABLE_COLUMNS.get(sort_by, Claim.created_at)
    ordering = column.asc() if sort_order.lower() == "asc" else column.desc()

    filters = dict(
        status=status,
        fraud_risk=fraud_risk,
        priority=priority,
        search=search,
        owner_id=owner_id,
    )

    total = await db.scalar(
        _apply_filters(select(func.count()).select_from(Claim), **filters)
    )

    stmt = (
        _apply_filters(select(Claim), **filters)
        # Tie-break on id so rows cannot shuffle between pages when the sort
        # column holds duplicates.
        .order_by(ordering, Claim.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.scalars(stmt)).all()
    return rows, int(total or 0)


async def update_claim_status(
    db: AsyncSession, claim: Claim, new_status: ClaimStatus, actor: Optional[str] = None
) -> Claim:
    """
    Move a claim to a new status.

    Args:
        db: Active database session.
        claim: The claim to update.
        new_status: Target status.
        actor: Who initiated the change, for the audit log.

    Returns:
        The updated claim.
    """
    previous = claim.status
    claim.status = new_status.value
    await db.flush()
    logger.info(
        "Claim %s status %s -> %s",
        claim.claim_number,
        previous,
        new_status.value,
        extra={"extra_fields": {"claim_id": str(claim.id), "actor": actor}},
    )
    return claim


async def analytics_snapshot(db: AsyncSession) -> dict:
    """
    Compute the dashboard KPI figures.

    Returns:
        Metric names mapped to their current values.
    """
    total = await db.scalar(select(func.count()).select_from(Claim)) or 0

    pending = (
        await db.scalar(
            select(func.count())
            .select_from(Claim)
            .where(Claim.status == ClaimStatus.PENDING_REVIEW.value)
        )
        or 0
    )

    # Count each claim once even if it has several assessments.
    high_risk = (
        await db.scalar(
            select(func.count(func.distinct(Assessment.claim_id))).where(
                Assessment.fraud_risk_level == "HIGH"
            )
        )
        or 0
    )

    fast_track = (
        await db.scalar(
            select(func.count(func.distinct(Assessment.claim_id))).where(
                Assessment.claim_priority == "FAST_TRACK"
            )
        )
        or 0
    )

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    processed_this_week = (
        await db.scalar(
            select(func.count()).select_from(Claim).where(Claim.updated_at >= week_ago)
        )
        or 0
    )

    # Hours between submission and the first recorded decision.
    avg_hours = await db.scalar(
        select(
            func.avg(
                func.extract("epoch", HumanDecision.created_at - Claim.created_at) / 3600.0
            )
        ).select_from(HumanDecision).join(Claim, Claim.id == HumanDecision.claim_id)
    )

    return {
        "total_claims": int(total),
        "pending_review": int(pending),
        "high_risk_claims": int(high_risk),
        "fast_track_claims": int(fast_track),
        "processed_this_week": int(processed_this_week),
        "average_processing_time_hours": round(float(avg_hours), 2) if avg_hours else None,
    }
