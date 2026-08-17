"""
Gemini client for vehicle damage analysis from photographs.

Gemini is used for the vision work: reading damage from claim photos and
turning it into costed line items.
"""

import asyncio
import base64
import logging
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.services.ai.base import AIError, extract_json

logger = logging.getLogger(__name__)

PROVIDER = "gemini"

_RETRY_STATUS = {408, 429, 500, 502, 503, 504}

DAMAGE_PROMPT = (
    "You are a motor vehicle damage assessor. Examine the photograph and return "
    "ONLY a JSON object with keys: damage_items (array of objects with part_name, "
    "severity as Minor/Moderate/Severe, estimated_repair_cost as a number in INR, "
    "repair_cost_reasoning), overall_severity (Minor/Moderate/Severe), "
    "damage_confidence (integer 0-100). Report only damage you can actually see. "
    "If the image shows no vehicle damage, return an empty damage_items array and "
    "a low damage_confidence."
)

DOCUMENT_PROMPT = (
    "You are transcribing an insurance document from an image. Return ONLY a JSON "
    "object with keys: document_text (the text you can read, preserving line "
    "breaks), legible (true or false). Transcribe only what is actually visible. "
    "Do not infer, complete, or correct field values: a misread policy number is "
    "worse than an omitted one. If the image is too blurred or cropped to read, "
    "set legible to false and document_text to an empty string."
)


class GeminiClient:
    """Vision analysis over the Gemini API."""

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
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.base_url = (base_url or settings.gemini_base_url).rstrip("/")
        self.model = model or settings.gemini_model
        self.timeout = settings.ai_request_timeout_seconds
        self.max_retries = settings.ai_max_retries

    async def analyze_damage_image(
        self, image_bytes: bytes, mime_type: str = "image/jpeg"
    ) -> dict[str, Any]:
        """
        Identify damaged parts and repair costs from a photograph.

        Args:
            image_bytes: Raw image content.
            mime_type: The image's MIME type.

        Returns:
            Keys: damage_items, overall_severity, damage_confidence.

        Raises:
            AIError: If the call fails or the reply cannot be parsed.
        """
        return await self._vision(DAMAGE_PROMPT, image_bytes, mime_type)

    async def read_document_image(
        self, image_bytes: bytes, mime_type: str = "image/jpeg"
    ) -> dict[str, Any]:
        """
        Transcribe a photographed or scanned document.

        Used for image uploads and for PDFs that carry no text layer, which is
        what a scanned policy looks like.

        Args:
            image_bytes: Raw image content.
            mime_type: The image's MIME type.

        Returns:
            Keys: document_text, legible.

        Raises:
            AIError: If the call fails or the reply cannot be parsed.
        """
        return await self._vision(DOCUMENT_PROMPT, image_bytes, mime_type)

    async def _vision(
        self, prompt: str, image_bytes: bytes, mime_type: str
    ) -> dict[str, Any]:
        """
        Send one image plus a prompt and parse the JSON reply.

        Args:
            prompt: Instruction describing the required JSON shape.
            image_bytes: Raw image content.
            mime_type: The image's MIME type.

        Returns:
            The parsed JSON object.

        Raises:
            AIError: If the call fails or the reply cannot be parsed.
        """
        if not self.api_key:
            raise AIError(
                "GEMINI_API_KEY is not configured", provider=PROVIDER, recoverable=False
            )
        if not image_bytes:
            raise AIError("No image content to analyse", provider=PROVIDER, recoverable=False)

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64.b64encode(image_bytes).decode("ascii"),
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        endpoint = f"{self.base_url}/models/{self.model}:generateContent"
        # Sent as a header rather than a query parameter so the key does not
        # appear in request logs or proxy access logs.
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}

        last_error: Optional[str] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(endpoint, json=payload, headers=headers)

                if response.status_code in _RETRY_STATUS:
                    last_error = f"HTTP {response.status_code}"
                    logger.warning(
                        "Gemini call attempt %s/%s failed: %s",
                        attempt,
                        self.max_retries,
                        last_error,
                    )
                    await asyncio.sleep(min(2 ** (attempt - 1), 8))
                    continue

                if response.status_code >= 400:
                    raise AIError(
                        f"Gemini rejected the request (HTTP {response.status_code})",
                        provider=PROVIDER,
                        recoverable=False,
                    )

                body = response.json()
                candidates = body.get("candidates") or []
                if not candidates:
                    # A safety block returns no candidates at all.
                    reason = (body.get("promptFeedback") or {}).get("blockReason", "unknown")
                    raise AIError(
                        f"Gemini returned no candidates (reason: {reason})", provider=PROVIDER
                    )

                parts = candidates[0].get("content", {}).get("parts") or []
                text = "".join(part.get("text", "") for part in parts)
                return extract_json(text, provider=PROVIDER)

            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = type(exc).__name__
                logger.warning(
                    "Gemini call attempt %s/%s failed: %s", attempt, self.max_retries, last_error
                )
                await asyncio.sleep(min(2 ** (attempt - 1), 8))
            except (KeyError, IndexError, ValueError) as exc:
                raise AIError(
                    f"Unexpected Gemini response shape: {exc}", provider=PROVIDER
                ) from exc

        raise AIError(
            f"Gemini unavailable after {self.max_retries} attempts ({last_error})",
            provider=PROVIDER,
        )
