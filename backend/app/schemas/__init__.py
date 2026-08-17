"""Pydantic schemas for request/response validation."""

from app.schemas.assessment_schemas import (
    AssessmentCreate,
    AssessmentRead,
    DamageItemCreate,
    DamageItemRead,
    FraudIndicatorCreate,
    FraudIndicatorRead,
)
from app.schemas.claim_schemas import (
    ClaimCreate,
    ClaimListItem,
    ClaimListResponse,
    ClaimRead,
    ClaimUpdate,
)
from app.schemas.common import APIModel, ORMModel, PaginatedResponse, PaginationMeta
from app.schemas.decision_schemas import DecisionCreate, DecisionRead
from app.schemas.document_schemas import DocumentCreate, DocumentRead
from app.schemas.enums import (
    AssessmentStatus,
    ClaimPriority,
    ClaimStatus,
    CoverageAssessment,
    DamageSeverity,
    DecisionType,
    DocumentType,
    FraudRiskLevel,
    IncidentType,
    IndicatorSeverity,
    PolicyStatus,
    ProcessingStatus,
    RecommendedAction,
    UserRole,
)
from app.schemas.error_schemas import ErrorResponse, FieldError, ValidationErrorResponse
from app.schemas.image_schemas import ImageCreate, ImageRead

__all__ = [
    # Base
    "APIModel",
    "ORMModel",
    "PaginatedResponse",
    "PaginationMeta",
    # Enums
    "AssessmentStatus",
    "ClaimPriority",
    "ClaimStatus",
    "CoverageAssessment",
    "DamageSeverity",
    "DecisionType",
    "DocumentType",
    "FraudRiskLevel",
    "IncidentType",
    "IndicatorSeverity",
    "PolicyStatus",
    "ProcessingStatus",
    "RecommendedAction",
    "UserRole",
    # Claims
    "ClaimCreate",
    "ClaimListItem",
    "ClaimListResponse",
    "ClaimRead",
    "ClaimUpdate",
    # Documents and images
    "DocumentCreate",
    "DocumentRead",
    "ImageCreate",
    "ImageRead",
    # Assessments
    "AssessmentCreate",
    "AssessmentRead",
    "DamageItemCreate",
    "DamageItemRead",
    "FraudIndicatorCreate",
    "FraudIndicatorRead",
    # Decisions
    "DecisionCreate",
    "DecisionRead",
    # Errors
    "ErrorResponse",
    "FieldError",
    "ValidationErrorResponse",
]
