"""
Authentication and authorisation for VeriClaim AI MVP.

Supabase issues the JWTs; this module verifies them and turns the claims into a
`CurrentUser` the route layer can authorise against.

The API is the authorisation boundary between the customer portal and the
adjuster console. Row Level Security is the backstop behind it, not a
replacement for the checks here.
"""

import logging
import time
from typing import Annotated, Any, Iterable, Optional
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings
from app.schemas.enums import UserRole

logger = logging.getLogger(__name__)

# auto_error=False so a missing header reaches our handler and produces the
# project's error envelope rather than FastAPI's default body.
bearer_scheme = HTTPBearer(auto_error=False, description="Supabase access token")

# Asymmetric algorithms verified against the project's published JWKS.
ASYMMETRIC_ALGORITHMS = frozenset({"ES256", "ES384", "ES512", "RS256", "RS384", "RS512"})
# Symmetric algorithm verified against the legacy shared JWT secret.
SYMMETRIC_ALGORITHMS = frozenset({"HS256", "HS384", "HS512"})

# JWKS is cached because it is fetched on the hot path of every request, and
# refetched when a token presents an unseen kid, which is how key rotation
# surfaces.
_JWKS_TTL_SECONDS = 600
_jwks_cache: dict[str, Any] = {"keys": [], "fetched_at": 0.0}


def _jwks_url() -> str:
    """Return the project's JWKS discovery URL."""
    return f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


async def _fetch_jwks(force: bool = False) -> list[dict]:
    """
    Return the project's signing keys, from cache when fresh.

    Args:
        force: Refetch even if the cache is still within its TTL. Used when a
            token presents a kid that is not in the cached set.

    Returns:
        The JWK list, empty if the endpoint could not be read.
    """
    fresh = time.monotonic() - _jwks_cache["fetched_at"] < _JWKS_TTL_SECONDS
    if _jwks_cache["keys"] and fresh and not force:
        return _jwks_cache["keys"]

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                _jwks_url(), headers={"apikey": settings.supabase_key}
            )
        if response.status_code >= 400:
            logger.error("JWKS fetch failed (%s)", response.status_code)
            return _jwks_cache["keys"]

        keys = response.json().get("keys") or []
        _jwks_cache["keys"] = keys
        _jwks_cache["fetched_at"] = time.monotonic()
        logger.info("Loaded %d signing key(s) from JWKS", len(keys))
        return keys
    except (httpx.HTTPError, ValueError):
        logger.exception("Could not fetch JWKS")
        # Serving from a stale cache beats rejecting every request outright.
        return _jwks_cache["keys"]


async def _signing_key(kid: Optional[str]) -> Optional[dict]:
    """
    Find the JWK matching a token's key id.

    Args:
        kid: The `kid` header from the token.

    Returns:
        The matching JWK, or None if no key matches.
    """
    keys = await _fetch_jwks()
    match = next((k for k in keys if k.get("kid") == kid), None)
    if match is None:
        # An unknown kid usually means the project rotated its keys.
        keys = await _fetch_jwks(force=True)
        match = next((k for k in keys if k.get("kid") == kid), None)
    return match


class CurrentUser(BaseModel):
    """Authenticated principal derived from a verified Supabase JWT."""

    id: UUID
    email: Optional[str] = None
    role: UserRole = UserRole.CUSTOMER

    @property
    def is_staff(self) -> bool:
        """True for roles allowed to see other people's claims."""
        return self.role in (UserRole.CLAIMS_EMPLOYEE, UserRole.ADMIN)


def _unauthorised(detail: str) -> HTTPException:
    """Build a 401 carrying the WWW-Authenticate header clients expect."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def decode_supabase_jwt(token: str) -> dict:
    """
    Verify a Supabase access token and return its claims.

    Supabase projects sign tokens one of two ways, and which one is in use is a
    property of the project, not a choice made here:

    * Newer projects use asymmetric keys (typically ES256) and publish the
      public half at the JWKS endpoint.
    * Older projects use a shared HS256 secret.

    The token's own `alg` header selects the path, but each path is pinned to
    one kind of key material. That matters: the JWKS public key is public, so
    if an HS256 token were ever verified against it, anyone could forge a token
    by signing with that public value. HS256 is therefore only ever checked
    against the private shared secret.

    Args:
        token: The raw JWT from the Authorization header.

    Returns:
        The decoded claim set.

    Raises:
        HTTPException: 401 if the token is malformed, expired, or fails
            signature or audience checks; 500 if the server has no way to
            verify the algorithm the token claims.
    """
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        logger.warning("Rejected malformed access token: %s", exc)
        raise _unauthorised("Invalid or expired access token") from exc

    algorithm = header.get("alg")

    if algorithm in SYMMETRIC_ALGORITHMS:
        if not settings.supabase_jwt_secret:
            # Fail closed: without the secret there is nothing to check against,
            # and accepting the token would make every role check decorative.
            logger.error(
                "Token uses %s but SUPABASE_JWT_SECRET is not set; rejecting", algorithm
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication is not configured on the server",
            )
        key: Any = settings.supabase_jwt_secret
        allowed = [algorithm]

    elif algorithm in ASYMMETRIC_ALGORITHMS:
        jwk_key = await _signing_key(header.get("kid"))
        if jwk_key is None:
            logger.warning(
                "No JWKS key matches kid=%s; rejecting token", header.get("kid")
            )
            raise _unauthorised("Invalid or expired access token")
        key = jwk_key
        # Pinned to the key's own algorithm so a token cannot nominate a weaker
        # one than the key was published for.
        allowed = [jwk_key.get("alg") or algorithm]

    else:
        logger.warning("Rejected token with unsupported alg=%r", algorithm)
        raise _unauthorised("Invalid or expired access token")

    try:
        return jwt.decode(
            token,
            key,
            algorithms=allowed,
            audience=settings.supabase_jwt_audience,
        )
    except JWTError as exc:
        logger.warning("Rejected access token: %s", exc)
        raise _unauthorised("Invalid or expired access token") from exc


def _role_from_claims(claims: dict) -> UserRole:
    """
    Read the application role out of a Supabase claim set.

    Supabase puts its own `role` claim (usually "authenticated") on every token,
    so the application role is read from user metadata first and only then from
    the top-level claim.

    Args:
        claims: Decoded JWT claims.

    Returns:
        The resolved role, defaulting to `customer`.
    """
    app_metadata = claims.get("app_metadata") or {}
    user_metadata = claims.get("user_metadata") or {}

    raw = (
        app_metadata.get("role")
        or user_metadata.get("role")
        or claims.get("user_role")
    )

    # Supabase's built-in "authenticated" role carries no application meaning.
    if raw in (None, "", "authenticated"):
        return UserRole.CUSTOMER

    try:
        return UserRole(raw)
    except ValueError:
        logger.warning("Unrecognised role claim %r; treating as customer", raw)
        return UserRole.CUSTOMER


async def get_current_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
) -> CurrentUser:
    """
    FastAPI dependency resolving the caller from the Authorization header.

    Args:
        credentials: Bearer credentials extracted by `HTTPBearer`.

    Returns:
        The authenticated `CurrentUser`.

    Raises:
        HTTPException: 401 if the header is absent or the token is unusable.
    """
    if credentials is None or not credentials.credentials:
        raise _unauthorised("Not authenticated")

    claims = await decode_supabase_jwt(credentials.credentials)

    subject = claims.get("sub")
    if not subject:
        raise _unauthorised("Access token is missing a subject claim")

    try:
        user_id = UUID(subject)
    except (ValueError, TypeError) as exc:
        raise _unauthorised("Access token subject is not a valid user id") from exc

    return CurrentUser(
        id=user_id,
        email=claims.get("email"),
        role=_role_from_claims(claims),
    )


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_roles(*allowed: UserRole):
    """
    Build a dependency that admits only the given roles.

    Usage:
        @router.get("/analytics", dependencies=[Depends(require_roles(UserRole.ADMIN))])

    Args:
        *allowed: Roles permitted to proceed.

    Returns:
        A FastAPI dependency callable.
    """
    permitted: frozenset[UserRole] = frozenset(allowed)

    async def _guard(user: CurrentUserDep) -> CurrentUser:
        if user.role not in permitted:
            logger.warning(
                "Blocked %s (role=%s) from a route requiring %s",
                user.id,
                user.role,
                sorted(r.value for r in permitted),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this resource",
            )
        return user

    return _guard


def require_staff():
    """
    Dependency admitting claims employees and admins.

    Returns:
        A FastAPI dependency callable.
    """
    return require_roles(UserRole.CLAIMS_EMPLOYEE, UserRole.ADMIN)


def assert_can_access_claim(user: CurrentUser, claim_owner_id: Optional[UUID]) -> None:
    """
    Authorise a customer to reach a specific claim.

    Staff may read any claim; a customer may only reach their own.

    Args:
        user: The authenticated caller.
        claim_owner_id: `created_by_user_id` on the claim.

    Raises:
        HTTPException: 404 if a customer requests someone else's claim.
    """
    if user.is_staff:
        return

    if claim_owner_id is None or claim_owner_id != user.id:
        # 404 rather than 403: confirming the claim exists would leak that a
        # given claim number is real.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )


def roles_summary(roles: Iterable[UserRole]) -> str:
    """Render a role set for log messages."""
    return ", ".join(sorted(r.value for r in roles))
