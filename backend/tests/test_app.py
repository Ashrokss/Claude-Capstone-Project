"""Integration tests for middleware, error handling, CORS, and authentication."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.core.middleware import REQUEST_ID_HEADER
from app.core.security import CurrentUserDep, require_roles, require_staff
from app.main import create_app
from app.schemas.claim_schemas import ClaimCreate
from app.schemas.enums import UserRole

JWT_SECRET = "test-secret-not-a-real-supabase-key"
AUDIENCE = "authenticated"


@pytest.fixture(autouse=True)
def configured_auth(monkeypatch):
    """Give the app a signing secret so auth paths are exercised, not short-circuited."""
    monkeypatch.setattr(settings, "supabase_jwt_secret", JWT_SECRET)
    monkeypatch.setattr(settings, "supabase_jwt_audience", AUDIENCE)


def make_token(role: str | None = None, sub: str | None = None, expired: bool = False) -> str:
    """Mint a Supabase-shaped access token for tests."""
    now = datetime.now(timezone.utc)
    claims = {
        "sub": sub if sub is not None else str(uuid4()),
        "aud": AUDIENCE,
        "email": "asha@example.com",
        "role": "authenticated",
        "iat": now,
        "exp": now - timedelta(minutes=5) if expired else now + timedelta(hours=1),
    }
    if role is not None:
        claims["app_metadata"] = {"role": role}
    return jwt.encode(claims, JWT_SECRET, algorithm="HS256")


@pytest.fixture
def app() -> FastAPI:
    """App instance with extra routes that exercise the error and auth paths."""
    application = create_app()

    @application.post("/test/claims")
    async def _create_claim(payload: ClaimCreate):
        return {"ok": True, "customer": payload.customer_name}

    @application.get("/test/boom")
    async def _boom():
        raise RuntimeError("database password is hunter2")

    @application.get("/test/teapot")
    async def _teapot():
        raise HTTPException(status_code=404, detail="Claim not found")

    @application.get("/test/me")
    async def _me(user: CurrentUserDep):
        return {"id": str(user.id), "role": user.role.value, "is_staff": user.is_staff}

    @application.get("/test/staff")
    async def _staff(user=Depends(require_staff())):
        return {"role": user.role.value}

    @application.get("/test/admin")
    async def _admin(user=Depends(require_roles(UserRole.ADMIN))):
        return {"role": user.role.value}

    return application


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Client that surfaces 500s as responses so handlers can be asserted on."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestBasics:
    def test_root_and_health_respond(self, client):
        assert client.get("/").status_code == 200
        health = client.get("/health")
        assert health.status_code == 200
        # No database is configured in tests, so it should say so rather than lie.
        assert health.json()["database"] == "disconnected"
        assert health.json()["status"] == "degraded"

    def test_openapi_documents_the_tags(self, client):
        schema = client.get("/openapi.json").json()
        assert {t["name"] for t in schema["tags"]} >= {"Health", "Claims", "Decisions"}


class TestRequestId:
    def test_generates_a_request_id(self, client):
        response = client.get("/health")
        assert response.headers.get(REQUEST_ID_HEADER)

    def test_honours_an_inbound_request_id(self, client):
        response = client.get("/health", headers={REQUEST_ID_HEADER: "trace-abc-123"})
        assert response.headers[REQUEST_ID_HEADER] == "trace-abc-123"

    def test_request_id_appears_in_error_bodies(self, client):
        response = client.get("/test/teapot", headers={REQUEST_ID_HEADER: "trace-xyz"})
        assert response.json()["request_id"] == "trace-xyz"


class TestErrorEnvelope:
    def test_http_exception_uses_the_envelope(self, client):
        response = client.get("/test/teapot")
        assert response.status_code == 404
        body = response.json()
        assert body["error"] == "NOT_FOUND"
        assert body["message"] == "Claim not found"

    def test_unknown_route_uses_the_envelope(self, client):
        body = client.get("/no/such/route").json()
        assert body["error"] == "NOT_FOUND"

    def test_validation_error_lists_offending_fields(self, client):
        response = client.post(
            "/test/claims",
            json={
                "customer_name": "Asha Menon",
                "email": "not-an-email",
                "phone": "+91 98200 11223",
                "vehicle_make": "Maruti",
                "vehicle_model": "Baleno",
                "vehicle_year": 2021,
                "registration_number": "MH01AB1234",
                "policy_number": "POL-1",
                "incident_date": "2026-01-05",
                "incident_type": "Collision",
                "incident_description": "Rear-ended at a signal on the highway.",
            },
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"] == "VALIDATION_ERROR"
        assert "email" in {e["field"] for e in body["errors"]}

    def test_unhandled_exception_does_not_leak_internals(self, client):
        response = client.get("/test/boom")
        assert response.status_code == 500
        body = response.json()
        assert body["error"] == "INTERNAL_ERROR"
        # The secret in the exception message must not reach the client.
        assert "hunter2" not in response.text

    def test_debug_mode_still_hides_secrets_from_the_message_field(self, client):
        body = client.get("/test/boom").json()
        assert body["message"] == "Something went wrong on our end. Please try again."


class TestCors:
    def test_allowed_origin_is_echoed_not_wildcarded(self, client):
        origin = settings.cors_origins[0]
        response = client.get("/health", headers={"Origin": origin})
        allowed = response.headers.get("access-control-allow-origin")
        # A wildcard would be rejected by browsers on credentialed requests.
        assert allowed == origin
        assert allowed != "*"
        assert response.headers.get("access-control-allow-credentials") == "true"

    def test_disallowed_origin_gets_no_cors_grant(self, client):
        response = client.get("/health", headers={"Origin": "https://evil.example"})
        assert response.headers.get("access-control-allow-origin") is None

    def test_preflight_advertises_the_methods(self, client):
        response = client.options(
            "/test/claims",
            headers={
                "Origin": settings.cors_origins[0],
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert response.status_code == 200
        assert "POST" in response.headers.get("access-control-allow-methods", "")


class TestAuthentication:
    def test_missing_token_is_unauthorised(self, client):
        response = client.get("/test/me")
        assert response.status_code == 401
        assert response.json()["error"] == "UNAUTHORIZED"

    def test_garbage_token_is_unauthorised(self, client):
        response = client.get("/test/me", headers={"Authorization": "Bearer not.a.jwt"})
        assert response.status_code == 401

    def test_expired_token_is_unauthorised(self, client):
        response = client.get(
            "/test/me", headers={"Authorization": f"Bearer {make_token(expired=True)}"}
        )
        assert response.status_code == 401

    def test_token_signed_with_the_wrong_secret_is_rejected(self, client):
        forged = jwt.encode(
            {
                "sub": str(uuid4()),
                "aud": AUDIENCE,
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            "the-wrong-secret",
            algorithm="HS256",
        )
        response = client.get("/test/me", headers={"Authorization": f"Bearer {forged}"})
        assert response.status_code == 401

    def test_valid_token_resolves_the_user(self, client):
        user_id = str(uuid4())
        response = client.get(
            "/test/me",
            headers={"Authorization": f"Bearer {make_token(sub=user_id)}"},
        )
        assert response.status_code == 200
        assert response.json()["id"] == user_id

    def test_supabase_authenticated_role_maps_to_customer(self, client):
        # Supabase stamps role="authenticated" on every token; it is not a
        # grant of staff access.
        body = client.get(
            "/test/me", headers={"Authorization": f"Bearer {make_token()}"}
        ).json()
        assert body["role"] == "customer"
        assert body["is_staff"] is False

    def test_app_metadata_role_is_honoured(self, client):
        body = client.get(
            "/test/me",
            headers={"Authorization": f"Bearer {make_token(role='claims_employee')}"},
        ).json()
        assert body["role"] == "claims_employee"
        assert body["is_staff"] is True

    def test_unknown_role_falls_back_to_customer(self, client):
        body = client.get(
            "/test/me",
            headers={"Authorization": f"Bearer {make_token(role='superuser')}"},
        ).json()
        assert body["role"] == "customer"

    def test_non_uuid_subject_is_rejected(self, client):
        response = client.get(
            "/test/me", headers={"Authorization": f"Bearer {make_token(sub='not-a-uuid')}"}
        )
        assert response.status_code == 401


class TestAuthorisation:
    def test_customer_cannot_reach_a_staff_route(self, client):
        response = client.get(
            "/test/staff", headers={"Authorization": f"Bearer {make_token()}"}
        )
        assert response.status_code == 403
        assert response.json()["error"] == "FORBIDDEN"

    def test_claims_employee_can_reach_a_staff_route(self, client):
        response = client.get(
            "/test/staff",
            headers={"Authorization": f"Bearer {make_token(role='claims_employee')}"},
        )
        assert response.status_code == 200

    def test_claims_employee_cannot_reach_an_admin_route(self, client):
        response = client.get(
            "/test/admin",
            headers={"Authorization": f"Bearer {make_token(role='claims_employee')}"},
        )
        assert response.status_code == 403

    def test_admin_can_reach_an_admin_route(self, client):
        response = client.get(
            "/test/admin", headers={"Authorization": f"Bearer {make_token(role='admin')}"}
        )
        assert response.status_code == 200


class TestFailClosed:
    def test_missing_jwt_secret_rejects_rather_than_admits(self, client, monkeypatch):
        # If the secret is absent the app must not fall back to trusting tokens.
        monkeypatch.setattr(settings, "supabase_jwt_secret", "")
        response = client.get(
            "/test/me", headers={"Authorization": f"Bearer {make_token()}"}
        )
        assert response.status_code == 500
        assert response.status_code != 200


class TestLoopbackCorsAliases:
    """
    A browser treats localhost and 127.0.0.1 as different origins.

    Opening the app on the spelling the operator did not configure blocked every
    API call at the preflight, surfacing as an opaque "Failed to fetch". They
    reach the same machine, so all loopback spellings of a configured loopback
    origin are accepted.
    """

    def test_localhost_origin_expands_to_its_aliases(self, monkeypatch):
        monkeypatch.setattr(settings, "frontend_url", "http://localhost:3000")
        monkeypatch.setattr(settings, "extra_cors_origins", "")
        assert set(settings.cors_origins) == {
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://[::1]:3000",
        }

    def test_expansion_works_from_the_other_spelling_too(self, monkeypatch):
        monkeypatch.setattr(settings, "frontend_url", "http://127.0.0.1:3000")
        monkeypatch.setattr(settings, "extra_cors_origins", "")
        assert "http://localhost:3000" in settings.cors_origins

    def test_the_port_is_preserved(self, monkeypatch):
        monkeypatch.setattr(settings, "frontend_url", "http://localhost:4321")
        monkeypatch.setattr(settings, "extra_cors_origins", "")
        assert "http://127.0.0.1:4321" in settings.cors_origins
        assert "http://127.0.0.1:3000" not in settings.cors_origins

    def test_a_public_domain_is_not_expanded(self, monkeypatch):
        # Only loopback is aliased; a real host must not gain extra origins.
        monkeypatch.setattr(settings, "frontend_url", "https://claims.example.com")
        monkeypatch.setattr(settings, "extra_cors_origins", "")
        assert settings.cors_origins == ["https://claims.example.com"]

    def test_scheme_is_preserved(self, monkeypatch):
        monkeypatch.setattr(settings, "frontend_url", "https://localhost:3000")
        monkeypatch.setattr(settings, "extra_cors_origins", "")
        assert all(o.startswith("https://") for o in settings.cors_origins)

    def test_extra_origins_are_expanded_as_well(self, monkeypatch):
        monkeypatch.setattr(settings, "frontend_url", "http://localhost:3000")
        monkeypatch.setattr(settings, "extra_cors_origins", "http://localhost:4000")
        assert "http://127.0.0.1:4000" in settings.cors_origins

    def test_a_malformed_origin_does_not_raise(self, monkeypatch):
        monkeypatch.setattr(settings, "frontend_url", "not a url")
        monkeypatch.setattr(settings, "extra_cors_origins", "")
        assert settings.cors_origins == ["not a url"]

    def test_the_preflight_is_granted_from_both_spellings(self, client, monkeypatch):
        for origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
            response = client.options(
                "/api/claims",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "authorization",
                },
            )
            assert response.status_code == 200, origin
            assert response.headers.get("access-control-allow-origin") == origin
