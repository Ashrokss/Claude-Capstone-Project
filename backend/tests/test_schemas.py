"""Unit tests for the Pydantic request/response schemas."""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas import (
    AssessmentRead,
    ClaimCreate,
    ClaimRead,
    DecisionCreate,
    DecisionType,
    IncidentType,
    PaginationMeta,
)


def valid_claim_payload(**overrides):
    """Build a minimal valid ClaimCreate payload, with optional overrides."""
    payload = {
        "customer_name": "Asha Menon",
        "email": "asha@example.com",
        "phone": "+91 98200 11223",
        "vehicle_make": "Maruti Suzuki",
        "vehicle_model": "Baleno",
        "vehicle_year": 2021,
        "registration_number": "MH01AB1234",
        "policy_number": "POL-88213",
        "incident_date": date.today() - timedelta(days=3),
        "incident_type": IncidentType.COLLISION,
        "incident_description": "Rear-ended at a signal on the Western Express Highway.",
    }
    payload.update(overrides)
    return payload


class TestClaimCreate:
    def test_accepts_a_valid_payload(self):
        claim = ClaimCreate(**valid_claim_payload())
        assert claim.incident_type is IncidentType.COLLISION
        assert claim.vehicle_year == 2021

    def test_rejects_future_incident_date(self):
        with pytest.raises(ValidationError, match="cannot be in the future"):
            ClaimCreate(**valid_claim_payload(incident_date=date.today() + timedelta(days=1)))

    def test_accepts_incident_dated_today(self):
        claim = ClaimCreate(**valid_claim_payload(incident_date=date.today()))
        assert claim.incident_date == date.today()

    def test_rejects_malformed_email(self):
        with pytest.raises(ValidationError):
            ClaimCreate(**valid_claim_payload(email="not-an-email"))

    def test_rejects_too_short_description(self):
        with pytest.raises(ValidationError):
            ClaimCreate(**valid_claim_payload(incident_description="dented"))

    def test_rejects_unknown_incident_type(self):
        with pytest.raises(ValidationError):
            ClaimCreate(**valid_claim_payload(incident_type="Meteorite"))

    def test_rejects_unknown_field(self):
        # extra="forbid" turns a client typo into a 422 instead of a silent drop.
        with pytest.raises(ValidationError):
            ClaimCreate(**valid_claim_payload(vehicle_colour="red"))

    @pytest.mark.parametrize("year", [1899, date.today().year + 2])
    def test_rejects_implausible_vehicle_year(self, year):
        with pytest.raises(ValidationError):
            ClaimCreate(**valid_claim_payload(vehicle_year=year))

    @pytest.mark.parametrize("slider", [-1, 6])
    def test_rejects_out_of_range_severity(self, slider):
        with pytest.raises(ValidationError):
            ClaimCreate(**valid_claim_payload(severity_slider=slider))

    @pytest.mark.parametrize("slider", [0, 5])
    def test_accepts_severity_bounds(self, slider):
        assert ClaimCreate(**valid_claim_payload(severity_slider=slider)).severity_slider == slider

    def test_damaged_areas_are_trimmed_and_deduplicated(self):
        claim = ClaimCreate(
            **valid_claim_payload(
                damaged_areas=["  Front Bumper ", "Windshield", "Front Bumper", "   ", ""]
            )
        )
        assert claim.damaged_areas == ["Front Bumper", "Windshield"]

    def test_string_whitespace_is_stripped(self):
        claim = ClaimCreate(**valid_claim_payload(customer_name="  Asha Menon  "))
        assert claim.customer_name == "Asha Menon"

    def test_optional_fields_default_to_none(self):
        claim = ClaimCreate(**valid_claim_payload())
        assert claim.incident_time is None
        assert claim.damaged_areas is None
        assert claim.severity_slider is None


class TestDecisionCreate:
    def test_approval_needs_no_extra_context(self):
        decision = DecisionCreate(decision=DecisionType.APPROVED, reviewer_name="R. Iyer")
        assert decision.decision is DecisionType.APPROVED

    def test_requested_info_requires_the_question(self):
        with pytest.raises(ValidationError, match="requested_information is required"):
            DecisionCreate(decision=DecisionType.REQUESTED_INFO, reviewer_name="R. Iyer")

    def test_requested_info_rejects_blank_question(self):
        with pytest.raises(ValidationError, match="requested_information is required"):
            DecisionCreate(
                decision=DecisionType.REQUESTED_INFO,
                reviewer_name="R. Iyer",
                requested_information="   ",
            )

    def test_requested_info_accepts_a_real_question(self):
        decision = DecisionCreate(
            decision=DecisionType.REQUESTED_INFO,
            reviewer_name="R. Iyer",
            requested_information="Please upload the police report.",
        )
        assert decision.requested_information.startswith("Please upload")

    def test_escalation_requires_notes(self):
        with pytest.raises(ValidationError, match="investigation_notes is required"):
            DecisionCreate(decision=DecisionType.ESCALATED, reviewer_name="R. Iyer")

    def test_escalation_accepts_notes(self):
        decision = DecisionCreate(
            decision=DecisionType.ESCALATED,
            reviewer_name="R. Iyer",
            investigation_notes="Damage inconsistent with the described collision.",
        )
        assert decision.decision is DecisionType.ESCALATED


class TestOrmSerialisation:
    def test_claim_read_builds_from_an_orm_style_object(self):
        now = datetime.now(timezone.utc)
        row = SimpleNamespace(
            id=uuid4(),
            claim_number="VC-2026-00042",
            customer_name="Asha Menon",
            email="asha@example.com",
            phone="+91 98200 11223",
            vehicle_make="Maruti Suzuki",
            vehicle_model="Baleno",
            vehicle_year=2021,
            registration_number="MH01AB1234",
            policy_number="POL-88213",
            incident_date=date.today(),
            incident_time=time(14, 30),
            incident_location="Western Express Highway",
            incident_type="Collision",
            incident_description="Rear-ended at a signal.",
            damaged_areas=["Rear Bumper"],
            severity_slider=3,
            damage_notes=None,
            status="PENDING_REVIEW",
            created_at=now,
            updated_at=now,
            created_by_user_id=None,
        )
        claim = ClaimRead.model_validate(row)
        assert claim.claim_number == "VC-2026-00042"
        assert claim.incident_type is IncidentType.COLLISION

    def test_claim_read_rejects_a_malformed_claim_number(self):
        with pytest.raises(ValidationError):
            ClaimRead.model_validate(
                SimpleNamespace(
                    id=uuid4(),
                    claim_number="42",
                    customer_name="A",
                    email="a@example.com",
                    phone="1234567",
                    vehicle_make="M",
                    vehicle_model="B",
                    vehicle_year=2021,
                    registration_number="R",
                    policy_number="P",
                    incident_date=date.today(),
                    incident_type="Collision",
                    incident_description="Rear-ended at a signal.",
                    status="SUBMITTED",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )

    def test_assessment_read_defaults_child_collections_to_empty(self):
        now = datetime.now(timezone.utc)
        assessment = AssessmentRead.model_validate(
            SimpleNamespace(
                id=uuid4(),
                claim_id=uuid4(),
                total_estimated_repair_cost=Decimal("48500.00"),
                fraud_risk_level="LOW",
                fraud_risk_score=12,
                claim_priority="FAST_TRACK",
                assessment_status="COMPLETE",
                created_at=now,
                updated_at=now,
                damage_items=[],
                fraud_indicators=[],
            )
        )
        assert assessment.damage_items == []
        assert assessment.total_estimated_repair_cost == Decimal("48500.00")

    @pytest.mark.parametrize("score", [-1, 101])
    def test_assessment_rejects_out_of_range_confidence(self, score):
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            AssessmentRead.model_validate(
                SimpleNamespace(
                    id=uuid4(),
                    claim_id=uuid4(),
                    fraud_risk_score=score,
                    assessment_status="COMPLETE",
                    created_at=now,
                    updated_at=now,
                    damage_items=[],
                    fraud_indicators=[],
                )
            )


class TestPaginationMeta:
    @pytest.mark.parametrize(
        ("total", "page_size", "expected_pages"),
        [(0, 20, 0), (1, 20, 1), (20, 20, 1), (21, 20, 2), (100, 7, 15)],
    )
    def test_page_count_rounds_up(self, total, page_size, expected_pages):
        meta = PaginationMeta.build(total=total, page=1, page_size=page_size)
        assert meta.total_pages == expected_pages


class TestDecisionReadEmailHandling:
    """
    `reviewer_email` is stored from the identity provider's token, not from a
    client payload, so the read schema must not re-validate it.

    email-validator rejects RFC 2606 reserved TLDs such as .test, so a decision
    recorded by adjuster@vericlaim.test made every later read of that claim
    fail. Validation belongs on the write path, where DecisionCreate applies it.
    """

    def test_a_reserved_tld_reviewer_email_can_be_read_back(self):
        from app.schemas.decision_schemas import DecisionRead

        decision = DecisionRead.model_validate(
            SimpleNamespace(
                id=uuid4(),
                claim_id=uuid4(),
                decision="APPROVED",
                reviewer_name="R. Iyer",
                reviewer_email="adjuster@vericlaim.test",
                reviewer_id=uuid4(),
                decision_comments=None,
                requested_information=None,
                investigation_notes=None,
                created_at=datetime.now(timezone.utc),
            )
        )
        assert decision.reviewer_email == "adjuster@vericlaim.test"

    def test_the_write_path_still_rejects_a_reserved_tld(self):
        # Loosening the read schema must not loosen what a client may submit.
        with pytest.raises(ValidationError):
            DecisionCreate(
                decision=DecisionType.APPROVED,
                reviewer_name="R. Iyer",
                reviewer_email="someone@vericlaim.test",
            )

    def test_the_write_path_still_accepts_a_real_address(self):
        decision = DecisionCreate(
            decision=DecisionType.APPROVED,
            reviewer_name="R. Iyer",
            reviewer_email="adjuster@example.com",
        )
        assert decision.reviewer_email == "adjuster@example.com"
