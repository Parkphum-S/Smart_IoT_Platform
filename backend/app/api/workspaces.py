"""Workspace creation API endpoints."""

from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.api.security import require_session_csrf
from app.modules.users.models import User
from app.modules.users.services.workspace_service import (
    WorkspaceCreatorNotActive,
    WorkspaceService,
)

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
AuthenticatedUser = Annotated[User, Depends(get_current_user)]
SessionCSRF = Annotated[None, Depends(require_session_csrf)]


class WorkspaceCreateRequest(BaseModel):
    """Fields accepted when creating a workspace."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    timezone: str = Field(default="UTC", min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Workspace name cannot be empty.")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        value = value.strip()
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError):
            raise ValueError("A valid IANA timezone is required.") from None
        return value


class WorkspaceCreateResponse(BaseModel):
    """Workspace details and the creator's initial membership."""

    id: UUID
    name: str
    description: str | None
    timezone: str
    role: str
    is_active: bool


@router.post(
    "",
    response_model=WorkspaceCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    session: DbSession,
    current_user: AuthenticatedUser,
    _: SessionCSRF,
) -> WorkspaceCreateResponse:
    """Create a workspace and make the authenticated user its owner."""
    service = WorkspaceService()

    try:
        workspace, membership = await service.create_workspace(
            session,
            creator_id=current_user.id,
            name=payload.name,
            description=payload.description,
            timezone=payload.timezone,
        )
    except WorkspaceCreatorNotActive:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An active user is required to create a workspace.",
        ) from None

    return WorkspaceCreateResponse(
        id=workspace.id,
        name=workspace.name,
        description=workspace.description,
        timezone=workspace.timezone,
        role=membership.role,
        is_active=membership.is_active,
    )
