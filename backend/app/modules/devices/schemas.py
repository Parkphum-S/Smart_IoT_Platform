"""Public request and response schemas for device management."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DeviceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_type_id: UUID
    device_uid: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=1, max_length=160)
    manufacturer: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    protocol: str = Field(default="mqtt", min_length=1, max_length=40)


class DeviceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=160)
    manufacturer: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    protocol: str | None = Field(default=None, min_length=1, max_length=40)


class DeviceLifecycleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(min_length=1, max_length=40)


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    device_type_id: UUID
    device_uid: str
    name: str
    manufacturer: str | None
    model: str | None
    protocol: str
    is_enabled: bool
    lifecycle_status: str | None
    created_at: datetime
    updated_at: datetime


class GatewayCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gateway_type: str = Field(min_length=1, max_length=40)
    adapter_key: str = Field(min_length=1, max_length=120)
    configuration: dict[str, Any] = Field(default_factory=dict)


class GatewayUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gateway_type: str | None = Field(default=None, min_length=1, max_length=40)
    adapter_key: str | None = Field(default=None, min_length=1, max_length=120)
    configuration: dict[str, Any] | None = None


class GatewayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_id: UUID
    workspace_id: UUID
    gateway_type: str
    adapter_key: str
    configuration: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class GatewayAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gateway_device_id: UUID


class GatewayMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    child_device_id: UUID
    workspace_id: UUID
    gateway_device_id: UUID
    created_at: datetime
