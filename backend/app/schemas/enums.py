"""
Shared enumerations for VeriClaim AI MVP schemas.

These mirror the CHECK constraints and documented value sets in the database
design. Keeping them in one module means the API contract, the ORM layer and
the migrations all agree on the same vocabulary.
"""

from enum import Enum


class StrEnum(str, Enum):
    """Base for string enums so values serialise as plain strings."""

    def __str__(self) -> str:
        return str(self.value)


class ClaimStatus(StrEnum):
    """Lifecycle state of a claim."""

    SUBMITTED = "SUBMITTED"
    PROCESSING = "PROCESSING"
    PENDING_REVIEW = "PENDING_REVIEW"
    INFORMATION_REQUIRED = "INFORMATION_REQUIRED"
    INVESTIGATION = "INVESTIGATION"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"


class IncidentType(StrEnum):
    """Category of the reported incident."""

    COLLISION = "Collision"
    THEFT = "Theft"
    FIRE = "Fire"
    VANDALISM = "Vandalism"
    NATURAL_DISASTER = "Natural Disaster"
    OTHER = "Other"


class DocumentType(StrEnum):
    """Supporting document category."""

    POLICY = "Policy"
    ACCIDENT_REPORT = "Accident Report"
    REPAIR_ESTIMATE = "Repair Estimate"
    OTHER = "Other"


class ProcessingStatus(StrEnum):
    """Status of an asynchronous extraction or analysis step."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class AssessmentStatus(StrEnum):
    """Status of an AI assessment run."""

    PENDING = "PENDING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class PolicyStatus(StrEnum):
    """Policy state as determined from the uploaded policy document."""

    ACTIVE = "Active"
    EXPIRED = "Expired"
    SUSPENDED = "Suspended"
    CANCELLED = "Cancelled"
    UNKNOWN = "Unknown"


class CoverageAssessment(StrEnum):
    """Whether the incident appears to fall within policy coverage."""

    LIKELY_COVERED = "Likely Covered"
    LIKELY_NOT_COVERED = "Likely Not Covered"
    PARTIALLY_COVERED = "Partially Covered"
    UNDETERMINED = "Undetermined"


class DamageSeverity(StrEnum):
    """Severity of damage to an individual part."""

    MINOR = "Minor"
    MODERATE = "Moderate"
    SEVERE = "Severe"


class FraudRiskLevel(StrEnum):
    """Overall fraud risk band for a claim."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class IndicatorSeverity(StrEnum):
    """Severity of an individual fraud indicator."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ClaimPriority(StrEnum):
    """Routing lane recommended for the claim."""

    FAST_TRACK = "FAST_TRACK"
    STANDARD_REVIEW = "STANDARD_REVIEW"
    INVESTIGATION = "INVESTIGATION"


class RecommendedAction(StrEnum):
    """Action the AI recommends to the human reviewer."""

    APPROVE = "Approve"
    REQUEST_INFO = "Request Info"
    ESCALATE = "Escalate"


class DecisionType(StrEnum):
    """Decision recorded by a human reviewer."""

    APPROVED = "APPROVED"
    REQUESTED_INFO = "REQUESTED_INFO"
    ESCALATED = "ESCALATED"


class UserRole(StrEnum):
    """Authorisation role carried in the Supabase JWT."""

    CUSTOMER = "customer"
    CLAIMS_EMPLOYEE = "claims_employee"
    ADMIN = "admin"
