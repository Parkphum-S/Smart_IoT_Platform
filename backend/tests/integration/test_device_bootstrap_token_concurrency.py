"""PostgreSQL concurrency tests for bootstrap token consumption."""

import asyncio

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.modules.devices.models import DeviceBootstrapToken
from app.modules.devices.services.device_bootstrap_token_repository import (
    DeviceBootstrapTokenRepository,
)


@pytest.mark.asyncio
async def test_concurrent_bootstrap_token_consumption_allows_only_one_winner(
    bootstrap_token_concurrency_context,
):
    context = bootstrap_token_concurrency_context
    factory = context["session_factory"]
    repository = DeviceBootstrapTokenRepository()

    first_session = factory()
    first_transaction = await first_session.begin()
    second_task = None

    try:
        first_token = await repository.get_by_hash(
            first_session,
            token_hash=context["token_hash"],
        )
        assert first_token is not None

        consumed_at = first_token.created_at.replace(
            tzinfo=timezone.utc
        ) + __import__("datetime").timedelta(seconds=1)

        await repository.consume(
            first_session,
            token=first_token,
            consumed_at=consumed_at,
        )

        second_started = asyncio.Event()

        async def competing_consume():
            async with factory() as second_session:
                async with second_session.begin():
                    second_token = await repository.get_by_hash(
                        second_session,
                        token_hash=context["token_hash"],
                    )
                    assert second_token is not None

                    second_started.set()

                    return await repository.consume(
                        second_session,
                        token=second_token,
                        consumed_at=consumed_at,
                    )

        second_task = asyncio.create_task(competing_consume())

        await asyncio.wait_for(second_started.wait(), timeout=5)

        done, _ = await asyncio.wait(
            {second_task},
            timeout=0.15,
        )
        assert not done, (
            "Second transaction should wait for the first "
            "transaction's row lock."
        )

        await first_transaction.commit()

        with pytest.raises(
            ValueError,
            match="expired, consumed, or revoked",
        ):
            await asyncio.wait_for(second_task, timeout=5)

        async with factory() as verification_session:
            stored_consumed_at = await verification_session.scalar(
                select(DeviceBootstrapToken.consumed_at).where(
                    DeviceBootstrapToken.id == context["token_id"]
                )
            )

        assert stored_consumed_at == consumed_at

    finally:
        if first_transaction.is_active:
            await first_transaction.rollback()

        if second_task is not None and not second_task.done():
            second_task.cancel()
            await asyncio.gather(
                second_task,
                return_exceptions=True,
            )

        await first_session.close()
