"""
Request and response schemas for claims.

Field constraints mirror the column definitions in the database design so that
validation fails at the API boundary rather than at the database.
"""

from datetime import date, datetime, time
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import APIModel, ORMModel, PaginationMeta
from app.schemas.enums import ClaimStatus, IncidentType

# Claim numbers are issued as VC-YYYY-NNNNN.
CLAIM_NUMBER_PATTERN = r"^VC-\d{4}-\d{5}$"

# Oldest vehicle year accepted on a motor claim.
MIN_VEHICLE_YEAR = 1900


class ClaimBase(APIModel):
    """Fields supplied by the customer when reporting an incident."""

    # Customer
    customer_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr = Field(..., max_length=255)
    phone: str = Field(..., min_length=5, max_length=20)

    # Vehicle
    vehicle_make: str = Field(..., min_length=1, max_length=100)
    vehicle_model: str = Field(..., min_length=1, max_length=100)
    vehicle_year: int = Field(..., ge=MIN_VEHICLE_YEAR)
    registration_number: str = Field(..., min_length=1, max_length=50)

    # Policy and incident
    policy_number: str = Field(..., min_length=1, max_length=50)
    incident_date: date
    incident_time: Optional[time] = None
    incident_location: Optional[str] = Field(None, max_length=500)
    incident_type: IncidentType
    incident_description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Customer's account of what happened",
    )

    # Damage detail
    damaged_areas: Optional[list[str]] = Field(
        None, description='Selected areas, e.g. ["Front Bumper", "Windshield"]'
    )
    severity_slider: Optional[int] = Field(
        None, ge=0, le=5, description="Customer's own severity rating, 0-5"
    )
    damage_notes: Optional[str] = Field(None, max_length=5000)

    @field_validator("incident_date")
    @classmethod
    def incident_not_in_future(cls, value: date) -> date:
        """Reject incidents dated in the future."""
        if value > date.today():
            raise ValueError("incident_date cannot be in the future")
        return value

    @field_validator("vehicle_year")
    @classmethod
    def vehicle_year_plausible(cls, value: int) -> int:
        """Reject model years beyond next year's models."""
        if value > date.today().year + 1:
            raise ValueError(f"vehicle_year cannot be later than {date.today().year + 1}")
        return value

    @field_validator("damaged_areas")
    @classmethod
    def clean_damaged_areas(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        """Drop blank entries and de-duplicate while preserving order."""
        if value is None:
            return None
        seen: dict[str, None] = {}
        for area in value:
            cleaned = area.strip()
            if cleaned:
                seen.setdefault(cleaned, None)
        return list(seen)


class ClaimCreate(ClaimBase):
    """Payload for `POST /api/claims`."""


class ClaimUpdate(APIModel):
    """
    Payload for `PATCH /api/claims/{claim_id}`.

    Every field is optional; only the keys present are applied.
    """

    status: Optional[ClaimStatus] = None
    incident_location: Optional[str] = Field(None, max_length=500)
    incident_description: Optional[str] = Field(None, min_length=10, max_length=5000)
    damaged_areas: Optional[list[str]] = None
    severity_slider: Optional[int] = Field(None, ge=0, le=5)
    damage_notes: Optional[str] = Field(None, max_length=5000)

    @field_validator("status")
    @classmethod
    def status_is_known(cls, value: Optional[ClaimStatus]) -> Optional[ClaimStatus]:
        """Guard against a null status being written over a real one."""
        if value is None:
            return None
        return value


class ClaimRead(ORMModel):
    """Full claim representation returned by the API."""

    id: UUID
    claim_number: str = Field(..., pattern=CLAIM_NUMBER_PATTERN)

    customer_name: str
    email: EmailStr
    phone: str

    vehicle_make: str
    vehicle_model: str
    vehicle_year: int
    registration_number: str

    policy_number: str
    incident_date: date
    incident_time: Optional[time] = None
    incident_location: Optional[str] = None
    incident_type: IncidentType
    incident_description: str

    damaged_areas: Optional[list[str]] = None
    severity_slider: Optional[int] = None
    damage_notes: Optional[str] = None

    status: ClaimStatus
    created_at: datetime
    updated_at: datetime
    created_by_user_id: Optional[UUID] = None


class ClaimListItem(ORMModel):
    """Condensed claim row for the adjuster dashboard table."""

    id: UUID
    claim_number: str
    customer_name: str
    vehicle_make: str
    vehicle_model: str
    vehicle_year: int
    incident_type: IncidentType
    incident_date: date
    status: ClaimStatus
    created_at: datetime


class ClaimListResponse(ORMModel):
    """Paginated response for `GET /api/claims`."""

    items: list[ClaimListItem] = Field(default_factory=list)
    pagination: PaginationMeta
