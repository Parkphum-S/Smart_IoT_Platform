"""Workspace management API endpoints."""

from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.api.security import require_session_csrf
from app.modules.users.models import User
from app.modules.users.services.workspace_service import (
    WorkspaceCreatorNotActive,
    WorkspaceNotFound,
    WorkspacePermissionDenied,
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


class WorkspaceDetailResponse(BaseModel):
    """Public workspace metadata."""
    id: UUID
    name: str
    description: str | None
    timezone: str


class WorkspaceUpdateRequest(BaseModel):
    """Fields that an authorized workspace administrator may update."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Workspace name cannot be null.")
        value = value.strip()
        if not value:
            raise ValueError("Workspace name cannot be empty.")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Workspace timezone cannot be null.")
        value = value.strip()
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError):
            raise ValueError("A valid IANA timezone is required.") from None
        return value

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("At least one workspace field must be supplied.")
        return self


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceDetailResponse,
)
async def get_workspace(
    workspace_id: UUID,
    session: DbSession,
    current_user: AuthenticatedUser,
) -> WorkspaceDetailResponse:
    """Read workspace details for an authorized member."""
    service = WorkspaceService()
    try:
        workspace = await service.get_workspace(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
        )
    except WorkspaceNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found.",
        ) from None
    except WorkspacePermissionDenied:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this workspace.",
        ) from None

    return WorkspaceDetailResponse.model_validate(
        workspace,
        from_attributes=True,
    )


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceDetailResponse,
)
async def update_workspace(
    workspace_id: UUID,
    payload: WorkspaceUpdateRequest,
    session: DbSession,
    current_user: AuthenticatedUser,
    _: SessionCSRF,
) -> WorkspaceDetailResponse:
    """Update workspace metadata; permission is enforced by the service."""
    service = WorkspaceService()
    changes = {
        field: getattr(payload, field)
        for field in payload.model_fields_set
    }

    try:
        workspace = await service.update_workspace(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            changes=changes,
        )
    except WorkspaceNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found.",
        ) from None
    except WorkspacePermissionDenied:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this workspace.",
        ) from None

    return WorkspaceDetailResponse.model_validate(
        workspace,
        from_attributes=True,
    )
