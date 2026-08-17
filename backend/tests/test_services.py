"""Unit tests for the service layer: AI parsing, routing rules, and storage."""

import io
import json

import httpx
import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.services import storage_service
from app.services.ai.base import AIError, clamp_percent, coerce_decimal, extract_json, pick_enum
from app.services.ai.gemini_client import GeminiClient
from app.services.ai.nvidia_client import NVIDIAClient
from app.services.ai.orchestrator import _classify_priority, _severity_score
from app.models import DamageItem
from app.schemas.enums import ClaimPriority, DamageSeverity, FraudRiskLevel


class TestJsonExtraction:
    def test_parses_a_plain_object(self):
        assert extract_json('{"a": 1}', provider="t") == {"a": 1}

    def test_strips_a_json_fence(self):
        assert extract_json('```json\n{"a": 1}\n```', provider="t") == {"a": 1}

    def test_strips_a_bare_fence(self):
        assert extract_json('```\n{"a": 1}\n```', provider="t") == {"a": 1}

    def test_recovers_an_object_wrapped_in_prose(self):
        raw = 'Sure! Here is the result:\n{"a": 1}\nHope that helps.'
        assert extract_json(raw, provider="t") == {"a": 1}

    @pytest.mark.parametrize("raw", ["", "   ", "no json here", "[1,2,3]", "{broken"])
    def test_unusable_responses_raise_aierror(self, raw):
        # A model returning prose must not surface as a raw ValueError.
        with pytest.raises(AIError):
            extract_json(raw, provider="t")


class TestScoreCoercion:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [(85, 85), ("85", 85), (0.85, 85), (1, 100), (0, 0), (150, 100), (-5, 0)],
    )
    def test_clamps_into_percent_range(self, value, expected):
        # Models return 0.85 for "85%" as often as 85, and sometimes overshoot.
        assert clamp_percent(value) == expected

    @pytest.mark.parametrize("value", [None, "high", "", object()])
    def test_uninterpretable_values_fall_back(self, value):
        assert clamp_percent(value, default=42) == 42

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(1500, 1500.0), ("1500", 1500.0), ("₹1,500.00", 1500.0), (-5, 0.0), ("Rs 48,500", 48500.0)],
    )
    def test_costs_are_coerced_and_floored_at_zero(self, value, expected):
        assert coerce_decimal(value) == expected

    @pytest.mark.parametrize("value", [None, "unknown", "1.2.3", ""])
    def test_uninterpretable_costs_are_none(self, value):
        assert coerce_decimal(value) is None


class TestEnumMapping:
    def test_matches_case_insensitively(self):
        assert pick_enum("high", {"HIGH", "LOW"}) == "HIGH"

    def test_unknown_value_uses_the_default(self):
        assert pick_enum("catastrophic", {"HIGH", "LOW"}, "LOW") == "LOW"

    def test_none_uses_the_default(self):
        assert pick_enum(None, {"HIGH"}, "HIGH") == "HIGH"


class TestPriorityRouting:
    """The routing rules from the design, computed in code so they are auditable."""

    def test_high_fraud_always_investigates(self):
        priority, reason = _classify_priority(fraud_level="HIGH", severity_score=10)
        assert priority == ClaimPriority.INVESTIGATION.value
        assert "fraud" in reason.lower()

    def test_severe_damage_investigates_even_at_low_fraud(self):
        priority, _ = _classify_priority(fraud_level="LOW", severity_score=90)
        assert priority == ClaimPriority.INVESTIGATION.value

    def test_low_fraud_and_light_damage_fast_tracks(self):
        priority, _ = _classify_priority(fraud_level="LOW", severity_score=20)
        assert priority == ClaimPriority.FAST_TRACK.value

    def test_medium_fraud_gets_standard_review(self):
        priority, _ = _classify_priority(fraud_level="MEDIUM", severity_score=40)
        assert priority == ClaimPriority.STANDARD_REVIEW.value

    def test_unknown_fraud_level_does_not_fast_track(self):
        # Absent a fraud verdict, the claim must not skip review.
        priority, _ = _classify_priority(fraud_level=None, severity_score=10)
        assert priority == ClaimPriority.STANDARD_REVIEW.value

    @pytest.mark.parametrize(
        ("severity", "expected_priority"),
        [(76, ClaimPriority.INVESTIGATION.value), (75, ClaimPriority.STANDARD_REVIEW.value)],
    )
    def test_severity_boundary_is_exclusive(self, severity, expected_priority):
        priority, _ = _classify_priority(fraud_level="MEDIUM", severity_score=severity)
        assert priority == expected_priority


class TestSeverityScore:
    def test_uses_the_customer_slider_when_no_damage_items(self):
        assert _severity_score([], 5) == 100
        assert _severity_score([], 0) == 0

    def test_defaults_to_mid_range_with_no_signal(self):
        assert _severity_score([], None) == 50

    def test_severe_damage_dominates_the_score(self):
        items = [
            DamageItem(part_name="Bumper", severity=DamageSeverity.MINOR.value),
            DamageItem(part_name="Chassis", severity=DamageSeverity.SEVERE.value),
        ]
        # A severe item must not be averaged away by minor ones.
        assert _severity_score(items, None) > 75


class TestFilenameSafety:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("photo.jpg", "photo.jpg"),
            ("../../etc/passwd", "passwd"),
            ("..\\..\\windows\\system32", "system32"),
            ("my photo (1).png", "my_photo_1_.png"),
            ("", "upload"),
            ("...", "upload"),
        ],
    )
    def test_traversal_and_odd_characters_are_stripped(self, raw, expected):
        assert storage_service.sanitise_filename(raw) == expected

    def test_long_names_are_truncated(self):
        assert len(storage_service.sanitise_filename("a" * 500)) <= 120

    def test_path_includes_claim_and_kind(self):
        from uuid import uuid4

        claim_id = uuid4()
        path = storage_service.build_path(claim_id, "images", "photo.jpg")
        assert path.startswith(f"claims/{claim_id}/images/")
        assert path.endswith("-photo.jpg")

    def test_two_uploads_of_the_same_name_do_not_collide(self):
        from uuid import uuid4

        claim_id = uuid4()
        a = storage_service.build_path(claim_id, "images", "photo.jpg")
        b = storage_service.build_path(claim_id, "images", "photo.jpg")
        assert a != b


class TestContentTypeDetection:
    @pytest.mark.parametrize(
        ("head", "expected"),
        [
            (b"\xff\xd8\xff\xe0", "image/jpeg"),
            (b"\x89PNG\r\n\x1a\n", "image/png"),
            (b"%PDF-1.7", "application/pdf"),
            (b"MZ\x90\x00", None),
            (b"", None),
        ],
    )
    def test_type_comes_from_magic_bytes(self, head, expected):
        assert storage_service.detect_mime(head, "whatever.jpg") == expected

    @pytest.mark.asyncio
    async def test_executable_renamed_as_jpg_is_rejected(self):
        # The declared extension is not evidence of what the bytes are.
        upload = UploadFile(file=io.BytesIO(b"MZ\x90\x00 evil"), filename="photo.jpg")
        with pytest.raises(HTTPException) as exc:
            await storage_service.validate_upload(
                upload, allowed_mimes={"image/jpeg"}, max_size_mb=5
            )
        assert exc.value.status_code == 415

    @pytest.mark.asyncio
    async def test_oversized_file_is_rejected(self):
        upload = UploadFile(
            file=io.BytesIO(b"\xff\xd8\xff" + b"x" * (2 * 1024 * 1024)), filename="big.jpg"
        )
        with pytest.raises(HTTPException) as exc:
            await storage_service.validate_upload(
                upload, allowed_mimes={"image/jpeg"}, max_size_mb=1
            )
        assert exc.value.status_code == 413

    @pytest.mark.asyncio
    async def test_empty_file_is_rejected(self):
        upload = UploadFile(file=io.BytesIO(b""), filename="empty.jpg")
        with pytest.raises(HTTPException) as exc:
            await storage_service.validate_upload(
                upload, allowed_mimes={"image/jpeg"}, max_size_mb=5
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_valid_jpeg_passes(self):
        upload = UploadFile(file=io.BytesIO(b"\xff\xd8\xff\xe0 body"), filename="ok.jpg")
        payload, mime = await storage_service.validate_upload(
            upload, allowed_mimes={"image/jpeg"}, max_size_mb=5
        )
        assert mime == "image/jpeg"
        assert payload.startswith(b"\xff\xd8\xff")


# Captured before any monkeypatching, so the factory below builds a real client
# instead of recursing into itself.
_RealAsyncClient = httpx.AsyncClient


def _mock_transport(handler):
    """Build an httpx client factory that routes every request to `handler`."""

    def factory(*args, **kwargs):
        kwargs.pop("timeout", None)
        kwargs.pop("transport", None)
        return _RealAsyncClient(transport=httpx.MockTransport(handler), **kwargs)

    return factory


class TestNvidiaClient:
    @pytest.mark.asyncio
    async def test_parses_a_well_formed_response(self, monkeypatch):
        def handler(request):
            assert request.headers["authorization"] == "Bearer test-key"
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": '{"incident_type": "Collision"}'}}]},
            )

        monkeypatch.setattr(httpx, "AsyncClient", _mock_transport(handler))
        client = NVIDIAClient(api_key="test-key")
        result = await client.analyze_claim({"incident_description": "rear-ended"})
        assert result["incident_type"] == "Collision"

    @pytest.mark.asyncio
    async def test_missing_key_fails_without_calling_out(self):
        client = NVIDIAClient(api_key="")
        with pytest.raises(AIError) as exc:
            await client.analyze_claim({})
        assert exc.value.recoverable is False

    @pytest.mark.asyncio
    async def test_auth_failure_is_not_retried(self, monkeypatch):
        calls = []

        def handler(request):
            calls.append(1)
            return httpx.Response(401, json={"error": "bad key"})

        monkeypatch.setattr(httpx, "AsyncClient", _mock_transport(handler))
        with pytest.raises(AIError) as exc:
            await NVIDIAClient(api_key="k").analyze_claim({})
        assert exc.value.recoverable is False
        assert len(calls) == 1  # retrying a bad key just wastes time

    @pytest.mark.asyncio
    async def test_server_error_is_retried_then_gives_up(self, monkeypatch):
        calls = []

        def handler(request):
            calls.append(1)
            return httpx.Response(503)

        monkeypatch.setattr(httpx, "AsyncClient", _mock_transport(handler))
        monkeypatch.setattr("app.services.ai.nvidia_client.settings.ai_max_retries", 2)

        client = NVIDIAClient(api_key="k")
        monkeypatch.setattr(client, "max_retries", 2)
        monkeypatch.setattr(client, "_backoff", lambda attempt: _noop())

        with pytest.raises(AIError):
            await client.analyze_claim({})
        assert len(calls) == 2


async def _noop():
    return None


class TestGeminiClient:
    @pytest.mark.asyncio
    async def test_parses_damage_items(self, monkeypatch):
        def handler(request):
            body = json.loads(request.content)
            # The image must actually be attached.
            assert body["contents"][0]["parts"][1]["inline_data"]["data"]
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"text": '{"damage_items": [{"part_name": "Bumper"}], "damage_confidence": 88}'}
                                ]
                            }
                        }
                    ]
                },
            )

        monkeypatch.setattr(httpx, "AsyncClient", _mock_transport(handler))
        result = await GeminiClient(api_key="k").analyze_damage_image(b"\xff\xd8\xff body")
        assert result["damage_items"][0]["part_name"] == "Bumper"

    @pytest.mark.asyncio
    async def test_safety_block_is_reported_clearly(self, monkeypatch):
        def handler(request):
            return httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}})

        monkeypatch.setattr(httpx, "AsyncClient", _mock_transport(handler))
        with pytest.raises(AIError, match="SAFETY"):
            await GeminiClient(api_key="k").analyze_damage_image(b"\xff\xd8\xff")

    @pytest.mark.asyncio
    async def test_empty_image_fails_without_calling_out(self):
        with pytest.raises(AIError) as exc:
            await GeminiClient(api_key="k").analyze_damage_image(b"")
        assert exc.value.recoverable is False

    @pytest.mark.asyncio
    async def test_key_is_sent_as_a_header_not_a_query_param(self, monkeypatch):
        seen = {}

        def handler(request):
            seen["url"] = str(request.url)
            seen["header"] = request.headers.get("x-goog-api-key")
            return httpx.Response(
                200,
                json={"candidates": [{"content": {"parts": [{"text": "{}"}]}}]},
            )

        monkeypatch.setattr(httpx, "AsyncClient", _mock_transport(handler))
        await GeminiClient(api_key="secret-key").analyze_damage_image(b"\xff\xd8\xff")
        # A key in the URL leaks into proxy and access logs.
        assert "secret-key" not in seen["url"]
        assert seen["header"] == "secret-key"


class TestOrchestratorRobustness:
    """
    The pipeline consumes model output, which is untrusted. Garbage must be
    dropped rather than written into the assessment or crashing the run.
    """

    @pytest.mark.parametrize(
        "raw",
        [None, "not a list", 42, [], [None], ["a string"], [{}], [{"no_name": "x"}]],
    )
    def test_malformed_indicator_payloads_yield_nothing(self, raw):
        from uuid import uuid4
        from app.services.ai.orchestrator import _build_indicators

        assert _build_indicators(uuid4(), raw) == []

    def test_valid_indicators_are_kept_and_invalid_ones_skipped(self):
        from uuid import uuid4
        from app.services.ai.orchestrator import _build_indicators

        result = _build_indicators(
            uuid4(),
            [
                {"indicator_name": "Missing police report", "severity": "High"},
                {"severity": "High"},  # no name, unusable
                {"indicator_name": "Delayed reporting", "severity": "nonsense"},
            ],
        )
        assert [i.indicator_name for i in result] == [
            "Missing police report",
            "Delayed reporting",
        ]
        # An unrecognised severity becomes null rather than failing the CHECK.
        assert result[1].severity is None

    def test_overlong_indicator_name_is_truncated_to_its_column(self):
        from uuid import uuid4
        from app.services.ai.orchestrator import _build_indicators

        result = _build_indicators(uuid4(), [{"indicator_name": "x" * 900}])
        assert len(result[0].indicator_name) == 255

    @pytest.mark.parametrize(
        ("priority", "expected"),
        [
            (ClaimPriority.INVESTIGATION.value, "Escalate"),
            (ClaimPriority.FAST_TRACK.value, "Approve"),
            (ClaimPriority.STANDARD_REVIEW.value, "Request Info"),
            (None, "Request Info"),
        ],
    )
    def test_fallback_action_follows_priority(self, priority, expected):
        from app.services.ai.orchestrator import _fallback_action

        # Used when the summary step fails; the claim still needs a recommendation.
        assert _fallback_action(priority) == expected

    def test_pdf_bytes_are_not_treated_as_text(self):
        from app.services.ai.orchestrator import _decode_text

        assert _decode_text(b"%PDF-1.7 binary junk") is None

    def test_plain_text_document_decodes(self):
        from app.services.ai.orchestrator import _decode_text

        assert "POL-123" in _decode_text(b"Policy Number: POL-123")

    def test_truncate_handles_none_and_blanks(self):
        from app.services.ai.orchestrator import _truncate

        assert _truncate(None, 10) is None
        assert _truncate("   ", 10) is None
        assert _truncate("  hello  ", 3) == "hel"
