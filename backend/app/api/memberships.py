"""Workspace membership lifecycle API endpoints."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.api.security import require_session_csrf
from app.modules.users.models import User
from app.modules.users.services.membership.exceptions import (
    MembershipError,
    DeactivationHistoryNotFound,
    InvalidOwnershipTransferTarget,
    InvalidRoleAssignment,
    MembershipAlreadyActive,
    MembershipAlreadyExists,
    MembershipInactive,
    MembershipNotFound,
    MembershipPermissionDenied,
    OwnerDeactivationProhibited,
    SelfManagementProhibited,
    UserNotFoundOrInactive,
    WorkspaceNotFound,
)
from app.modules.users.services.membership.membership_service import (
    MembershipService,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/members",
    tags=["Workspace Memberships"],
)

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
AuthenticatedUser = Annotated[User, Depends(get_current_user)]
SessionCSRF = Annotated[None, Depends(require_session_csrf)]

AssignableRole = Literal["admin", "operator", "viewer"]


class MembershipCreateRequest(BaseModel):
    """A new workspace member; owner cannot be assigned through this API."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    role: AssignableRole


class MembershipRoleUpdateRequest(BaseModel):
    """A permitted role change."""

    model_config = ConfigDict(extra="forbid")

    role: AssignableRole


class OwnershipTransferRequest(BaseModel):
    """The active membership receiving workspace ownership."""

    model_config = ConfigDict(extra="forbid")

    target_membership_id: UUID


class MembershipResponse(BaseModel):
    """Public membership information without private account fields."""

    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: str
    is_active: bool
    joined_at: datetime


class OwnershipTransferResponse(BaseModel):
    """Both membership records after ownership transfer."""

    previous_owner: MembershipResponse
    new_owner: MembershipResponse


def _raise_membership_http_error(exc: MembershipError) -> None:
    """Translate business exceptions into stable HTTP responses."""

    if isinstance(exc, (WorkspaceNotFound, MembershipNotFound)):
        code, detail = 404, "The requested workspace or membership was not found."
    elif isinstance(exc, UserNotFoundOrInactive):
        code, detail = 404, "The requested active user was not found."
    elif isinstance(exc, MembershipPermissionDenied):
        code, detail = 403, "You do not have permission to perform this action."
    elif isinstance(exc, SelfManagementProhibited):
        code, detail = 403, "You cannot manage your own membership through this endpoint."
    elif isinstance(exc, InvalidRoleAssignment):
        code, detail = 422, "The requested role assignment is not permitted."
    elif isinstance(
        exc,
        (
            MembershipAlreadyExists,
            MembershipInactive,
            MembershipAlreadyActive,
            OwnerDeactivationProhibited,
            InvalidOwnershipTransferTarget,
            DeactivationHistoryNotFound,
        ),
    ):
        code, detail = 409, "The requested membership operation conflicts with its current state."
    else:
        raise exc

    raise HTTPException(status_code=code, detail=detail) from None


@router.get("", response_model=list[MembershipResponse])
async def list_members(
    workspace_id: UUID,
    session: DbSession,
    current_user: AuthenticatedUser,
    include_inactive: Annotated[bool, Query()] = False,
) -> list[MembershipResponse]:
    """List active members, optionally including inactive memberships."""

    service = MembershipService()

    try:
        memberships = await service.list_members(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            include_inactive=include_inactive,
        )
    except MembershipError as exc:
        _raise_membership_http_error(exc)

    return [
        MembershipResponse.model_validate(membership, from_attributes=True)
        for membership in memberships
    ]


@router.post(
    "",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    workspace_id: UUID,
    payload: MembershipCreateRequest,
    session: DbSession,
    current_user: AuthenticatedUser,
    _: SessionCSRF,
) -> MembershipResponse:
    """Add an existing active platform user to a workspace."""

    service = MembershipService()

    try:
        membership = await service.add_member(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            user_id=payload.user_id,
            role=payload.role,
        )
    except MembershipError as exc:
        _raise_membership_http_error(exc)

    return MembershipResponse.model_validate(
        membership,
        from_attributes=True,
    )


@router.patch(
    "/{membership_id}/role",
    response_model=MembershipResponse,
)
async def change_member_role(
    workspace_id: UUID,
    membership_id: UUID,
    payload: MembershipRoleUpdateRequest,
    session: DbSession,
    current_user: AuthenticatedUser,
    _: SessionCSRF,
) -> MembershipResponse:
    """Change a member's workspace role."""

    service = MembershipService()

    try:
        membership = await service.change_role(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            membership_id=membership_id,
            new_role=payload.role,
        )
    except MembershipError as exc:
        _raise_membership_http_error(exc)

    return MembershipResponse.model_validate(
        membership,
        from_attributes=True,
    )


@router.post(
    "/{membership_id}/deactivate",
    response_model=MembershipResponse,
)
async def deactivate_member(
    workspace_id: UUID,
    membership_id: UUID,
    session: DbSession,
    current_user: AuthenticatedUser,
    _: SessionCSRF,
) -> MembershipResponse:
    """Deactivate a workspace membership."""

    service = MembershipService()

    try:
        membership = await service.deactivate_member(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            membership_id=membership_id,
        )
    except MembershipError as exc:
        _raise_membership_http_error(exc)

    return MembershipResponse.model_validate(
        membership,
        from_attributes=True,
    )


@router.post(
    "/{membership_id}/reactivate",
    response_model=MembershipResponse,
)
async def reactivate_member(
    workspace_id: UUID,
    membership_id: UUID,
    session: DbSession,
    current_user: AuthenticatedUser,
    _: SessionCSRF,
) -> MembershipResponse:
    """Reactivate a workspace membership using its recorded previous role."""

    service = MembershipService()

    try:
        membership = await service.reactivate_member(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            membership_id=membership_id,
        )
    except MembershipError as exc:
        _raise_membership_http_error(exc)

    return MembershipResponse.model_validate(
        membership,
        from_attributes=True,
    )


@router.post(
    "/transfer-ownership",
    response_model=OwnershipTransferResponse,
)
async def transfer_ownership(
    workspace_id: UUID,
    payload: OwnershipTransferRequest,
    session: DbSession,
    current_user: AuthenticatedUser,
    _: SessionCSRF,
) -> OwnershipTransferResponse:
    """Transfer workspace ownership to another eligible active member."""

    service = MembershipService()

    try:
        previous_owner, new_owner = await service.transfer_ownership(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            target_membership_id=payload.target_membership_id,
        )
    except MembershipError as exc:
        _raise_membership_http_error(exc)

    return OwnershipTransferResponse(
        previous_owner=MembershipResponse.model_validate(
            previous_owner,
            from_attributes=True,
        ),
        new_owner=MembershipResponse.model_validate(
            new_owner,
            from_attributes=True,
        ),
    )
