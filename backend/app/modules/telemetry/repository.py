"""Persistence operations for telemetry metrics and readings."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.telemetry.models import (
    TelemetryMetric,
    TelemetryReading,
)


class TelemetryRepository:
    """Database operations; transaction ownership remains with the caller."""

    @staticmethod
    async def get_metric(
        session: AsyncSession,
        *,
        device_type_id: UUID,
        metric_key: str,
    ) -> TelemetryMetric | None:
        """Find a metric belonging to the specified device type."""
        statement = select(TelemetryMetric).where(
            TelemetryMetric.device_type_id == device_type_id,
            TelemetryMetric.metric_key == metric_key,
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_metrics(
        session: AsyncSession,
        *,
        device_type_id: UUID,
    ) -> list[TelemetryMetric]:
        """List metrics declared for one device type."""
        statement = (
            select(TelemetryMetric)
            .where(TelemetryMetric.device_type_id == device_type_id)
            .order_by(TelemetryMetric.metric_key, TelemetryMetric.id)
        )
        result = await session.execute(statement)
        return list(result.scalars().all())

    @staticmethod
    async def add_reading(
        session: AsyncSession,
        *,
        workspace_id: UUID,
        device_id: UUID,
        device_type_id: UUID,
        metric_id: UUID,
        recorded_at: datetime,
        received_at: datetime,
        value_numeric: Decimal | None = None,
        value_text: str | None = None,
        value_boolean: bool | None = None,
        value_json: dict | list | None = None,
        quality: str | None = None,
    ) -> TelemetryReading:
        """Add and flush one reading without committing."""
        reading = TelemetryReading(
            workspace_id=workspace_id,
            device_id=device_id,
            device_type_id=device_type_id,
            metric_id=metric_id,
            recorded_at=recorded_at,
            received_at=received_at,
            value_numeric=value_numeric,
            value_text=value_text,
            value_boolean=value_boolean,
            value_json=value_json,
            quality=quality,
        )
        session.add(reading)
        await session.flush()
        return reading

    @staticmethod
    async def add_readings(
        session: AsyncSession,
        *,
        readings: list[dict[str, Any]],
    ) -> list[TelemetryReading]:
        """Add and flush a batch without committing.

        The caller must provide a single transaction for the entire batch.
        Any flush failure must abort that transaction.
        """
        if not readings:
            return []

        records = [
            TelemetryReading(**reading)
            for reading in readings
        ]
        session.add_all(records)
        await session.flush()
        return records
