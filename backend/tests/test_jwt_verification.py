"""
Tests for Supabase access token verification.

Supabase projects sign either with asymmetric keys published via JWKS (newer
projects, typically ES256) or a shared HS256 secret (older ones). Both paths are
covered here, along with the confusion attack that the split invites.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from jose import jwt
from jose.utils import base64url_encode

from app.core import security
from app.core.config import settings

AUDIENCE = "authenticated"
KID = "test-signing-key"

_RealAsyncClient = httpx.AsyncClient


@pytest.fixture
def ec_keypair():
    """An EC P-256 keypair plus its JWK, mirroring a Supabase signing key."""
    private = ec.generate_private_key(ec.SECP256R1())
    numbers = private.public_key().public_numbers()

    def encode(value: int) -> str:
        return base64url_encode(value.to_bytes(32, "big")).decode()

    jwk = {
        "kty": "EC",
        "crv": "P-256",
        "alg": "ES256",
        "use": "sig",
        "kid": KID,
        "x": encode(numbers.x),
        "y": encode(numbers.y),
    }
    pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    return pem, jwk


@pytest.fixture(autouse=True)
def reset_jwks_cache():
    """Keep the module-level JWKS cache from leaking between tests."""
    security._jwks_cache["keys"] = []
    security._jwks_cache["fetched_at"] = 0.0
    yield
    security._jwks_cache["keys"] = []
    security._jwks_cache["fetched_at"] = 0.0


@pytest.fixture
def serve_jwks(monkeypatch):
    """Serve a JWKS document, counting how many times it is fetched."""
    calls = {"count": 0}

    def _serve(keys: list[dict], status_code: int = 200):
        def handler(request):
            calls["count"] += 1
            if status_code != 200:
                return httpx.Response(status_code, text="nope")
            return httpx.Response(200, json={"keys": keys})

        def factory(*args, **kwargs):
            kwargs.pop("timeout", None)
            return _RealAsyncClient(transport=httpx.MockTransport(handler), **kwargs)

        monkeypatch.setattr(httpx, "AsyncClient", factory)
        monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")
        monkeypatch.setattr(settings, "supabase_jwt_audience", AUDIENCE)
        return calls

    return _serve


def es256_token(pem: str, *, kid: str = KID, role: str | None = None, expired: bool = False):
    """Mint an ES256 token the way Supabase would."""
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(uuid4()),
        "aud": AUDIENCE,
        "email": "user@example.com",
        "exp": now - timedelta(minutes=5) if expired else now + timedelta(hours=1),
    }
    if role:
        claims["app_metadata"] = {"role": role}
    return jwt.encode(claims, pem, algorithm="ES256", headers={"kid": kid})


class TestAsymmetricVerification:
    @pytest.mark.asyncio
    async def test_a_real_shaped_es256_token_is_accepted(self, ec_keypair, serve_jwks):
        pem, jwk = ec_keypair
        serve_jwks([jwk])
        claims = await security.decode_supabase_jwt(es256_token(pem))
        assert claims["email"] == "user@example.com"

    @pytest.mark.asyncio
    async def test_role_is_read_from_app_metadata(self, ec_keypair, serve_jwks):
        pem, jwk = ec_keypair
        serve_jwks([jwk])
        claims = await security.decode_supabase_jwt(
            es256_token(pem, role="claims_employee")
        )
        assert security._role_from_claims(claims).value == "claims_employee"

    @pytest.mark.asyncio
    async def test_expired_token_is_rejected(self, ec_keypair, serve_jwks):
        pem, jwk = ec_keypair
        serve_jwks([jwk])
        with pytest.raises(HTTPException) as exc:
            await security.decode_supabase_jwt(es256_token(pem, expired=True))
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_token_from_another_keypair_is_rejected(self, ec_keypair, serve_jwks):
        _, jwk = ec_keypair
        other = ec.generate_private_key(ec.SECP256R1())
        other_pem = other.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()
        serve_jwks([jwk])
        with pytest.raises(HTTPException) as exc:
            await security.decode_supabase_jwt(es256_token(other_pem))
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_unknown_kid_is_rejected(self, ec_keypair, serve_jwks):
        pem, jwk = ec_keypair
        serve_jwks([jwk])
        with pytest.raises(HTTPException) as exc:
            await security.decode_supabase_jwt(es256_token(pem, kid="rotated-away"))
        assert exc.value.status_code == 401


class TestJwksCaching:
    @pytest.mark.asyncio
    async def test_jwks_is_fetched_once_for_repeated_tokens(self, ec_keypair, serve_jwks):
        pem, jwk = ec_keypair
        calls = serve_jwks([jwk])
        for _ in range(3):
            await security.decode_supabase_jwt(es256_token(pem))
        # Fetching per request would put an HTTP round trip on every API call.
        assert calls["count"] == 1

    @pytest.mark.asyncio
    async def test_unknown_kid_triggers_exactly_one_refetch(self, ec_keypair, serve_jwks):
        pem, jwk = ec_keypair
        calls = serve_jwks([jwk])
        await security.decode_supabase_jwt(es256_token(pem))  # warms the cache
        with pytest.raises(HTTPException):
            await security.decode_supabase_jwt(es256_token(pem, kid="unseen"))
        # One refetch, because an unseen kid is how key rotation appears; not a
        # refetch per request, which would let a bad token hammer the endpoint.
        assert calls["count"] == 2

    @pytest.mark.asyncio
    async def test_unreachable_jwks_rejects_rather_than_admits(self, serve_jwks, ec_keypair):
        pem, _ = ec_keypair
        serve_jwks([], status_code=500)
        with pytest.raises(HTTPException) as exc:
            await security.decode_supabase_jwt(es256_token(pem))
        assert exc.value.status_code == 401


class TestSymmetricVerification:
    """Legacy projects still using a shared HS256 secret."""

    @pytest.mark.asyncio
    async def test_hs256_token_is_accepted_when_a_secret_is_set(self, monkeypatch):
        monkeypatch.setattr(settings, "supabase_jwt_secret", "legacy-shared-secret")
        monkeypatch.setattr(settings, "supabase_jwt_audience", AUDIENCE)
        token = jwt.encode(
            {"sub": str(uuid4()), "aud": AUDIENCE,
             "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "legacy-shared-secret", algorithm="HS256")
        claims = await security.decode_supabase_jwt(token)
        assert claims["sub"]

    @pytest.mark.asyncio
    async def test_hs256_without_a_secret_is_a_server_error_not_an_admission(
        self, monkeypatch
    ):
        monkeypatch.setattr(settings, "supabase_jwt_secret", "")
        monkeypatch.setattr(settings, "supabase_jwt_audience", AUDIENCE)
        token = jwt.encode(
            {"sub": str(uuid4()), "aud": AUDIENCE,
             "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "anything", algorithm="HS256")
        with pytest.raises(HTTPException) as exc:
            await security.decode_supabase_jwt(token)
        assert exc.value.status_code == 500


class TestAlgorithmConfusion:
    """
    The attack the two-path design invites.

    The JWKS key is public. If an HS256 token were verified against that public
    value as a shared secret, anyone could mint a valid token. HS256 is
    therefore only ever checked against the private shared secret.
    """

    @pytest.mark.asyncio
    async def test_hs256_signed_with_the_public_key_is_rejected(
        self, ec_keypair, serve_jwks, monkeypatch
    ):
        _, jwk = ec_keypair
        serve_jwks([jwk])
        # No shared secret configured: the only key material on the server is
        # the public JWKS entry.
        monkeypatch.setattr(settings, "supabase_jwt_secret", "")

        forged = jwt.encode(
            {"sub": str(uuid4()), "aud": AUDIENCE,
             "app_metadata": {"role": "admin"},
             "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            jwk["x"] + jwk["y"],          # the public coordinates, as a "secret"
            algorithm="HS256",
            headers={"kid": KID},
        )
        with pytest.raises(HTTPException) as exc:
            await security.decode_supabase_jwt(forged)
        # Refused, and never as a success.
        assert exc.value.status_code in (401, 500)

    @pytest.mark.asyncio
    async def test_none_algorithm_is_rejected(self, ec_keypair, serve_jwks):
        _, jwk = ec_keypair
        serve_jwks([jwk])
        unsigned = (
            jwt.encode({"sub": "x"}, "k", algorithm="HS256").rsplit(".", 1)[0] + "."
        )
        # Rebuild the header to claim alg=none.
        import base64, json

        header = base64url_encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode()
        payload = unsigned.split(".")[1]
        with pytest.raises(HTTPException) as exc:
            await security.decode_supabase_jwt(f"{header}.{payload}.")
        assert exc.value.status_code == 401
