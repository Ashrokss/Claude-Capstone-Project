"""
SQLAlchemy ORM models.

Importing this package registers every table on `Base.metadata`, which is what
Alembic's autogenerate reads. Any new model must be imported here or migrations
will silently omit it.
"""

from app.models.assessment import Assessment, DamageItem, FraudIndicator
from app.models.base import Base, BaseModel
from app.models.claim import Claim
from app.models.decision import HumanDecision
from app.models.evidence import Document, Image

__all__ = [
    "Base",
    "BaseModel",
    "Claim",
    "Document",
    "Image",
    "Assessment",
    "DamageItem",
    "FraudIndicator",
    "HumanDecision",
]
