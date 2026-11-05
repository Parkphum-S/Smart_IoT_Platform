"""Workspace-scoped device and gateway management API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.api.security import require_session_csrf
from app.core.config import Settings, get_settings
from app.modules.devices.models import Device, DeviceGateway, DeviceGatewayMember
from app.modules.devices.schemas import (
    DeviceCreateRequest,
    DeviceLifecycleRequest,
    DeviceResponse,
    DeviceUpdateRequest,
    GatewayAssignmentRequest,
    GatewayCreateRequest,
    GatewayMembershipResponse,
    GatewayResponse,
    GatewayUpdateRequest,
    GatewaySecretCreateRequest,
    GatewaySecretUpdateRequest,
    GatewaySecretResponse,
)
from app.modules.devices.services.device_service import DeviceService
from app.modules.devices.services.exceptions import (
    DeviceError,
    DeviceInvalidInput,
    DeviceNotFound,
    DevicePermissionDenied,
    DeviceStateConflict,
    DeviceTypeNotFound,
    GatewayAlreadyRegistered,
    GatewayCycleDetected,
    GatewayMembershipConflict,
    GatewayNotFound,
    GatewaySecretAlreadyExists,
    GatewaySecretEncryptionUnavailable,
    GatewaySecretNotFound,
)
from app.modules.devices.services.gateway_service import GatewayService
from app.modules.devices.services.gateway_secret_service import GatewaySecretService
from app.modules.users.models import User

router = APIRouter(
    prefix="/workspaces/{workspace_id}/devices",
    tags=["Devices"],
)

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
AuthenticatedUser = Annotated[User, Depends(get_current_user)]
SessionCSRF = Annotated[None, Depends(require_session_csrf)]


def _raise_device_http_error(exc: DeviceError) -> None:
    """Map domain errors to stable HTTP responses without exposing internals."""
    if isinstance(
        exc,
        (
            DeviceNotFound,
            DeviceTypeNotFound,
            GatewayNotFound,
            GatewaySecretNotFound,
        ),
    ):
        code, detail = 404, "The requested device resource was not found."
    elif isinstance(exc, GatewaySecretEncryptionUnavailable):
        code, detail = 503, "Gateway secret encryption is unavailable."
    elif isinstance(exc, DevicePermissionDenied):
        code, detail = 403, "You do not have permission to perform this action."
    elif isinstance(exc, DeviceInvalidInput):
        code, detail = 422, "The supplied device data is invalid."
    elif isinstance(
        exc,
        (
            DeviceStateConflict,
            GatewayAlreadyRegistered,
            GatewayMembershipConflict,
            GatewayCycleDetected,
            GatewaySecretAlreadyExists,
        ),
    ):
        code, detail = 409, "The requested device operation conflicts with its current state."
    else:
        raise exc
    raise HTTPException(status_code=code, detail=detail) from None


@router.post(
    "",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_device(
    workspace_id: UUID,
    payload: DeviceCreateRequest,
    session: DbSession,
    current_user: AuthenticatedUser,
    _: SessionCSRF,
) -> DeviceResponse:
    service = DeviceService()
    try:
        device = await service.create_device(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            **payload.model_dump(),
        )
    except DeviceError as exc:
        _raise_device_http_error(exc)
    return DeviceResponse.model_validate(device)


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    workspace_id: UUID,
    session: DbSession,
    current_user: AuthenticatedUser,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DeviceResponse]:
    service = DeviceService()
    try:
        devices = await service.list_devices(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            limit=limit,
            offset=offset,
        )
    except DeviceError as exc:
        _raise_device_http_error(exc)
    return [DeviceResponse.model_validate(item) for item in devices]


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    workspace_id: UUID,
    device_id: UUID,
    session: DbSession,
    current_user: AuthenticatedUser,
) -> DeviceResponse:
    service = DeviceService()
    try:
        device = await service.get_device(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            device_id=device_id,
        )
    except DeviceError as exc:
        _raise_device_http_error(exc)
    return DeviceResponse.model_validate(device)


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    workspace_id: UUID,
    device_id: UUID,
    payload: DeviceUpdateRequest,
    session: DbSession,
    current_user: AuthenticatedUser,
    _: SessionCSRF,
) -> DeviceResponse:
    service = DeviceService()
    try:
        device = await service.update_device(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            device_id=device_id,
            changes=payload.model_dump(exclude_unset=True),
        )
    except DeviceError as exc:
        _raise_device_http_error(exc)
    return DeviceResponse.model_validate(device)


@router.post("/{device_id}/lifecycle", response_model=DeviceResponse)
async def change_device_lifecycle(
    workspace_id: UUID,
    device_id: UUID,
    payload: DeviceLifecycleRequest,
    session: DbSession,
    current_user: AuthenticatedUser,
    _: SessionCSRF,
) -> DeviceResponse:
    service = DeviceService()
    try:
        device = await service.change_lifecycle(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            device_id=device_id,
            new_status=payload.status,
        )
    except DeviceError as exc:
        _raise_device_http_error(exc)
    return DeviceResponse.model_validate(device)


@router.post(
    "/{device_id}/gateway",
    response_model=GatewayResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_gateway(
    workspace_id: UUID,
    device_id: UUID,
    payload: GatewayCreateRequest,
    session: DbSession,
    current_user: AuthenticatedUser,
    _: SessionCSRF,
) -> GatewayResponse:
    service = GatewayService()
    try:
        gateway = await service.register_gateway(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            device_id=device_id,
            **payload.model_dump(),
        )
    except DeviceError as exc:
        _raise_device_http_error(exc)
    return GatewayResponse.model_validate(gateway)


@router.patch("/{device_id}/gateway", response_model=GatewayResponse)
async def update_gateway(
    workspace_id: UUID,
    device_id: UUID,
    payload: GatewayUpdateRequest,
    session: DbSession,
    current_user: AuthenticatedUser,
    _: SessionCSRF,
) -> GatewayResponse:
    service = GatewayService()
    changes = payload.model_dump(exclude_unset=True)
    try:
        gateway = await service.update_gateway(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            device_id=device_id,
            **changes,
        )
    except DeviceError as exc:
        _raise_device_http_error(exc)
    return GatewayResponse.model_validate(gateway)


@router.get(
    "/{device_id}/gateway/secrets",
    response_model=list[GatewaySecretResponse],
)
async def list_gateway_secrets(
    workspace_id: UUID,
    device_id: UUID,
    session: DbSession,
    current_user: AuthenticatedUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[GatewaySecretResponse]:
    service = GatewaySecretService(settings=settings)
    try:
        secrets = await service.list_secrets(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            gateway_device_id=device_id,
        )
    except DeviceError as exc:
        _raise_device_http_error(exc)

    return [GatewaySecretResponse.model_validate(item) for item in secrets]


@router.post(
    "/{device_id}/gateway/secrets",
    response_model=GatewaySecretResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_gateway_secret(
    workspace_id: UUID,
    device_id: UUID,
    payload: GatewaySecretCreateRequest,
    session: DbSession,
    current_user: AuthenticatedUser,
    _: SessionCSRF,
    settings: Annotated[Settings, Depends(get_settings)],
) -> GatewaySecretResponse:
    service = GatewaySecretService(settings=settings)
    try:
        secret = await service.create_secret(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            gateway_device_id=device_id,
            secret_name=payload.secret_name,
            secret_value=payload.value.get_secret_value(),
        )
    except DeviceError as exc:
        _raise_device_http_error(exc)

    return GatewaySecretResponse.model_validate(secret)


@router.put(
    "/{device_id}/gateway/secrets/{secret_name}",
    response_model=GatewaySecretResponse,
)
async def update_gateway_secret(
    workspace_id: UUID,
    device_id: UUID,
    secret_name: str,
    payload: GatewaySecretUpdateRequest,
    session: DbSession,
    current_user: AuthenticatedUser,
    _: SessionCSRF,
    settings: Annotated[Settings, Depends(get_settings)],
) -> GatewaySecretResponse:
    service = GatewaySecretService(settings=settings)
    try:
        secret = await service.update_secret(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            gateway_device_id=device_id,
            secret_name=secret_name,
            secret_value=payload.value.get_secret_value(),
        )
    except DeviceError as exc:
        _raise_device_http_error(exc)

    return GatewaySecretResponse.model_validate(secret)


@router.delete(
    "/{device_id}/gateway/secrets/{secret_name}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_gateway_secret(
    workspace_id: UUID,
    device_id: UUID,
    secret_name: str,
    session: DbSession,
    current_user: AuthenticatedUser,
    _: SessionCSRF,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    service = GatewaySecretService(settings=settings)
    try:
        await service.delete_secret(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            gateway_device_id=device_id,
            secret_name=secret_name,
        )
    except DeviceError as exc:
        _raise_device_http_error(exc)


@router.put(
    "/{child_device_id}/gateway-membership",
    response_model=GatewayMembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_gateway(
    workspace_id: UUID,
    child_device_id: UUID,
    payload: GatewayAssignmentRequest,
    session: DbSession,
    current_user: AuthenticatedUser,
    _: SessionCSRF,
) -> GatewayMembershipResponse:
    service = GatewayService()
    try:
        membership = await service.assign_gateway(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            child_device_id=child_device_id,
            gateway_device_id=payload.gateway_device_id,
        )
    except DeviceError as exc:
        _raise_device_http_error(exc)
    return GatewayMembershipResponse.model_validate(membership)


@router.delete(
    "/{child_device_id}/gateway-membership",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_gateway(
    workspace_id: UUID,
    child_device_id: UUID,
    session: DbSession,
    current_user: AuthenticatedUser,
    _: SessionCSRF,
) -> None:
    service = GatewayService()
    try:
        await service.remove_gateway(
            session,
            actor_id=current_user.id,
            workspace_id=workspace_id,
            child_device_id=child_device_id,
        )
    except DeviceError as exc:
        _raise_device_http_error(exc)
