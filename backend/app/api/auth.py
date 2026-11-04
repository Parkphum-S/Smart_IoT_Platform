"""Authentication API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user as get_authenticated_user, get_db_session
from app.api.security import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    require_prelogin_csrf,
    require_session_csrf,
)
from app.core.config import Settings, get_settings
from app.core.csrf import generate_csrf_token
from app.modules.users.models import User
from app.modules.users.services.authentication_service import AuthenticationService
from app.modules.users.services.session_service import SessionService


router = APIRouter(prefix="/auth", tags=["Authentication"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


class LoginRequest(BaseModel):
    """User login credentials."""

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """Apply basic email format validation without optional dependencies."""
        value = value.strip()

        if (
            len(value) > 320
            or any(character.isspace() for character in value)
            or value.count("@") != 1
        ):
            raise ValueError("A valid email address is required.")

        local_part, domain = value.rsplit("@", maxsplit=1)

        if (
            not local_part
            or len(local_part) > 64
            or "." not in domain
            or domain.startswith(".")
            or domain.endswith(".")
        ):
            raise ValueError("A valid email address is required.")

        return value


class UserResponse(BaseModel):
    """Public user information."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str


class AuthResponse(BaseModel):
    """Successful authentication response."""

    user: UserResponse


def _cookie_options(settings: Settings) -> dict:
    """Return consistent security options for authentication cookies."""
    return {
        "secure": settings.app_env == "production",
        "samesite": "lax",
        "path": settings.api_v1_prefix,
    }


def _require_secret(settings: Settings) -> str:
    """Return the configured signing secret."""
    if settings.secret_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication security is not configured.",
        )

    secret = settings.secret_key.get_secret_value()

    if len(secret) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication security is not configured.",
        )

    return secret


@router.get("/csrf")
async def issue_csrf_token(
    response: Response,
    settings: AppSettings,
) -> dict[str, str]:
    """Issue an unbound CSRF token before login."""
    token = generate_csrf_token(_require_secret(settings))

    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,
        max_age=settings.session_absolute_lifetime_seconds,
        **_cookie_options(settings),
    )

    return {"csrf_token": token}


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: DbSession,
    settings: AppSettings,
    _: Annotated[None, Depends(require_prelogin_csrf)],
) -> AuthResponse:
    """Authenticate a user and establish a server-side session."""
    secret_key = _require_secret(settings)
    authentication_service = AuthenticationService()

    user = await authentication_service.authenticate(
        session,
        email=str(payload.email),
        password=payload.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    session_service = SessionService(settings)
    raw_token, user_session = await session_service.create_session(
        session,
        user_id=user.id,
    )

    csrf_token = generate_csrf_token(
        secret_key,
        session_binding=raw_token,
    )

    cookie_options = _cookie_options(settings)

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        max_age=settings.session_absolute_lifetime_seconds,
        **cookie_options,
    )

    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        max_age=settings.session_absolute_lifetime_seconds,
        **cookie_options,
    )

    return AuthResponse(user=UserResponse.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: DbSession,
    settings: AppSettings,
    _: Annotated[None, Depends(require_session_csrf)],
) -> Response:
    """Revoke the current session and clear authentication cookies."""
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)

    if raw_token:
        session_service = SessionService(settings)
        await session_service.revoke_session(
            session,
            raw_token=raw_token,
        )

    cookie_options = _cookie_options(settings)

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        **cookie_options,
    )
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        httponly=False,
        **cookie_options,
    )

    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: Annotated[User, Depends(get_authenticated_user)],
) -> UserResponse:
    """Return the authenticated user associated with the current session."""
    return UserResponse.model_validate(current_user)
