"""
Shared helpers for AI provider clients.

Language models return prose even when asked for JSON, so parsing is defensive:
fenced blocks are stripped, and a failure to parse is reported as a typed error
rather than propagating a ValueError from deep inside a client.
"""

import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Matches ```json ... ``` or ``` ... ``` wrappers around a payload.
_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


class AIError(RuntimeError):
    """Raised when a provider call fails or returns something unusable."""

    def __init__(self, message: str, *, provider: str, recoverable: bool = True):
        super().__init__(message)
        self.provider = provider
        self.recoverable = recoverable


def extract_json(raw: str, *, provider: str) -> dict[str, Any]:
    """
    Parse a JSON object out of a model response.

    Args:
        raw: The raw text returned by the model.
        provider: Provider name, for error reporting.

    Returns:
        The parsed object.

    Raises:
        AIError: If no JSON object can be recovered.
    """
    if not raw or not raw.strip():
        raise AIError("Model returned an empty response", provider=provider)

    text = raw.strip()

    fenced = _FENCE.match(text)
    if fenced:
        text = fenced.group(1).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Fall back to the outermost braces, which handles a model that wrapped
        # the object in a sentence.
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            logger.warning("%s returned no JSON object: %r", provider, text[:200])
            raise AIError("Model response was not valid JSON", provider=provider)
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            logger.warning("%s returned malformed JSON: %r", provider, text[:200])
            raise AIError("Model response was not valid JSON", provider=provider)

    if not isinstance(parsed, dict):
        raise AIError("Model response was not a JSON object", provider=provider)

    return parsed


def clamp_percent(value: Any, default: Optional[int] = None) -> Optional[int]:
    """
    Coerce a model-supplied score into 0-100.

    Models routinely return 0.85 for "85%" or overshoot the range entirely, and
    the database has a CHECK constraint that would reject either.

    Args:
        value: The raw value from the model.
        default: Returned when the value cannot be interpreted.

    Returns:
        An integer between 0 and 100, or the default.
    """
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default

    # A confidence expressed as a fraction.
    if 0 < number <= 1:
        number *= 100

    return max(0, min(100, int(round(number))))


def coerce_decimal(value: Any) -> Optional[float]:
    """
    Coerce a model-supplied cost into a non-negative number.

    Args:
        value: The raw value, possibly a string with currency formatting.

    Returns:
        A float, or None if it cannot be interpreted.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return max(0.0, float(value))

    cleaned = re.sub(r"[^0-9.]", "", str(value))
    if not cleaned or cleaned.count(".") > 1:
        return None
    try:
        return max(0.0, float(cleaned))
    except ValueError:
        return None


def pick_enum(value: Any, allowed: set[str], default: Optional[str] = None) -> Optional[str]:
    """
    Map a model-supplied label onto a permitted value.

    Args:
        value: The raw label.
        allowed: Values the database will accept.
        default: Returned when no match is found.

    Returns:
        A permitted value, or the default.
    """
    if value is None:
        return default

    candidate = str(value).strip()
    for option in allowed:
        if candidate.lower() == option.lower():
            return option
    return default
