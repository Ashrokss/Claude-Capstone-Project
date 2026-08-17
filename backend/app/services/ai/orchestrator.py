"""
Coordinates the AI analysis of a claim.

The pipeline is deliberately fault-tolerant: each step is independent, and a
provider failure degrades that step to null rather than losing the whole
assessment. An adjuster is better served by a partial analysis with visible gaps
than by an error page.

Priority classification is computed here in code, not asked of a model, because
it drives routing and must be reproducible and auditable.
"""

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Assessment, Claim, DamageItem, FraudIndicator
from app.schemas.enums import (
    AssessmentStatus,
    ClaimPriority,
    ClaimStatus,
    CoverageAssessment,
    DamageSeverity,
    FraudRiskLevel,
    IndicatorSeverity,
    PolicyStatus,
    RecommendedAction,
)
from app.services import claim_service, storage_service
from app.services.ai.base import AIError, clamp_percent, coerce_decimal, pick_enum
from app.services.ai.gemini_client import GeminiClient
from app.services.ai.nvidia_client import NVIDIAClient

logger = logging.getLogger(__name__)

# Thresholds for the routing rules in the design.
_HIGH_SEVERITY = 75
_LOW_SEVERITY = 50


class AIOrchestrator:
    """Runs the multi-step analysis and persists the result."""

    def __init__(
        self, nvidia: Optional[NVIDIAClient] = None, gemini: Optional[GeminiClient] = None
    ):
        """
        Args:
            nvidia: Text analysis client; constructed from settings if omitted.
            gemini: Vision client; constructed from settings if omitted.
        """
        self.nvidia = nvidia or NVIDIAClient()
        self.gemini = gemini or GeminiClient()

    async def analyze_claim(self, db: AsyncSession, claim_id: UUID) -> Optional[Assessment]:
        """
        Run the full analysis for a claim and store the assessment.

        Args:
            db: Active database session.
            claim_id: The claim to analyse.

        Returns:
            The persisted assessment, or None if the claim no longer exists.
        """
        claim = await claim_service.get_claim_detail(db, claim_id)
        if claim is None:
            logger.warning("Analysis requested for unknown claim %s", claim_id)
            return None

        assessment = Assessment(
            claim_id=claim.id, assessment_status=AssessmentStatus.PENDING.value
        )
        db.add(assessment)
        await db.flush()

        await claim_service.update_claim_status(
            db, claim, ClaimStatus.PROCESSING, actor="ai-orchestrator"
        )
        await db.commit()

        failures: list[str] = []
        context = _claim_context(claim)

        # 1. Extract structured incident information.
        extraction = await self._step("analyze_claim", failures, self.nvidia.analyze_claim, context)
        if extraction:
            assessment.extracted_incident_type = _truncate(extraction.get("incident_type"), 50)
            assessment.extracted_collision_type = _truncate(extraction.get("collision_type"), 50)
            assessment.incident_summary = extraction.get("incident_summary")

        # 2. Documents.
        policy_data = await self._analyze_documents(claim, failures)

        # 3. Images.
        damage_items, damage_confidence = await self._analyze_images(claim, failures)

        # 4. Policy coverage.
        coverage = await self._step(
            "assess_policy", failures, self.nvidia.assess_policy, context, policy_data
        )
        if coverage:
            assessment.policy_status = pick_enum(
                coverage.get("policy_status"),
                {s.value for s in PolicyStatus},
                PolicyStatus.UNKNOWN.value,
            )
            assessment.coverage_assessment = pick_enum(
                coverage.get("coverage_assessment"),
                {c.value for c in CoverageAssessment},
                CoverageAssessment.UNDETERMINED.value,
            )
            assessment.coverage_reasoning = coverage.get("coverage_reasoning")
            gaps = coverage.get("coverage_gaps")
            assessment.coverage_gaps = [str(g) for g in gaps] if isinstance(gaps, list) else None

        # 5. Fraud risk.
        fraud = await self._step(
            "assess_fraud_risk", failures, self.nvidia.assess_fraud_risk, context
        )
        indicators: list[FraudIndicator] = []
        if fraud:
            assessment.fraud_risk_level = pick_enum(
                fraud.get("fraud_risk_level"),
                {f.value for f in FraudRiskLevel},
                FraudRiskLevel.LOW.value,
            )
            assessment.fraud_risk_score = clamp_percent(fraud.get("fraud_risk_score"), 0)
            indicators = _build_indicators(assessment.id, fraud.get("indicators"))

        # Damage totals.
        assessment.damage_confidence = damage_confidence
        if damage_items:
            total = sum(
                float(item.estimated_repair_cost or 0) for item in damage_items
            )
            assessment.total_estimated_repair_cost = round(total, 2) if total else None

        # 6. Priority, computed in code so routing is deterministic.
        assessment.claim_priority, assessment.priority_reasoning = _classify_priority(
            fraud_level=assessment.fraud_risk_level,
            severity_score=_severity_score(damage_items, claim.severity_slider),
        )

        # 7. Adjuster-facing summary.
        summary = await self._step(
            "generate_claim_summary",
            failures,
            self.nvidia.generate_claim_summary,
            {
                **context,
                "coverage": coverage,
                "fraud": fraud,
                "damage_items": [
                    {"part": d.part_name, "severity": d.severity, "cost": float(d.estimated_repair_cost or 0)}
                    for d in damage_items
                ],
                "priority": assessment.claim_priority,
            },
        )
        if summary:
            assessment.final_summary = summary.get("final_summary")
            assessment.recommended_action = pick_enum(
                summary.get("recommended_action"),
                {r.value for r in RecommendedAction},
            )
            assessment.overall_confidence = clamp_percent(summary.get("overall_confidence"))

        if assessment.recommended_action is None:
            assessment.recommended_action = _fallback_action(assessment.claim_priority)

        for item in damage_items:
            item.assessment_id = assessment.id
            db.add(item)
        for indicator in indicators:
            db.add(indicator)

        # A run that produced nothing at all is a failure; partial results are
        # still worth showing, with the gaps visible.
        produced_nothing = len(failures) >= 5
        assessment.assessment_status = (
            AssessmentStatus.FAILED.value if produced_nothing else AssessmentStatus.COMPLETE.value
        )

        await claim_service.update_claim_status(
            db, claim, ClaimStatus.PENDING_REVIEW, actor="ai-orchestrator"
        )
        await db.commit()

        logger.info(
            "Assessment %s for claim %s finished as %s (%d step failures)",
            assessment.id,
            claim.claim_number,
            assessment.assessment_status,
            len(failures),
            extra={"extra_fields": {"claim_id": str(claim.id), "failed_steps": failures}},
        )
        return assessment

    async def _step(self, name: str, failures: list[str], func, *args) -> Optional[dict[str, Any]]:
        """
        Run one pipeline step, recording rather than raising on failure.

        Args:
            name: Step name for logging.
            failures: Accumulator of failed step names.
            func: The client coroutine to call.
            *args: Arguments forwarded to the call.

        Returns:
            The step's result, or None if it failed.
        """
        try:
            return await func(*args)
        except AIError as exc:
            failures.append(name)
            logger.warning("AI step %s failed: %s", name, exc)
        except Exception:
            failures.append(name)
            logger.exception("AI step %s raised unexpectedly", name)
        return None

    async def _analyze_documents(
        self, claim: Claim, failures: list[str]
    ) -> Optional[dict[str, Any]]:
        """
        Extract policy data from the claim's documents.

        Args:
            claim: Claim with its documents loaded.
            failures: Accumulator of failed step names.

        Returns:
            Extracted policy fields from the first document that yielded any.
        """
        policy_data: Optional[dict[str, Any]] = None

        for document in claim.documents:
            content = await storage_service.download(document.file_path)
            if content is None:
                document.extraction_status = "FAILED"
                document.extraction_error = "File could not be retrieved from storage"
                continue

            # PDFs are not text-extracted here; that needs a parser and is out
            # of scope for the MVP. Images of documents go to the vision model.
            text = _decode_text(content)
            if not text:
                document.extraction_status = "FAILED"
                document.extraction_error = "No extractable text in this document"
                continue

            result = await self._step(
                f"analyze_document:{document.id}",
                failures,
                self.nvidia.analyze_document,
                text,
                document.document_type,
            )
            if result is None:
                document.extraction_status = "FAILED"
                document.extraction_error = "Document analysis failed"
                continue

            document.extracted_data = result
            document.extraction_status = "SUCCESS"
            document.extraction_error = None
            if policy_data is None and result.get("policy_number"):
                policy_data = result

        return policy_data

    async def _analyze_images(
        self, claim: Claim, failures: list[str]
    ) -> tuple[list[DamageItem], Optional[int]]:
        """
        Run damage analysis over every image on the claim.

        Args:
            claim: Claim with its images loaded.
            failures: Accumulator of failed step names.

        Returns:
            A tuple of (damage items, mean confidence across analysed images).
        """
        items: list[DamageItem] = []
        confidences: list[int] = []

        for image in claim.images:
            content = await storage_service.download(image.file_path)
            if content is None:
                image.analysis_status = "FAILED"
                image.analysis_error = "File could not be retrieved from storage"
                continue

            result = await self._step(
                f"analyze_image:{image.id}",
                failures,
                self.gemini.analyze_damage_image,
                content,
                image.mime_type or "image/jpeg",
            )
            if result is None:
                image.analysis_status = "FAILED"
                image.analysis_error = "Damage analysis failed"
                continue

            image.analysis_status = "SUCCESS"
            image.analysis_error = None
            image.analyzed = True

            confidence = clamp_percent(result.get("damage_confidence"))
            if confidence is not None:
                confidences.append(confidence)

            for raw in result.get("damage_items") or []:
                if not isinstance(raw, dict) or not raw.get("part_name"):
                    continue
                items.append(
                    DamageItem(
                        part_name=_truncate(raw.get("part_name"), 255),
                        severity=pick_enum(
                            raw.get("severity"), {s.value for s in DamageSeverity}
                        ),
                        estimated_repair_cost=coerce_decimal(raw.get("estimated_repair_cost")),
                        repair_cost_reasoning=raw.get("repair_cost_reasoning"),
                    )
                )

        mean_confidence = round(sum(confidences) / len(confidences)) if confidences else None
        return items, mean_confidence


def _claim_context(claim: Claim) -> dict[str, Any]:
    """Build the prompt context describing a claim."""
    return {
        "claim_number": claim.claim_number,
        "incident_type": claim.incident_type,
        "incident_date": str(claim.incident_date),
        "incident_time": str(claim.incident_time) if claim.incident_time else None,
        "incident_location": claim.incident_location,
        "incident_description": claim.incident_description,
        "damaged_areas": claim.damaged_areas,
        "customer_severity_rating": claim.severity_slider,
        "damage_notes": claim.damage_notes,
        "vehicle": f"{claim.vehicle_year} {claim.vehicle_make} {claim.vehicle_model}",
        "policy_number": claim.policy_number,
        "submitted_at": str(claim.created_at),
        "documents_supplied": len(claim.documents),
        "images_supplied": len(claim.images),
    }


def _severity_score(items: list[DamageItem], slider: Optional[int]) -> int:
    """
    Derive a 0-100 severity score for routing.

    Uses the assessed damage where available and falls back to the customer's
    own rating, which is the only signal present before any photo is analysed.

    Args:
        items: Damage items from the vision step.
        slider: The customer's 0-5 severity rating.

    Returns:
        A score between 0 and 100.
    """
    if items:
        weights = {
            DamageSeverity.MINOR.value: 25,
            DamageSeverity.MODERATE.value: 60,
            DamageSeverity.SEVERE.value: 95,
        }
        scores = [weights.get(item.severity or "", 50) for item in items]
        return round(max(scores) * 0.7 + (sum(scores) / len(scores)) * 0.3)

    if slider is not None:
        return int(slider / 5 * 100)

    return 50


def _classify_priority(
    *, fraud_level: Optional[str], severity_score: int
) -> tuple[str, str]:
    """
    Route the claim according to the design's rules.

    Args:
        fraud_level: Assessed fraud risk band.
        severity_score: Derived 0-100 severity.

    Returns:
        A tuple of (priority, human-readable reasoning).
    """
    if fraud_level == FraudRiskLevel.HIGH.value or severity_score > _HIGH_SEVERITY:
        reason = (
            "High fraud risk flagged"
            if fraud_level == FraudRiskLevel.HIGH.value
            else f"Assessed damage severity {severity_score}/100 exceeds the fast-track range"
        )
        return ClaimPriority.INVESTIGATION.value, reason

    if fraud_level == FraudRiskLevel.LOW.value and severity_score < _LOW_SEVERITY:
        return (
            ClaimPriority.FAST_TRACK.value,
            f"Low fraud risk and limited damage (severity {severity_score}/100)",
        )

    return (
        ClaimPriority.STANDARD_REVIEW.value,
        f"Fraud risk {fraud_level or 'unknown'} with severity {severity_score}/100",
    )


def _fallback_action(priority: Optional[str]) -> str:
    """Recommend an action when the summary step did not produce one."""
    if priority == ClaimPriority.INVESTIGATION.value:
        return RecommendedAction.ESCALATE.value
    if priority == ClaimPriority.FAST_TRACK.value:
        return RecommendedAction.APPROVE.value
    return RecommendedAction.REQUEST_INFO.value


def _build_indicators(assessment_id: UUID, raw: Any) -> list[FraudIndicator]:
    """Convert model-supplied fraud indicators into ORM rows."""
    if not isinstance(raw, list):
        return []

    indicators = []
    for entry in raw:
        if not isinstance(entry, dict) or not entry.get("indicator_name"):
            continue
        indicators.append(
            FraudIndicator(
                assessment_id=assessment_id,
                indicator_name=_truncate(entry.get("indicator_name"), 255),
                indicator_category=_truncate(entry.get("indicator_category"), 100),
                severity=pick_enum(
                    entry.get("severity"), {s.value for s in IndicatorSeverity}
                ),
                description=entry.get("description"),
                evidence=entry.get("evidence"),
            )
        )
    return indicators


def _decode_text(content: bytes) -> Optional[str]:
    """Decode document bytes as text, if they are text at all."""
    if content[:5] == b"%PDF-":
        return None
    try:
        text = content.decode("utf-8", errors="ignore").strip()
    except Exception:
        return None
    return text or None


def _truncate(value: Any, length: int) -> Optional[str]:
    """Trim a model-supplied string to fit its column."""
    if value is None:
        return None
    text = str(value).strip()
    return text[:length] if text else None
