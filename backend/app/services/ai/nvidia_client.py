"""
NVIDIA API client for text analysis of claims.

Uses NVIDIA's OpenAI-compatible chat completions endpoint. Every method asks for
a JSON object and validates what comes back, because a model that returns prose
must not be allowed to write nonsense into the assessment record.
"""

import asyncio
import logging
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.services.ai.base import AIError, extract_json

logger = logging.getLogger(__name__)

PROVIDER = "nvidia"

# Retried because they are transient; anything else fails fast.
_RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


class NVIDIAClient:
    """Text analysis over the NVIDIA inference API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Args:
            api_key: Overrides the configured key.
            base_url: Overrides the configured endpoint.
            model: Overrides the configured model name.
        """
        self.api_key = api_key if api_key is not None else settings.nvidia_api_key
        self.base_url = (base_url or settings.nvidia_base_url).rstrip("/")
        self.model = model or settings.nvidia_model
        self.timeout = settings.ai_request_timeout_seconds
        self.max_retries = settings.ai_max_retries

    async def _chat(self, system: str, user: str, *, max_tokens: int = 1200) -> dict[str, Any]:
        """
        Send a chat completion and parse the JSON reply.

        Args:
            system: System prompt establishing the task.
            user: User message carrying the claim data.
            max_tokens: Ceiling on the reply length.

        Returns:
            The parsed JSON object.

        Raises:
            AIError: If the call fails or the reply cannot be parsed.
        """
        if not self.api_key:
            raise AIError(
                "NVIDIA_API_KEY is not configured", provider=PROVIDER, recoverable=False
            )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            # Low temperature: this is extraction, not composition. Two runs
            # over the same claim should not disagree.
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        last_error: Optional[str] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions", json=payload, headers=headers
                    )

                if response.status_code in _RETRY_STATUS:
                    last_error = f"HTTP {response.status_code}"
                    logger.warning(
                        "NVIDIA call attempt %s/%s failed: %s",
                        attempt,
                        self.max_retries,
                        last_error,
                    )
                    await self._backoff(attempt)
                    continue

                if response.status_code >= 400:
                    # 401/403/404 will not improve on retry.
                    raise AIError(
                        f"NVIDIA rejected the request (HTTP {response.status_code})",
                        provider=PROVIDER,
                        recoverable=False,
                    )

                body = response.json()
                content = body["choices"][0]["message"]["content"]
                return extract_json(content, provider=PROVIDER)

            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = type(exc).__name__
                logger.warning(
                    "NVIDIA call attempt %s/%s failed: %s", attempt, self.max_retries, last_error
                )
                await self._backoff(attempt)
            except (KeyError, IndexError, ValueError) as exc:
                raise AIError(
                    f"Unexpected NVIDIA response shape: {exc}", provider=PROVIDER
                ) from exc

        raise AIError(
            f"NVIDIA unavailable after {self.max_retries} attempts ({last_error})",
            provider=PROVIDER,
        )

    async def _backoff(self, attempt: int) -> None:
        """Sleep between retries, doubling each time."""
        await asyncio.sleep(min(2 ** (attempt - 1), 8))

    async def analyze_claim(self, claim: dict[str, Any]) -> dict[str, Any]:
        """
        Extract structured incident information from the customer's account.

        Args:
            claim: Claim fields including the description.

        Returns:
            Keys: incident_type, collision_type, incident_summary.
        """
        return await self._chat(
            "You are a motor insurance claims analyst. Read the incident report and "
            "return ONLY a JSON object with keys: incident_type (one of Collision, "
            "Theft, Fire, Vandalism, Natural Disaster, Other), collision_type (e.g. "
            "rear-end, side-impact, head-on, single-vehicle, or null), "
            "incident_summary (1-2 factual sentences).",
            _render_claim(claim),
        )

    async def analyze_document(self, text: str, document_type: Optional[str]) -> dict[str, Any]:
        """
        Extract policy fields from a supporting document.

        Args:
            text: Text content of the document.
            document_type: Declared document category, if known.

        Returns:
            Keys: policy_number, policy_status, coverage_type, insured_name,
            valid_from, valid_to.
        """
        return await self._chat(
            "You extract fields from insurance paperwork. Return ONLY a JSON object "
            "with keys: policy_number, policy_status (Active, Expired, Suspended, "
            "Cancelled or Unknown), coverage_type, insured_name, valid_from, valid_to. "
            "Use null for anything not stated. Never guess a value.",
            f"Document type: {document_type or 'Unknown'}\n\n{text[:6000]}",
        )

    async def assess_policy(
        self, claim: dict[str, Any], policy: Optional[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Judge whether the incident falls within policy coverage.

        Args:
            claim: Claim fields.
            policy: Extracted policy data, if a policy document was supplied.

        Returns:
            Keys: policy_status, coverage_assessment, coverage_reasoning,
            coverage_gaps.
        """
        return await self._chat(
            "You assess insurance coverage. Return ONLY a JSON object with keys: "
            "policy_status (Active, Expired, Suspended, Cancelled, Unknown), "
            "coverage_assessment (Likely Covered, Likely Not Covered, Partially "
            "Covered, Undetermined), coverage_reasoning (2-3 sentences), "
            "coverage_gaps (array of strings). If no policy document was provided, "
            "use Undetermined rather than assuming coverage.",
            f"{_render_claim(claim)}\n\nPolicy data: {policy or 'none provided'}",
        )

    async def assess_fraud_risk(self, claim: dict[str, Any]) -> dict[str, Any]:
        """
        Identify fraud indicators in a claim.

        Args:
            claim: Claim fields, including evidence counts.

        Returns:
            Keys: fraud_risk_level, fraud_risk_score, indicators.
        """
        return await self._chat(
            "You are a fraud analyst. Return ONLY a JSON object with keys: "
            "fraud_risk_level (LOW, MEDIUM, HIGH), fraud_risk_score (integer 0-100), "
            "indicators (array of objects with indicator_name, indicator_category, "
            "severity as Low/Medium/High, description, evidence). Flag only what the "
            "provided facts support. An ordinary claim with no red flags is LOW with "
            "an empty indicators array.",
            _render_claim(claim),
        )

    async def generate_claim_summary(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Produce the adjuster-facing summary and recommendation.

        Args:
            context: Claim plus the findings from earlier steps.

        Returns:
            Keys: final_summary, recommended_action, overall_confidence.
        """
        return await self._chat(
            "You brief a claims adjuster. Return ONLY a JSON object with keys: "
            "final_summary (200-400 words, factual, no speculation), "
            "recommended_action (Approve, Request Info, or Escalate), "
            "overall_confidence (integer 0-100). The adjuster decides; you advise.",
            str(context)[:8000],
            max_tokens=1600,
        )


def _render_claim(claim: dict[str, Any]) -> str:
    """Render claim fields as a compact prompt block."""
    lines = [f"{key}: {value}" for key, value in claim.items() if value not in (None, "", [])]
    return "\n".join(lines)
