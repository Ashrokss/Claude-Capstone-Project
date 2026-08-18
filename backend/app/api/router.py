"""
Aggregate API router.

Route order matters: `claims.py` owns `/claims/{claim_id}` while the evidence,
assessment and decision routers mount sub-paths beneath it. The sub-path routers
are registered first so their concrete segments are matched before the
`{claim_id}` catch-all.
"""

from fastapi import APIRouter

from app.api.endpoints import analytics, assessment, claims, decisions, evidence

api_router = APIRouter(prefix="/api")

api_router.include_router(evidence.router)
api_router.include_router(assessment.router)
api_router.include_router(decisions.router)
api_router.include_router(claims.router)
api_router.include_router(analytics.router)

__all__ = ["api_router"]
