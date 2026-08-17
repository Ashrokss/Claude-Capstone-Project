"""
In-process background job runner for AI analysis.

Analysis takes tens of seconds across several providers, which is far too long
to hold an HTTP request open, so submission returns immediately and the work
runs here.

This is an in-process queue: jobs live in this worker's memory and are lost if
it restarts. That is an acceptable trade for the MVP because analysis can always
be re-triggered from the claim, and it avoids standing up Redis or Celery. If
analysis ever becomes something that must not be lost, this is the seam to
replace.
"""

import asyncio
import logging
from typing import Optional
from uuid import UUID

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.schemas.enums import AssessmentStatus, ClaimStatus
from app.services import claim_service
from app.services.ai.orchestrator import AIOrchestrator

logger = logging.getLogger(__name__)


class AnalysisQueue:
    """Serialises claim analysis jobs onto a small pool of workers."""

    def __init__(self, concurrency: int = 2):
        """
        Args:
            concurrency: How many analyses may run at once. Kept low because
                each one fans out into several provider calls.
        """
        self._queue: asyncio.Queue[UUID] = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        self._concurrency = concurrency
        self._pending: set[UUID] = set()
        self._orchestrator: Optional[AIOrchestrator] = None

    async def start(self) -> None:
        """Spin up the worker tasks. Called during application startup."""
        if self._workers:
            return
        self._orchestrator = AIOrchestrator()
        self._workers = [
            asyncio.create_task(self._worker(i), name=f"analysis-worker-{i}")
            for i in range(self._concurrency)
        ]
        logger.info("Started %d analysis workers", self._concurrency)

    async def stop(self) -> None:
        """Cancel workers and wait for them to unwind, during shutdown."""
        for task in self._workers:
            task.cancel()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("Analysis workers stopped")

    def is_running(self) -> bool:
        """Return whether workers are currently active."""
        return bool(self._workers)

    async def enqueue_analysis(self, claim_id: UUID) -> bool:
        """
        Queue a claim for analysis.

        Args:
            claim_id: The claim to analyse.

        Returns:
            True if queued, False if that claim is already waiting.
        """
        if claim_id in self._pending:
            logger.info("Claim %s is already queued for analysis", claim_id)
            return False

        self._pending.add(claim_id)
        await self._queue.put(claim_id)
        logger.info("Queued claim %s for analysis (depth=%d)", claim_id, self._queue.qsize())
        return True

    def depth(self) -> int:
        """Return the number of jobs waiting."""
        return self._queue.qsize()

    async def _worker(self, index: int) -> None:
        """Consume claims from the queue until cancelled."""
        while True:
            claim_id = await self._queue.get()
            try:
                await self._run_with_retries(claim_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Analysis worker %d crashed on claim %s", index, claim_id)
            finally:
                self._pending.discard(claim_id)
                self._queue.task_done()

    async def _run_with_retries(self, claim_id: UUID) -> None:
        """
        Run one analysis, retrying transient failures.

        Args:
            claim_id: The claim to analyse.
        """
        attempts = settings.ai_max_retries
        for attempt in range(1, attempts + 1):
            try:
                async with asyncio.timeout(settings.ai_job_timeout_seconds):
                    async with AsyncSessionLocal() as session:
                        await self._orchestrator.analyze_claim(session, claim_id)
                return
            except asyncio.CancelledError:
                raise
            except TimeoutError:
                logger.warning(
                    "Analysis of %s timed out after %ss (attempt %d/%d)",
                    claim_id,
                    settings.ai_job_timeout_seconds,
                    attempt,
                    attempts,
                )
            except Exception:
                logger.exception(
                    "Analysis of %s failed (attempt %d/%d)", claim_id, attempt, attempts
                )

            if attempt < attempts:
                await asyncio.sleep(min(2**attempt, 30))

        await self._mark_failed(claim_id)

    async def _mark_failed(self, claim_id: UUID) -> None:
        """
        Record a terminal analysis failure against the claim.

        Leaving the claim in PROCESSING would strand it invisibly, so it is
        returned to PENDING_REVIEW for a human to pick up.
        """
        try:
            async with AsyncSessionLocal() as session:
                assessment = await claim_service.latest_assessment(session, claim_id)
                if assessment is not None:
                    assessment.assessment_status = AssessmentStatus.FAILED.value
                claim = await claim_service.get_claim(session, claim_id)
                if claim is not None and claim.status == ClaimStatus.PROCESSING.value:
                    await claim_service.update_claim_status(
                        session, claim, ClaimStatus.PENDING_REVIEW, actor="analysis-queue"
                    )
                await session.commit()
            logger.error("Analysis permanently failed for claim %s", claim_id)
        except Exception:
            logger.exception("Could not record analysis failure for claim %s", claim_id)


# Module-level singleton wired into the application lifespan.
analysis_queue = AnalysisQueue()
