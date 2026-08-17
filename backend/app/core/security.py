"""
Authentication and authorisation for VeriClaim AI MVP.

Supabase issues the JWTs; this module verifies them and turns the claims into a
`CurrentUser` the route layer can authorise against.

The API is the authorisation boundary between the customer portal and the
adjuster console. Row Level Security is the backstop behind it, not a
replacement for the checks here.
"""

import logging
from typing import Annotated, Iterable, Optional
from uuid import UUID

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

ALGORITHM = "HS256"


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


def decode_supabase_jwt(token: str) -> dict:
    """
    Verify a Supabase access token and return its claims.

    Args:
        token: The raw JWT from the Authorization header.

    Returns:
        The decoded claim set.

    Raises:
        HTTPException: 500 if no signing secret is configured, 401 if the token
            is expired, malformed, or fails signature or audience checks.
    """
    if not settings.supabase_jwt_secret:
        # Fail closed. Accepting unverified tokens would make every role check
        # below decorative.
        logger.error("SUPABASE_JWT_SECRET is not configured; rejecting request")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication is not configured on the server",
        )

    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=[ALGORITHM],
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

    claims = decode_supabase_jwt(credentials.credentials)

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
