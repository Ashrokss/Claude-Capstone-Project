"""
Contract tests for the API surface: authentication, authorisation, validation.

These exercise the HTTP layer without a live database. The session dependency is
overridden with a stub, so a route that reaches its body would fail loudly
rather than silently querying nothing; every test here asserts on behaviour that
resolves before the body runs.
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.core.database import get_async_session
from app.main import create_app

JWT_SECRET = "test-secret-not-a-real-supabase-key"
AUDIENCE = "authenticated"
CLAIM_ID = str(uuid4())


@pytest.fixture(autouse=True)
def configured_auth(monkeypatch):
    """Give the app a signing secret so auth paths are exercised."""
    monkeypatch.setattr(settings, "supabase_jwt_secret", JWT_SECRET)
    monkeypatch.setattr(settings, "supabase_jwt_audience", AUDIENCE)


def token(role: str | None = None) -> str:
    """Mint a Supabase-shaped access token."""
    claims = {
        "sub": str(uuid4()),
        "aud": AUDIENCE,
        "email": "adjuster@example.com",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    if role:
        claims["app_metadata"] = {"role": role}
    return jwt.encode(claims, JWT_SECRET, algorithm="HS256")


def auth(role: str | None = None) -> dict:
    """Build an Authorization header for the given role."""
    return {"Authorization": f"Bearer {token(role)}"}


@pytest.fixture
def client():
    """Client with the database session stubbed out."""
    app = create_app()

    async def _stub_session():
        yield AsyncMock()

    app.dependency_overrides[get_async_session] = _stub_session
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


VALID_CLAIM = {
    "customer_name": "Asha Menon",
    "email": "asha@example.com",
    "phone": "+91 98200 11223",
    "vehicle_make": "Maruti Suzuki",
    "vehicle_model": "Baleno",
    "vehicle_year": 2021,
    "registration_number": "MH01AB1234",
    "policy_number": "POL-88213",
    "incident_date": str(date.today()),
    "incident_type": "Collision",
    "incident_description": "Rear-ended at a signal on the Western Express Highway.",
}

PROTECTED = [
    ("post", "/api/claims"),
    ("get", "/api/claims"),
    ("get", f"/api/claims/{CLAIM_ID}"),
    ("patch", f"/api/claims/{CLAIM_ID}"),
    ("post", f"/api/claims/{CLAIM_ID}/analyze"),
    ("get", f"/api/claims/{CLAIM_ID}/assessment"),
    ("post", f"/api/claims/{CLAIM_ID}/decision"),
    ("get", f"/api/claims/{CLAIM_ID}/decision"),
    ("post", f"/api/claims/{CLAIM_ID}/documents"),
    ("post", f"/api/claims/{CLAIM_ID}/images"),
    ("delete", f"/api/claims/{CLAIM_ID}/documents/{uuid4()}"),
    ("delete", f"/api/claims/{CLAIM_ID}/images/{uuid4()}"),
    ("get", "/api/analytics"),
]


class TestEveryRouteRequiresAuth:
    @pytest.mark.parametrize(("method", "path"), PROTECTED)
    def test_anonymous_access_is_refused(self, client, method, path):
        response = getattr(client, method)(path)
        assert response.status_code == 401, f"{method.upper()} {path} was reachable anonymously"
        assert response.json()["error"] == "UNAUTHORIZED"

    @pytest.mark.parametrize(("method", "path"), PROTECTED)
    def test_a_forged_token_is_refused(self, client, method, path):
        forged = jwt.encode(
            {"sub": str(uuid4()), "aud": AUDIENCE,
             "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "wrong-secret",
            algorithm="HS256",
        )
        response = getattr(client, method)(path, headers={"Authorization": f"Bearer {forged}"})
        assert response.status_code == 401


class TestStaffOnlyRoutes:
    """Routes that expose other customers' data, or change claim state."""

    @pytest.mark.parametrize(
        ("method", "path", "body"),
        [
            ("get", "/api/analytics", None),
            ("patch", f"/api/claims/{CLAIM_ID}", {"status": "APPROVED"}),
            (
                "post",
                f"/api/claims/{CLAIM_ID}/decision",
                {"decision": "APPROVED", "reviewer_name": "R. Iyer"},
            ),
        ],
    )
    def test_a_customer_is_forbidden(self, client, method, path, body):
        kwargs = {"json": body} if body else {}
        response = getattr(client, method)(path, headers=auth(), **kwargs)
        assert response.status_code == 403
        assert response.json()["error"] == "FORBIDDEN"

    def test_analytics_admits_a_claims_employee(self, client):
        # Reaches the body, where the stubbed session yields no real rows; the
        # point is that authorisation let it through rather than 403.
        response = client.get("/api/analytics", headers=auth("claims_employee"))
        assert response.status_code != 403


class TestClaimValidation:
    def test_a_valid_payload_passes_validation(self, client):
        response = client.post("/api/claims", json=VALID_CLAIM, headers=auth())
        # Not a 422: the payload cleared validation and reached the handler.
        assert response.status_code != 422

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("email", "not-an-email"),
            ("incident_type", "Meteorite"),
            ("vehicle_year", 1800),
            ("incident_description", "short"),
            ("severity_slider", 9),
        ],
    )
    def test_bad_fields_are_rejected_with_the_field_named(self, client, field, value):
        response = client.post(
            "/api/claims", json={**VALID_CLAIM, field: value}, headers=auth()
        )
        assert response.status_code == 422
        assert field in {e["field"] for e in response.json()["errors"]}

    def test_future_incident_date_is_rejected(self, client):
        payload = {**VALID_CLAIM, "incident_date": str(date.today() + timedelta(days=1))}
        response = client.post("/api/claims", json=payload, headers=auth())
        assert response.status_code == 422

    def test_unknown_field_is_rejected(self, client):
        response = client.post(
            "/api/claims", json={**VALID_CLAIM, "colour": "red"}, headers=auth()
        )
        assert response.status_code == 422


class TestQueryValidation:
    @pytest.mark.parametrize(
        "query",
        ["page=0", "limit=0", "limit=500", "sort_order=sideways", "status=NOPE"],
    )
    def test_bad_query_parameters_are_rejected(self, client, query):
        response = client.get(f"/api/claims?{query}", headers=auth())
        assert response.status_code == 422

    def test_unsortable_column_is_rejected_by_name(self, client):
        # The parameter must never be interpolated into SQL, so it is validated
        # against an allow-list rather than passed through.
        response = client.get("/api/claims?sort_by=password", headers=auth())
        assert response.status_code == 422
        assert "password" in response.text

    @pytest.mark.parametrize("query", ["page=1&limit=20", "sort_by=created_at&sort_order=asc",
                                       "status=PENDING_REVIEW", "fraud_risk=HIGH",
                                       "priority=FAST_TRACK", "search=VC-2026"])
    def test_valid_query_parameters_pass(self, client, query):
        response = client.get(f"/api/claims?{query}", headers=auth("claims_employee"))
        assert response.status_code != 422


class TestDecisionValidation:
    def test_requested_info_without_the_question_is_rejected(self, client):
        response = client.post(
            f"/api/claims/{CLAIM_ID}/decision",
            json={"decision": "REQUESTED_INFO", "reviewer_name": "R. Iyer"},
            headers=auth("claims_employee"),
        )
        assert response.status_code == 422

    def test_escalation_without_notes_is_rejected(self, client):
        response = client.post(
            f"/api/claims/{CLAIM_ID}/decision",
            json={"decision": "ESCALATED", "reviewer_name": "R. Iyer"},
            headers=auth("claims_employee"),
        )
        assert response.status_code == 422

    def test_unknown_decision_type_is_rejected(self, client):
        response = client.post(
            f"/api/claims/{CLAIM_ID}/decision",
            json={"decision": "MAYBE", "reviewer_name": "R. Iyer"},
            headers=auth("claims_employee"),
        )
        assert response.status_code == 422


class TestOpenApiContract:
    def test_every_designed_endpoint_is_published(self, client):
        paths = client.get("/openapi.json").json()["paths"]
        expected = {
            "/api/claims",
            "/api/claims/{claim_id}",
            "/api/claims/{claim_id}/documents",
            "/api/claims/{claim_id}/images",
            "/api/claims/{claim_id}/analyze",
            "/api/claims/{claim_id}/assessment",
            "/api/claims/{claim_id}/decision",
            "/api/analytics",
        }
        assert expected <= set(paths)

    def test_claim_ids_are_uuids_not_free_text(self, client):
        schema = client.get("/openapi.json").json()
        params = schema["paths"]["/api/claims/{claim_id}"]["get"]["parameters"]
        claim_param = next(p for p in params if p["name"] == "claim_id")
        assert claim_param["schema"]["format"] == "uuid"
