"""Public device enrollment endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import Settings, get_settings
from app.modules.devices.schemas import (
    DeviceEnrollmentRequest,
    DeviceEnrollmentResponse,
)
from app.modules.devices.services.device_enrollment_service import (
    DeviceEnrollmentService,
)
from app.modules.devices.services.exceptions import DeviceEnrollmentFailed


router = APIRouter(
    prefix="/device-enrollment",
    tags=["device-enrollment"],
)


@router.post(
    "/enroll",
    response_model=DeviceEnrollmentResponse,
    status_code=status.HTTP_200_OK,
)
async def enroll_device(
    payload: DeviceEnrollmentRequest,
    session: Annotated[
        AsyncSession,
        Depends(get_db_session, scope="function"),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DeviceEnrollmentResponse:
    """Authenticate a device and activate its pending credential."""
    broker_key = settings.device_enrollment_broker_key
    if broker_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device enrollment is unavailable.",
        )

    try:
        result = await DeviceEnrollmentService().enroll_device(
            session,
            bootstrap_token=payload.bootstrap_token.get_secret_value(),
            broker_key=broker_key.get_secret_value(),
            credential_identifier=payload.credential_identifier,
            password=payload.password.get_secret_value(),
        )
    except DeviceEnrollmentFailed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device enrollment failed.",
        ) from None

    return DeviceEnrollmentResponse(
        device_id=result.device_id,
        credential_id=result.credential_id,
        lifecycle_status=result.lifecycle_status,
        credential_status=result.credential_status,
    )
